const express = require('express');
const router = express.Router();
const logger = require('../../../../shared/common/logger');

/**
 * Stats/Monitoring routes — Phase 4 Observability
 *
 * Provides CTR (Click-Through Rate) and CVR (Conversion Rate) metrics
 * plus latency breakdown for bottleneck identification.
 *
 * @param {object} deps - { pool, hybridService, nightlyBatch }
 */
module.exports = function statsRoutes({ pool, hybridService, nightlyBatch, weightLearner }) {

    /**
     * GET /api/chatbot/stats/recommendations?storeId=1&days=30
     * Aggregated recommendation performance metrics
     */
    router.get('/stats/recommendations', async (req, res, next) => {
        try {
            const storeId = parseInt(req.query.storeId) || 1;
            const days = parseInt(req.query.days) || 30;

            // Action counts
            const { rows: actionStats } = await pool.query(`
                SELECT action, COUNT(*)::int AS count
                FROM recommendation_feedback
                WHERE store_id = $1 AND created_at > NOW() - INTERVAL '1 day' * $2
                  AND source != 'organic'
                GROUP BY action
            `, [storeId, days]);

            const actionMap = {};
            for (const r of actionStats) {
                actionMap[r.action] = r.count;
            }

            const totalRecommended = actionMap.recommended || 0;
            const totalHovered = actionMap.hovered || 0;
            const totalClicked = actionMap.clicked || 0;
            const totalAddedToCart = actionMap.added_to_cart || 0;
            const totalPurchased = actionMap.purchased || 0;

            // Source breakdown
            const { rows: sourceStats } = await pool.query(`
                SELECT source,
                    COUNT(*) FILTER (WHERE action = 'recommended')::int AS recommended,
                    COUNT(*) FILTER (WHERE action = 'hovered')::int AS hovered,
                    COUNT(*) FILTER (WHERE action = 'clicked')::int AS clicked,
                    COUNT(*) FILTER (WHERE action = 'purchased')::int AS purchased
                FROM recommendation_feedback
                WHERE store_id = $1 AND created_at > NOW() - INTERVAL '1 day' * $2
                GROUP BY source
            `, [storeId, days]);

            const sourceBreakdown = {};
            for (const r of sourceStats) {
                sourceBreakdown[r.source] = {
                    recommended: r.recommended,
                    hovered: r.hovered,
                    clicked: r.clicked,
                    purchased: r.purchased,
                    hoverRate: r.recommended > 0 ? Math.round((r.hovered / r.recommended) * 10000) / 10000 : 0,
                    ctr: r.recommended > 0 ? Math.round((r.clicked / r.recommended) * 10000) / 10000 : 0,
                    cvr: r.recommended > 0 ? Math.round((r.purchased / r.recommended) * 10000) / 10000 : 0
                };
            }

            // Current weights
            const weights = hybridService ? hybridService.getWeights() : null;

            // Nightly batch status
            const batchStatus = nightlyBatch ? nightlyBatch.getStatus() : null;

            res.json({
                success: true,
                data: {
                    period: { days, storeId },
                    funnel: {
                        totalRecommended,
                        totalHovered,
                        totalClicked,
                        totalAddedToCart,
                        totalPurchased
                    },
                    rates: {
                        hoverRate: totalRecommended > 0
                            ? Math.round((totalHovered / totalRecommended) * 10000) / 10000 : 0,
                        clickThroughRate: totalRecommended > 0
                            ? Math.round((totalClicked / totalRecommended) * 10000) / 10000 : 0,
                        addToCartRate: totalRecommended > 0
                            ? Math.round((totalAddedToCart / totalRecommended) * 10000) / 10000 : 0,
                        conversionRate: totalRecommended > 0
                            ? Math.round((totalPurchased / totalRecommended) * 10000) / 10000 : 0
                    },
                    sourceBreakdown,
                    currentWeights: weights,
                    lastBatchRun: batchStatus?.lastRunAt || null,
                    batchResult: batchStatus?.lastResult || null
                }
            });
        } catch (err) {
            next(err);
        }
    });

    /**
     * GET /api/chatbot/stats/latency?storeId=1
     * Pipeline latency metrics (from recent chat_message metadata)
     */
    router.get('/stats/latency', async (req, res, next) => {
        try {
            const storeId = parseInt(req.query.storeId) || 1;

            // Query recent metadata from chat messages (last 24h)
            const { rows } = await pool.query(`
                SELECT metadata
                FROM chat_message
                WHERE role = 'assistant'
                  AND metadata IS NOT NULL
                  AND metadata::text != 'null'
                  AND created_at > NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
                LIMIT 100
            `);

            if (rows.length === 0) {
                return res.json({
                    success: true,
                    data: {
                        sampleSize: 0,
                        message: 'No recent chat messages with metadata found'
                    }
                });
            }

            const latencies = { total: [], hybrid: [], generation: [], embedding: [] };

            for (const row of rows) {
                const meta = typeof row.metadata === 'string' ? JSON.parse(row.metadata) : row.metadata;
                if (!meta?.totalLatencyMs) continue;

                latencies.total.push(meta.totalLatencyMs);
                if (meta.steps?.hybrid?.latencyMs) latencies.hybrid.push(meta.steps.hybrid.latencyMs);
                if (meta.steps?.generation?.latencyMs) latencies.generation.push(meta.steps.generation.latencyMs);
                if (meta.steps?.embedding?.latencyMs) latencies.embedding.push(meta.steps.embedding.latencyMs);
            }

            const calc = (arr) => {
                if (arr.length === 0) return { avg: 0, p95: 0, min: 0, max: 0 };
                const sorted = [...arr].sort((a, b) => a - b);
                return {
                    avg: Math.round(sorted.reduce((s, v) => s + v, 0) / sorted.length),
                    p95: sorted[Math.floor(sorted.length * 0.95)] || sorted[sorted.length - 1],
                    min: sorted[0],
                    max: sorted[sorted.length - 1]
                };
            };

            res.json({
                success: true,
                data: {
                    sampleSize: latencies.total.length,
                    period: 'last 24 hours',
                    total: calc(latencies.total),
                    hybrid: calc(latencies.hybrid),
                    generation: calc(latencies.generation),
                    embedding: calc(latencies.embedding)
                }
            });
        } catch (err) {
            next(err);
        }
    });

    // ── Phase 5: Feedback Stream ──

    /**
     * GET /api/chatbot/stats/feedback-stream?storeId=1&limit=50&source=content&recency=1h
     * Recent recommendation interactions for live dashboard (filtered by source and recency)
     */
    router.get('/stats/feedback-stream', async (req, res, next) => {
        try {
            const storeId = parseInt(req.query.storeId) || 1;
            const limit = Math.min(parseInt(req.query.limit) || 50, 100);
            const source = req.query.source;
            const recency = req.query.recency;

            const RECENCY_MAP = {
                '30m': '30 minutes',
                '1h': '1 hour',
                '6h': '6 hours',
                '24h': '24 hours'
            };

            let query = `
                SELECT rf.id, rf.user_id, rf.product_id, rf.source, rf.action,
                       rf.recommendation_score, rf.created_at,
                       pkb.content AS product_info
                FROM recommendation_feedback rf
                LEFT JOIN product_knowledge_base pkb
                    ON pkb.product_id = rf.product_id AND pkb.store_id = rf.store_id
                WHERE rf.store_id = $1
            `;
            const params = [storeId];

            if (source && source !== 'all' && ['content', 'cf', 'apriori', 'session', 'organic'].includes(source)) {
                params.push(source);
                query += ` AND rf.source = $${params.length}`;
            }

            if (recency && recency !== 'all' && RECENCY_MAP[recency]) {
                query += ` AND rf.created_at > NOW() - INTERVAL '${RECENCY_MAP[recency]}'`;
            }

            params.push(limit);
            query += `
                ORDER BY rf.created_at DESC
                LIMIT $${params.length}
            `;

            const { rows } = await pool.query(query, params);

            // Extract product name from content field
            const feedbacks = rows.map(r => {
                let productName = `Product #${r.product_id}`;
                if (r.product_info) {
                    const match = r.product_info.match(/Sản phẩm "([^"]+)"/);
                    if (match) productName = match[1];
                }
                return {
                    id: r.id,
                    userId: r.user_id,
                    productId: r.product_id,
                    productName,
                    source: r.source,
                    action: r.action,
                    score: r.recommendation_score ? Number(r.recommendation_score) : null,
                    createdAt: r.created_at
                };
            });

            res.json({ success: true, data: { feedbacks } });
        } catch (err) {
            next(err);
        }
    });

    /**
     * GET /api/chatbot/stats/weight-history?storeId=1&limit=30
     * Ensemble weight change log for trend visualization
     */
    router.get('/stats/weight-history', async (req, res, next) => {
        try {
            const storeId = parseInt(req.query.storeId) || 1;
            const limit = Math.min(parseInt(req.query.limit) || 30, 90);

            const { rows } = await pool.query(`
                SELECT alpha, beta, gamma, delta, feedback_count,
                       trigger_type, created_at
                FROM ensemble_weights_history
                WHERE store_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            `, [storeId, limit]);

            // Reverse to chronological order for chart
            const history = rows.reverse().map(r => ({
                alpha: Number(r.alpha),
                beta: Number(r.beta),
                gamma: Number(r.gamma),
                delta: Number(r.delta),
                feedbackCount: r.feedback_count,
                triggerType: r.trigger_type,
                date: r.created_at
            }));

            res.json({ success: true, data: { history } });
        } catch (err) {
            next(err);
        }
    });

    /**
     * GET /api/chatbot/stats/cf-matrix?storeId=1
     * CF Matrix and Dual-Tracking statistics
     */
    router.get('/stats/cf-matrix', async (req, res, next) => {
        try {
            const storeId = parseInt(req.query.storeId) || 1;

            // 1. Interaction Matrix Density
            const { rows: densityRows } = await pool.query(`
                WITH counts AS (
                    SELECT 
                        COUNT(DISTINCT user_id)::float AS users,
                        COUNT(DISTINCT product_id)::float AS products,
                        COUNT(*)::float AS interactions
                    FROM user_product_interaction
                    WHERE store_id = $1 AND interaction_score > 0
                )
                SELECT 
                    users, products, interactions,
                    CASE WHEN users * products > 0 THEN interactions / (users * products) ELSE 0 END AS density
                FROM counts
            `, [storeId]);
            const density = densityRows[0] || { users: 0, products: 0, interactions: 0, density: 0 };

            // 2. Implicit Signals (Dual-Stream Breakdown)
            const { rows: signalRows } = await pool.query(`
                SELECT 
                    COUNT(*) FILTER (WHERE action = 'clicked')::int AS clicks,
                    COUNT(*) FILTER (WHERE action = 'added_to_cart')::int AS carts,
                    COUNT(*) FILTER (WHERE action = 'hovered')::int AS hovers,
                    COUNT(*) FILTER (WHERE source = 'organic')::int AS organic,
                    COUNT(*) FILTER (WHERE source != 'organic')::int AS chatbot
                FROM recommendation_feedback
                WHERE user_id IS NOT NULL AND store_id = $1
                  AND created_at > NOW() - INTERVAL '90 days'
            `, [storeId]);
            const signals = signalRows[0] || { clicks: 0, carts: 0, hovers: 0, organic: 0, chatbot: 0 };

            // 3. Similarity Quality
            const { rows: simRows } = await pool.query(`
                SELECT 
                    COUNT(*)::int AS total_pairs,
                    COUNT(*) FILTER (WHERE similarity >= 0.5)::int AS high,
                    COUNT(*) FILTER (WHERE similarity >= 0.2 AND similarity < 0.5)::int AS medium,
                    COUNT(*) FILTER (WHERE similarity >= 0.05 AND similarity < 0.2)::int AS low,
                    AVG(common_users)::float AS avg_common,
                    MAX(computed_at) AS last_computed
                FROM item_similarity
                WHERE store_id = $1
            `, [storeId]);
            const sim = simRows[0] || { total_pairs: 0, high: 0, medium: 0, low: 0, avg_common: 0, last_computed: null };

            res.json({
                success: true,
                data: {
                    interactionMatrix: {
                        totalUsers: density.users,
                        totalProducts: density.products,
                        totalInteractions: density.interactions,
                        density: density.density,
                        avgInteractionsPerUser: density.users > 0 ? density.interactions / density.users : 0
                    },
                    implicitSignals: {
                        totalClicks: signals.clicks,
                        totalCarts: signals.carts,
                        totalHovers: signals.hovers,
                        organicCount: signals.organic,
                        chatbotCount: signals.chatbot
                    },
                    similarityMatrix: {
                        totalPairs: sim.total_pairs,
                        highSimilarity: sim.high,
                        mediumSimilarity: sim.medium,
                        lowSimilarity: sim.low,
                        avgCommonUsers: sim.avg_common || 0,
                        lastComputedAt: sim.last_computed
                    }
                }
            });
        } catch (err) {
            next(err);
        }
    });

    /**
     * POST /api/chatbot/admin/force-learn
     * Trigger weight learning immediately (Admin only)
     */
    router.post('/admin/force-learn', async (req, res, next) => {
        try {
            if (!weightLearner) {
                return res.status(503).json({
                    success: false,
                    error: { message: 'WeightLearner not available' }
                });
            }

            const storeId = parseInt(req.body.storeId) || 1;
            const result = await weightLearner.learn(storeId, 'manual');

            // Refresh in-memory cache immediately
            if (!result.skipped && hybridService) {
                await hybridService.warmUp(storeId);
            }

            res.json({
                success: true,
                data: {
                    ...result,
                    message: result.skipped
                        ? `Skipped: only ${result.feedbackCount} feedbacks (need ${20})`
                        : 'Weights updated and cache refreshed'
                }
            });
        } catch (err) {
            next(err);
        }
    });

    /**
     * POST /api/chatbot/admin/run-batch
     * Trigger full nightly batch pipeline manually (Admin only)
     */
    router.post('/admin/run-batch', async (req, res, next) => {
        try {
            if (!nightlyBatch) {
                return res.status(503).json({
                    success: false,
                    error: { message: 'NightlyBatchPipeline not available' }
                });
            }

            const storeId = parseInt(req.body.storeId) || 1;
            const result = await nightlyBatch.run(storeId);

            res.json({
                success: true,
                data: {
                    ...result,
                    message: result.failCount === 0
                        ? `All 4 steps completed successfully in ${result.totalMs}ms`
                        : `Completed with ${result.failCount} failure(s) in ${result.totalMs}ms`
                }
            });
        } catch (err) {
            next(err);
        }
    });

    return router;
};
