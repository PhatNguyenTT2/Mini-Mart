/**
 * HybridRecommendationService — Orchestrator (Single Responsibility Principle)
 * 
 * Routes recommendation scoring through:
 *   - Step 0 (Fast Path): Deep Learning Two-Tower ONNX Model via AIClient
 *   - Graceful Fallback: Legacy White-box Ensemble (α/β/γ/δ) via LegacyFallbackService
 */
const logger = require('../../../../shared/common/logger');
const EventEmitter = require('events');
const LegacyFallbackService = require('./legacy.fallback.service');

class HybridRecommendationService extends EventEmitter {
    constructor({ copurchaseRepo, cfService, pool, aiClient = null, legacyFallback = null }) {
        super();
        this.copurchaseRepo = copurchaseRepo;
        this.cfService = cfService;
        this.pool = pool;
        this.aiClient = aiClient;
        this.legacyFallback = legacyFallback || new LegacyFallbackService({ copurchaseRepo, cfService, pool });
    }

    /**
     * Warm up caches (delegates to legacy fallback for White-box fallback readiness)
     */
    async warmUp(storeId) {
        await this.legacyFallback.warmUp(storeId);
    }

    /**
     * Orchestrate scoring: AI Fast Path -> Graceful Fallback
     */
    async score(contentResults, userId, storeId, customerType = 'retail', options = {}) {
        if (!contentResults || contentResults.length === 0) {
            return [];
        }

        // ── Step 0: Deep Learning ONNX Fast Path ──
        if (this.aiClient) {
            try {
                const contentPids = new Set(contentResults.map(r => Number(r.product_id)));
                const candidateIds = Array.from(contentPids);
                const contextPid = options.contextProductId ?? null;
                const personaCluster = options.personaCluster ?? null;

                // ── Step 0.5: Inject Apriori Cross-Sell Candidates (skip for general rec queries) ──
                const aprioriCandidates = options.isGeneralRecQuery ? [] : await this._getAprioriCandidates(contentResults, storeId);
                const aprioriPidMap = new Map(aprioriCandidates.map(c => [c.product_id, c]));
                const aprioriPids = aprioriCandidates.map(c => c.product_id);

                const expandedIds = [...new Set([...candidateIds, ...aprioriPids])];

                const aiRankings = await this.aiClient.scoreProducts({
                    storeId,
                    userId: userId ?? null,
                    personaCluster,
                    candidateProductIds: expandedIds,
                    contextProductId: contextPid
                });

                if (aiRankings && aiRankings.length > 0) {
                    const aiScoreMap = new Map(aiRankings.map(r => [Number(r.product_id), Number(r.ai_score)]));
                    if (aiScoreMap.size !== expandedIds.length || expandedIds.some(pid => !aiScoreMap.has(pid))) {
                        throw new Error('AI response omitted one or more candidates');
                    }

                    // Fetch metadata for injected Apriori candidates not present in contentResults
                    const missingPids = aprioriPids.filter(pid => !contentPids.has(pid));
                    const missingProductsMap = new Map();
                    if (missingPids.length > 0 && this.pool) {
                        try {
                            const { rows } = await this.pool.query(`
                                SELECT product_id, content, category_name, unit_price, is_in_stock,
                                       COALESCE(substring(content from 'Sản phẩm "([^"]+)"'), 'Product ' || product_id) AS product_name
                                FROM product_knowledge_base
                                WHERE product_id = ANY($1::int[]) AND store_id = $2
                            `, [missingPids, storeId]);
                            for (const row of rows) {
                                missingProductsMap.set(Number(row.product_id), row);
                            }
                        } catch (err) {
                            logger.warn({ err: err.message }, 'Hybrid: Failed to fetch metadata for Apriori candidates');
                        }
                    }

                    const results = expandedIds.map(pid => {
                        const isContent = contentPids.has(pid);
                        const contentObj = isContent ? contentResults.find(r => Number(r.product_id) === pid) : null;
                        const missingObj = missingProductsMap.get(pid);
                        const score = aiScoreMap.get(pid);

                        const rawProduct = contentObj || missingObj || { product_id: pid };

                        if (isContent) {
                            return {
                                product_id: pid,
                                final_score: score,
                                scores: { content: score, cf: 0, apriori: 0, personal: 0 },
                                sources: ['two_tower_onnx'],
                                topSource: 'two_tower_onnx',
                                rawProduct
                            };
                        } else {
                            return {
                                product_id: pid,
                                final_score: score,
                                scores: { content: 0, cf: 0, apriori: score, personal: 0 },
                                sources: ['two_tower_onnx', 'apriori'],
                                topSource: 'apriori',
                                rawProduct
                            };
                        }
                    });

                    results.sort((a, b) => b.final_score - a.final_score);
                    logger.debug({
                        ragCandidates: candidateIds.length,
                        aprioriInjected: aprioriPids.length,
                        totalCandidates: expandedIds.length,
                        topScore: results[0]?.final_score
                    }, 'Hybrid: Scored via AI Two-Tower ONNX with Apriori Injection');
                    return results;
                }
            } catch (err) {
                logger.warn({ err: err.message }, 'Hybrid: AI Fast Path failed — switching to Legacy Fallback');
            }
        }

        // ── Graceful Fallback: White-box Ensemble (α/β/γ/δ) ──
        return this.legacyFallback.score(contentResults, userId, storeId, customerType, options);
    }

    /**
     * Record feedback for weight learning & auditing
     */
    async recordFeedback(userId, productId, storeId, source, action, sessionId = null, score = null, metadata = null, sequenceOrder = 1) {
        try {
            const intervalVal = action === 'recommended' ? '5 minutes' : '30 minutes';
            if (userId && action !== 'purchased') {
                const { rows } = await this.pool.query(`
                    SELECT 1 FROM recommendation_feedback
                    WHERE user_id = $1 AND product_id = $2 AND store_id = $3
                      AND action = $4 AND source = $5
                      AND created_at > NOW() - INTERVAL '${intervalVal}'
                    LIMIT 1
                `, [userId, productId, storeId, action, source]);

                if (rows.length > 0) return;
            }

            const { rows: [inserted] } = await this.pool.query(`
                INSERT INTO recommendation_feedback 
                    (user_id, product_id, store_id, source, action, session_id, sequence_order, recommendation_score, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id, created_at
            `, [userId, productId, storeId, source, action, sessionId, sequenceOrder || 1, score,
                metadata ? JSON.stringify(metadata) : null]);

            if (inserted) {
                this.emit('feedback', {
                    id: inserted.id, userId, productId, storeId, source, action,
                    sessionId, sequenceOrder: sequenceOrder || 1, score, createdAt: inserted.created_at
                });
            }
        } catch (err) {
            logger.warn({ err }, 'Hybrid: Failed to record feedback');
        }
    }

    /**
     * Helper to extract top Apriori cross-sell candidates related to contentResults
     */
    async _getAprioriCandidates(contentResults, storeId, limit = 5) {
        if (!contentResults || contentResults.length === 0) return [];

        const contentPids = new Set(contentResults.map(r => Number(r.product_id)));
        const candidateMap = new Map();

        for (const r of contentResults) {
            const pid = Number(r.product_id);
            const cacheKey = `${pid}_${storeId}`;
            let related = this.legacyFallback?._aprioriCache?.get(cacheKey);

            if (!related && this.copurchaseRepo) {
                try {
                    const dbRelated = await this.copurchaseRepo.getRelatedProducts(pid, storeId, 3);
                    related = dbRelated.map(item => ({
                        product_id: Number(item.product_id_b),
                        confidence: Number(item.confidence) || 0,
                        lift: Number(item.lift) || 0
                    }));
                } catch (e) {
                    related = [];
                }
            }

            if (related && Array.isArray(related)) {
                for (const rel of related) {
                    const relPid = Number(rel.product_id);
                    if (contentPids.has(relPid)) continue; // skip items already in contentResults
                    if (rel.lift < 1.2) continue; // keep only positive associations

                    const existing = candidateMap.get(relPid);
                    if (!existing || rel.lift > existing.lift) {
                        candidateMap.set(relPid, rel);
                    }
                }
            }
        }

        const candidates = Array.from(candidateMap.values())
            .sort((a, b) => b.lift - a.lift)
            .slice(0, limit);

        return candidates;
    }

    getWeights() {
        return this.legacyFallback.getWeights();
    }
}

module.exports = HybridRecommendationService;
