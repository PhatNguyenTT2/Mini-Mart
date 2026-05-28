/**
 * EmbeddingClient — Local Vietnamese SBERT via @xenova/transformers
 * Model: keepitreal/vietnamese-sbert (768 dimensions)
 * Runs on CPU (ONNX Runtime) — no GPU required
 *
 * Cache: Set TRANSFORMERS_CACHE env var to persist models across container restarts.
 * Without cache, the ~400MB ONNX model is re-downloaded from HuggingFace CDN every restart.
 */
const { pipeline, env } = require('@xenova/transformers');
const logger = require('../../../../shared/common/logger');

// Configure model cache directory (persisted via Docker named volume)
if (process.env.TRANSFORMERS_CACHE) {
    env.cacheDir = process.env.TRANSFORMERS_CACHE;
    logger.info({ cacheDir: env.cacheDir }, 'Transformers cache directory configured');
}

class EmbeddingClient {
    constructor(modelName = 'Xenova/multilingual-e5-base') {
        this.modelName = modelName;
        this.extractor = null;
        this.isReady = false;
    }

    /**
     * Load model on startup (cached after first download)
     * Retries up to MAX_RETRIES times with exponential backoff on network errors
     */
    async initialize(maxRetries = 3) {
        const startTime = Date.now();
        logger.info({ model: this.modelName }, 'Loading embedding model...');

        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                this.extractor = await pipeline(
                    'feature-extraction',
                    this.modelName,
                    { quantized: true }
                );

                this.isReady = true;
                const loadMs = Date.now() - startTime;
                logger.info({ model: this.modelName, loadMs, attempt }, 'Embedding model loaded');
                return;
            } catch (err) {
                const isRetryable = err.message?.includes('fetch failed') ||
                    err.message?.includes('Timeout') ||
                    err.code === 'UND_ERR_CONNECT_TIMEOUT' ||
                    err.code === 'ECONNREFUSED' ||
                    err.code === 'ENOTFOUND';

                if (!isRetryable || attempt === maxRetries) {
                    logger.error({ err, attempt, maxRetries }, 'Embedding model load failed — no more retries');
                    throw err;
                }

                const backoffMs = 5000 * Math.pow(2, attempt - 1); // 5s, 10s, 20s
                logger.warn({ err: err.message, attempt, maxRetries, backoffMs }, `Embedding model load failed — retrying in ${backoffMs / 1000}s`);
                await new Promise(r => setTimeout(r, backoffMs));
            }
        }
    }

    /**
     * Embed single text → 768d vector
     * @param {string} text
     * @returns {number[]}
     */
    async embed(text) {
        if (!this.isReady) throw new Error('Embedding model not initialized');

        const startTime = Date.now();
        const output = await this.extractor(text, {
            pooling: 'mean',
            normalize: true
        });

        const vector = Array.from(output.data);
        const latencyMs = Date.now() - startTime;

        logger.debug({ textLength: text.length, vectorDim: vector.length, latencyMs }, 'Text embedded');
        return vector;
    }

    /**
     * Embed multiple texts sequentially (avoid OOM on CPU)
     * @param {string[]} texts
     * @returns {number[][]}
     */
    async embedBatch(texts) {
        if (!this.isReady) throw new Error('Embedding model not initialized');

        const startTime = Date.now();
        const vectors = [];

        for (const text of texts) {
            const output = await this.extractor(text, {
                pooling: 'mean',
                normalize: true
            });
            vectors.push(Array.from(output.data));
        }

        const latencyMs = Date.now() - startTime;
        logger.info({ batchSize: texts.length, latencyMs }, 'Batch embedding completed');
        return vectors;
    }
}

module.exports = EmbeddingClient;
