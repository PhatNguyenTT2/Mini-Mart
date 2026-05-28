const fs = require('fs');
const path = require('path');
const http = require('http');
const cron = require('node-cron');
const { Server: SocketIO } = require('socket.io');
const logger = require('../../../shared/common/logger');
const { createPool, closePool } = require('../../../shared/db');
const eventBus = require('../../../shared/event-bus');
const EVENT = require('../../../shared/event-bus/eventTypes');

// Repositories
const ChatRepository = require('./repositories/chat.repository');
const KnowledgeRepository = require('./repositories/knowledge.repository');
const CoPurchaseRepository = require('./repositories/copurchase.repository');

// Services
const ChatService = require('./services/chat.service');
const HFClient = require('./services/hf.client');
const ApiClient = require('./services/api.client');
const EmbeddingClient = require('./services/embedding.client');
const DataIngestionService = require('./services/data-ingestion.service');
const QueryReformulator = require('./services/query-reformulator');
const RAGService = require('./services/rag.service');

// WebSocket
const initChatSocket = require('./ws/chat.handler');

const PORT = process.env.PORT || 3008;
const SERVICE_NAME = 'chatbot-service';

async function initDatabase(pool) {
  const initSql = fs.readFileSync(path.join(__dirname, 'db', 'init.sql'), 'utf8');
  await pool.query(initSql);
  logger.info('Database schema initialized for chatbot');
}

async function start() {
  try {
    // 1. Database
    const pool = createPool();
    await initDatabase(pool);
    logger.info('PostgreSQL connected');

    // 2. Event bus
    await eventBus.connect();
    logger.info('RabbitMQ connected');

    // 3. HF Inference Client
    const hfAccessToken = process.env.HF_ACCESS_TOKEN;
    if (!hfAccessToken) {
      logger.warn('HF_ACCESS_TOKEN not set — AI features will return fallback responses');
    }
    const hfModel = process.env.HF_MODEL || 'Qwen/Qwen2.5-7B-Instruct';
    const hfClient = new HFClient(hfAccessToken, hfModel);

    // 4. Internal API Client (service-to-service)
    const apiClient = new ApiClient();
    logger.info('Internal API client ready (Catalog, Inventory, Order, Auth)');

    // 5. Embedding Client (Vietnamese SBERT — local ONNX)
    const embeddingClient = new EmbeddingClient();

    // 6. Build dependency graph
    const chatRepo = new ChatRepository(pool);
    const knowledgeRepo = new KnowledgeRepository(pool);
    const copurchaseRepo = new CoPurchaseRepository(pool);

    const dataIngestionService = new DataIngestionService(pool, embeddingClient, apiClient);
    const reformulator = new QueryReformulator(hfClient);

    // Phase 2: Collaborative Filtering
    const CollaborativeFilteringService = require('./services/cf.service');
    const cfService = new CollaborativeFilteringService(pool);

    // Phase 3: Hybrid Ensemble + Session Context + Weight Learning
    const HybridRecommendationService = require('./services/hybrid.service');
    const SessionContextService = require('./services/session-context.service');
    const WeightLearner = require('./services/weight-learner');

    const hybridService = new HybridRecommendationService({ copurchaseRepo, cfService, pool });
    const sessionContextService = new SessionContextService();
    const weightLearner = new WeightLearner(pool);

    let ragService = null;
    const chatService = new ChatService(chatRepo, hfClient, apiClient, ragService, copurchaseRepo);

    // Phase 4: Nightly Batch Pipeline
    const NightlyBatchPipeline = require('./jobs/nightly-batch');
    const nightlyBatch = new NightlyBatchPipeline({
      pool, hybridService, cfService, weightLearner, copurchaseRepo
    });

    // 7. Subscribe to immediate events
    await eventBus.subscribe(SERVICE_NAME, EVENT.ORDER_COMPLETED, async (message) => {
      // 1. Data ingestion (co-purchase stats)
      await dataIngestionService.handleOrderCompleted(message);
    });

    // 2. Purchase attribution tracking (Phase 4 Task 5)
    await eventBus.subscribe(SERVICE_NAME, EVENT.ORDER_SHIPPING, async (message) => {
      try {
        const { customerId, storeId, items } = message.data || {};
        if (!customerId || !items?.length) return;

        const { rows } = await pool.query(`
          SELECT DISTINCT ON (product_id) product_id, source
          FROM recommendation_feedback
          WHERE user_id = $1 AND store_id = $2
            AND action != 'purchased'
            AND created_at > NOW() - INTERVAL '24 hours'
          ORDER BY product_id, created_at DESC
        `, [customerId, storeId]);

        if (rows.length === 0) return;

        const recommendedMap = new Map(rows.map(r => [Number(r.product_id), r.source]));

        let attributedCount = 0;
        for (const item of items) {
          const source = recommendedMap.get(Number(item.productId));
          if (source) {
            await hybridService.recordFeedback(
              customerId, item.productId, storeId, source, 'purchased'
            );
            attributedCount++;
          }
        }

        if (attributedCount > 0) {
          logger.info({ customerId, storeId, attributedCount, totalItems: items.length },
            'Purchase attribution: matched recommended products');
        }
      } catch (err) {
        logger.warn({ err }, 'Purchase attribution tracking failed — non-critical');
      }
    });
    logger.info('Purchase attribution tracking registered (order.shipping)');
    logger.info('Event subscriptions registered (order.completed)');

    // 8. Create Express app
    const createApp = require('./app');
    const app = createApp({ chatService, knowledgeRepo, hybridService, pool, nightlyBatch, weightLearner });
    app.locals.db = pool;

    // 9. Create HTTP server + Socket.IO
    const server = http.createServer(app);
    const allowedOrigins = (process.env.CORS_ORIGINS || 'http://localhost:5174,http://localhost:5173').split(',').map(o => o.trim());
    const io = new SocketIO(server, {
      cors: {
        origin: allowedOrigins,
        methods: ['GET', 'POST'],
        credentials: true
      },
      path: '/ws/chat',
      pingTimeout: 60000,
      pingInterval: 25000
    });

    // 10. Initialize WebSocket handlers
    initChatSocket(io, chatService);
    logger.info('Socket.IO initialized on /ws/chat');

    // 11. Start server (non-blocking)
    server.listen(PORT, () => {
      logger.info(`${SERVICE_NAME} running on port ${PORT} (HTTP + WebSocket + RAG Fallback)`);
    });

    // 12. Background initialization (Model Loading, RAG, Warmup, Sync)
    setImmediate(async () => {
      try {
        logger.info('Background initialization started: Loading Embedding Model...');
        await embeddingClient.initialize();
        if (embeddingClient.isReady) {
          ragService = new RAGService({
            knowledgeRepo,
            copurchaseRepo,
            cfService,
            hybridService,
            sessionContextService,
            embeddingClient,
            hfClient,
            apiClient,
            reformulator
          });

          chatService.updateRAGService(ragService);
          logger.info('RAG Service initialized and hot-swapped into ChatService');

          // Subscribe product events (cần embedding để index)
          await eventBus.subscribe(SERVICE_NAME, EVENT.PRODUCT_CREATED, async (message) => {
            await dataIngestionService.handleProductCreated(message);
          });

          await eventBus.subscribe(SERVICE_NAME, EVENT.PRODUCT_UPDATED, async (message) => {
            await dataIngestionService.handleProductUpdated(message);
          });

          await eventBus.subscribe(SERVICE_NAME, EVENT.PRODUCT_DELETED, async (message) => {
            await dataIngestionService.handleProductDeleted(message);
          });

          await eventBus.subscribe(SERVICE_NAME, EVENT.PRODUCT_PRICE_CHANGED, async (message) => {
            await dataIngestionService.handleProductUpdated(message);
          });

          await eventBus.subscribe(SERVICE_NAME, EVENT.INVENTORY_UPDATED, async (message) => {
            await dataIngestionService.handleInventoryUpdated(message);
          });
          logger.info('Event subscriptions registered (product.*, inventory.updated)');

          // Warmup (in-memory Apriori + CF similarities)
          logger.info('Background: Warming up hybrid cache...');
          await hybridService.warmUp(1).catch(err => {
            logger.warn({ err }, 'Hybrid cache warmup failed — will use DB fallback');
          });

          // Initial sync — MUST run BEFORE session cluster warmup
          // because clusters depend on product_knowledge_base (populated by syncAll)
          logger.info('Background: Running initial data sync...');
          try {
            const result = await dataIngestionService.syncAll();
            logger.info(result, 'Background: Initial sync completed');
          } catch (err) {
            logger.error({ err }, 'Background: Initial sync failed (will retry at next cron)');
          }

          // Session cluster warmup — runs AFTER syncAll so product_knowledge_base is populated
          logger.info('Background: Warming up session clusters...');
          await sessionContextService.warmUp(pool, 1).catch(err => {
            logger.warn({ err }, 'Session cluster warmup failed — will use keyword-only fallback');
          });

          logger.info('Background init completed successfully');
        }
      } catch (err) {
        logger.error({ err }, 'Background init failed — RAG disabled');
      }
    });

    // 13. Cron fallback: full sync every 30 minutes
    cron.schedule('*/30 * * * *', async () => {
      logger.info('Cron: Starting scheduled full sync...');
      if (!embeddingClient.isReady) {
        logger.warn('Cron: Skipping sync because embedding client is not ready');
        return;
      }
      try {
        const result = await dataIngestionService.syncAll();
        logger.info(result, 'Cron: Full sync completed');
      } catch (err) {
        logger.error({ err }, 'Cron: Full sync failed');
      }
    });
    logger.info('Cron scheduled: full sync every 30 minutes');

    // 14. Phase 4: Nightly batch pipeline
    if (process.env.ENABLE_CRON !== 'false') {
      nightlyBatch.start('0 2 * * *');
    }

    // Graceful shutdown
    const shutdown = async (signal) => {
      logger.info(`${signal} received, shutting down...`);
      io.close();
      server.close();
      await eventBus.close();
      await closePool();
      process.exit(0);
    };

    process.on('SIGTERM', () => shutdown('SIGTERM'));
    process.on('SIGINT', () => shutdown('SIGINT'));

  } catch (err) {
    logger.error(err, 'Failed to start service');
    process.exit(1);
  }
}

start();
