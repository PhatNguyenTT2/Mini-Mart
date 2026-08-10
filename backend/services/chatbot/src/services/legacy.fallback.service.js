/**
 * LegacyFallbackService — Standalone White-box Ensemble (α/β/γ/δ)
 * 
 * Extracted from HybridRecommendationService to enforce Separation of Concerns (SRP).
 * Activated ONLY when AI Inference Microservice fails or Circuit Breaker is OPEN.
 * 
 * Formula:
 *   final_score = α×content + β×cf + γ×apriori + δ×personalization
 */
const logger = require('../../../../shared/common/logger');

const DEFAULT_WEIGHTS = { alpha: 0.40, beta: 0.25, gamma: 0.25, delta: 0.10 };

class LegacyFallbackService {
  constructor({ copurchaseRepo, cfService, pool }) {
    this.copurchaseRepo = copurchaseRepo;
    this.cfService = cfService;
    this.pool = pool;

    this._cfCache = new Map();       // `${userId}_${storeId}` → recommendations[]
    this._aprioriCache = new Map();  // `${productId}_${storeId}` → relatedProducts[]
    this._weights = { ...DEFAULT_WEIGHTS };
    this._cacheReady = false;
  }

  /**
   * Warm up caches — pre-load Apriori & CF similarities from DB
   */
  async warmUp(storeId) {
    const start = Date.now();
    try {
      const { rows } = await this.pool.query(
        'SELECT alpha, beta, gamma, delta FROM ensemble_weights WHERE store_id = $1',
        [storeId]
      );
      if (rows.length > 0) {
        this._weights = {
          alpha: Number(rows[0].alpha),
          beta: Number(rows[0].beta),
          gamma: Number(rows[0].gamma),
          delta: Number(rows[0].delta)
        };
      }

      const { rows: aprioriRows } = await this.pool.query(`
                SELECT product_id_a, product_id_b, co_purchase_count,
                       confidence_ab, confidence_ba, lift
                FROM co_purchase_stats
                WHERE store_id = $1::bigint AND co_purchase_count >= 3
                ORDER BY lift DESC
            `, [storeId]);

      this._aprioriCache.clear();
      for (const row of aprioriRows) {
        const keyA = `${row.product_id_a}_${storeId}`;
        const keyB = `${row.product_id_b}_${storeId}`;

        if (!this._aprioriCache.has(keyA)) this._aprioriCache.set(keyA, []);
        this._aprioriCache.get(keyA).push({
          product_id: Number(row.product_id_b),
          confidence: Number(row.confidence_ab) || 0,
          lift: Number(row.lift) || 0
        });

        if (!this._aprioriCache.has(keyB)) this._aprioriCache.set(keyB, []);
        this._aprioriCache.get(keyB).push({
          product_id: Number(row.product_id_a),
          confidence: Number(row.confidence_ba) || 0,
          lift: Number(row.lift) || 0
        });
      }

      const { rows: simRows } = await this.pool.query(`
                SELECT item_a, item_b, similarity
                FROM item_similarity
                WHERE store_id = $1 AND similarity >= 0.1
            `, [storeId]);

      this._cfCache.clear();
      this._cfCache.set('_similarities', simRows.map(r => ({
        itemA: Number(r.item_a),
        itemB: Number(r.item_b),
        similarity: Number(r.similarity)
      })));

      this._cacheReady = true;
      logger.info({
        storeId,
        weights: this._weights,
        aprioriPairs: aprioriRows.length,
        cfPairs: simRows.length,
        elapsed: `${Date.now() - start}ms`
      }, 'LegacyFallback: Cache warmed up');
    } catch (err) {
      logger.error({ err }, 'LegacyFallback: Cache warmup failed — using DB fallback');
    }
  }

  /**
   * White-box Ensemble scoring (Steps 1-5)
   */
  async score(contentResults, userId, storeId, customerType = 'retail', options = {}) {
    const { alpha, beta, gamma, delta } = this._weights;
    const scoreMap = new Map();

    // ── Step 1: Content scores ──
    const maxRRF = contentResults.length > 0
      ? Math.max(...contentResults.map(r => r.rrf_score || 0))
      : 1;

    for (const r of contentResults) {
      const pid = Number(r.product_id);
      const normalizedContent = maxRRF > 0 ? Math.max(0, (r.rrf_score || 0) / maxRRF) : 0;
      scoreMap.set(pid, {
        content: normalizedContent, cf: 0, apriori: 0, personal: 0,
        sources: ['content'], rawProduct: r
      });
    }

    // ── Step 2: CF scores ──
    let cfResults = [];
    if (userId && beta > 0 && this.cfService) {
      try {
        cfResults = await this.cfService.getRecommendations(
          userId, storeId, 10, options.excludePurchased !== false
        );
      } catch (err) {
        logger.warn({ err }, 'LegacyFallback: CF engine failed');
      }
    }

    if (cfResults.length > 0) {
      const maxCF = Math.max(...cfResults.map(r => r.prediction_score));
      for (const r of cfResults) {
        const pid = Number(r.product_id);
        const normalizedCF = maxCF > 0 ? r.prediction_score / maxCF : 0;

        if (scoreMap.has(pid)) {
          scoreMap.get(pid).cf = normalizedCF;
          scoreMap.get(pid).sources.push('cf');
        } else {
          scoreMap.set(pid, {
            content: 0, cf: normalizedCF, apriori: 0, personal: 0,
            sources: ['cf'], rawProduct: null
          });
        }
      }
    }

    // ── Step 3: Apriori scores ──
    if (gamma > 0) {
      const aprioriCandidates = new Map();

      for (const r of contentResults) {
        const pid = Number(r.product_id);
        const contentWeight = maxRRF > 0 ? Math.max(0, (r.rrf_score || 0) / maxRRF) : 0;
        const cacheKey = `${pid}_${storeId}`;
        let related = this._aprioriCache.get(cacheKey);

        if (!related && !this._cacheReady && this.copurchaseRepo) {
          try {
            related = await this.copurchaseRepo.getRelatedProducts(pid, storeId, 5);
            related = related.map(r => ({
              product_id: Number(r.product_id_b),
              confidence: Number(r.confidence) || 0,
              lift: Number(r.lift) || 0
            }));
          } catch (err) {
            related = [];
          }
        }

        if (related) {
          for (const rel of related) {
            const effectiveScore = rel.confidence * contentWeight;
            const existing = aprioriCandidates.get(rel.product_id);
            if (!existing || effectiveScore > existing.effectiveScore) {
              aprioriCandidates.set(rel.product_id, {
                confidence: rel.confidence,
                effectiveScore
              });
            }
          }
        }
      }

      for (const [pid, { effectiveScore }] of aprioriCandidates) {
        if (scoreMap.has(pid)) {
          scoreMap.get(pid).apriori = effectiveScore;
          scoreMap.get(pid).sources.push('apriori');
        } else {
          scoreMap.set(pid, {
            content: 0, cf: 0, apriori: effectiveScore, personal: 0,
            sources: ['apriori'], rawProduct: null
          });
        }
      }
    }

    // ── Step 4: Personalization bonus ──
    const personalBonus = customerType === 'vip' ? 1.0
      : customerType === 'wholesale' ? 0.8
        : 0.3;

    for (const entry of scoreMap.values()) {
      entry.personal = personalBonus;
    }

    // ── Step 5: Compute final ensemble score ──
    const results = [];
    for (const [pid, entry] of scoreMap) {
      let w = { ...this._weights };
      if (entry.cf === 0 && cfResults.length === 0) {
        w.alpha += w.beta;
        w.beta = 0;
      }

      const finalScore =
        w.alpha * entry.content +
        w.beta * entry.cf +
        w.gamma * entry.apriori +
        w.delta * entry.personal;

      const penalty = entry.apriori > 0 ? 0.75 : 0.5;
      const adjustedScore = entry.content > 0
        ? finalScore
        : finalScore * penalty;

      results.push({
        product_id: pid,
        final_score: Math.round(adjustedScore * 10000) / 10000,
        scores: {
          content: Math.round(entry.content * 10000) / 10000,
          cf: Math.round(entry.cf * 10000) / 10000,
          apriori: Math.round(entry.apriori * 10000) / 10000,
          personal: Math.round(entry.personal * 10000) / 10000
        },
        sources: entry.sources,
        topSource: this._getTopSource(entry, w),
        rawProduct: entry.rawProduct
      });
    }

    results.sort((a, b) => b.final_score - a.final_score);
    return results;
  }

  _getTopSource(entry, weights) {
    const contributions = {
      content: weights.alpha * entry.content,
      cf: weights.beta * entry.cf,
      apriori: weights.gamma * entry.apriori,
    };

    const sorted = Object.entries(contributions).sort((a, b) => b[1] - a[1]);
    const [topKey, topVal] = sorted[0];

    if (topKey !== 'cf' && contributions.cf > 0 && topVal > 0) {
      const cfRatio = contributions.cf / topVal;
      if (cfRatio >= 0.40) return 'cf';
    }

    return topKey;
  }

  getWeights() {
    return { ...this._weights };
  }
}

module.exports = LegacyFallbackService;
