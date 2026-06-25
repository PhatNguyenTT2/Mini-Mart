/**
 * WeightLearner — Adaptive Weight Learning (Phase 3)
 * 
 * Nightly batch job: học trọng số α/β/γ/δ từ recommendation_feedback.
 * 
 * Thuật toán:
 *   1. Query feedback WHERE action='purchased' trong 30 ngày
 *   2. conversion_rate(source) = purchased / recommended
 *   3. new_weight(source) = conversion_rate / SUM(all rates)
 *   4. Smoothing: 0.8 × current + 0.2 × new
 *   5. Clamp: [0.05, 0.60]
 */
const logger = require('../../../../shared/common/logger');

const SMOOTHING_FACTOR = 0.2;  // 20% new, 80% old
const MIN_WEIGHT = 0.05;
const MAX_WEIGHT = 0.60;
const MIN_FEEDBACK_COUNT = 20; // Don't adjust if < 20 feedbacks
const MIN_CONVERSED_SCORE = 1.0; // Min weighted conversion score (e.g. 1 purchase or 10 hovers)

class WeightLearner {
    constructor(pool) {
        this.pool = pool;
    }

    /**
     * Run weight learning for a store
     * @param {number} storeId
     * @param {string} triggerType - 'nightly' | 'manual'
     * @returns {object} { oldWeights, newWeights, feedbackCount }
     */
    async learn(storeId, triggerType = 'nightly') {
        logger.info({ storeId }, 'WeightLearner: Starting weight adjustment');

        // Step 1: Get current weights
        const { rows: currentRows } = await this.pool.query(
            'SELECT alpha, beta, gamma, delta FROM ensemble_weights WHERE store_id = $1',
            [storeId]
        );

        const current = currentRows.length > 0
            ? {
                alpha: Number(currentRows[0].alpha),
                beta: Number(currentRows[0].beta),
                gamma: Number(currentRows[0].gamma),
                delta: Number(currentRows[0].delta)
            }
            : { alpha: 0.40, beta: 0.25, gamma: 0.25, delta: 0.10 };

        // Step 2: Query conversion rates per source (last 30 days)
        // Data Isolation: Exclude 'organic' source to prevent Data Poisoning
        const { rows: feedbackStats } = await this.pool.query(`
            SELECT 
                source,
                COUNT(*) FILTER (WHERE action = 'recommended') AS recommended,
                COUNT(*) FILTER (WHERE action = 'purchased') AS purchased,
                COUNT(*) FILTER (WHERE action = 'clicked') AS clicked,
                COUNT(*) FILTER (WHERE action = 'added_to_cart') AS added_to_cart,
                COUNT(*) FILTER (WHERE action = 'hovered') AS hovered
            FROM recommendation_feedback
            WHERE store_id = $1 AND created_at > NOW() - INTERVAL '30 days'
              AND source IN ('content', 'cf', 'apriori')
            GROUP BY source
        `, [storeId]);

        // Organic ratio monitoring (non-blocking warning if organic feedback dominates >80%)
        try {
            const { rows: [{ organic_count }] } = await this.pool.query(`
                SELECT COUNT(*)::int AS organic_count
                FROM recommendation_feedback
                WHERE store_id = $1 AND created_at > NOW() - INTERVAL '30 days'
                  AND source = 'organic'
            `, [storeId]);
            const totalChatbot = feedbackStats.reduce(
                (sum, r) => sum + Number(r.recommended || 0), 0
            );
            const totalInteraction = totalChatbot + organic_count;
            const organicRatio = totalInteraction > 0 ? (organic_count / totalInteraction) : 0;
            if (organicRatio > 0.80) {
                logger.warn({ storeId, organicRatio: Math.round(organicRatio * 100) + '%', organic_count, chatbotFeedback: totalChatbot },
                    'WeightLearner: Organic feedback dominates (>80%). Consider increasing Chatbot engagement.');
            }
        } catch (e) {
            logger.warn({ err: e }, 'WeightLearner: Organic feedback ratio calculation failed (non-critical)');
        }

        const totalFeedback = feedbackStats.reduce(
            (sum, r) => sum + Number(r.recommended || 0), 0
        );

        if (totalFeedback < MIN_FEEDBACK_COUNT) {
            logger.info({ storeId, totalFeedback, minRequired: MIN_FEEDBACK_COUNT },
                'WeightLearner: Not enough feedback — keeping current weights');
            return { oldWeights: current, newWeights: current, feedbackCount: totalFeedback, skipped: true };
        }

        // Staleness check: Skip if no new interactions in last 24h
        const { rows: [{ fresh_count }] } = await this.pool.query(`
            SELECT COUNT(*)::int AS fresh_count
            FROM recommendation_feedback
            WHERE store_id = $1
              AND created_at > NOW() - INTERVAL '24 hours'
              AND source IN ('content', 'cf', 'apriori')
              AND action != 'recommended'
        `, [storeId]);

        if (fresh_count === 0) {
            logger.info({ storeId, totalFeedback },
                'WeightLearner: No fresh feedback in last 24h — keeping current weights');
            return { oldWeights: current, newWeights: current, feedbackCount: totalFeedback, skipped: true };
        }

        // Step 3: Compute conversion rates
        const sourceMap = { content: 'alpha', cf: 'beta', apriori: 'gamma' };
        const conversionRates = {};
        let totalRate = 0;

        for (const [source, weightKey] of Object.entries(sourceMap)) {
            const stat = feedbackStats.find(r => r.source === source);
            const recommended = Number(stat?.recommended || 0);
            const purchased = Number(stat?.purchased || 0);

            // Weighted conversion: purchase×1.0 + cart×0.5 + click×0.2 + hover×0.1
            const clicked = Number(stat?.clicked || 0);
            const addedToCart = Number(stat?.added_to_cart || 0);
            const hovered = Number(stat?.hovered || 0);
            const weightedConversions = purchased * 1.0 + addedToCart * 0.5 + clicked * 0.2 + hovered * 0.1;

            const rate = recommended > 0 ? weightedConversions / recommended : 0;
            conversionRates[weightKey] = rate;
            totalRate += rate;
        }

        // Guard rail: Require minimum conversion energy across ALL sources
        const totalWeightedConversions = feedbackStats.reduce(
            (sum, r) => {
                const purchased = Number(r.purchased || 0);
                const addedToCart = Number(r.added_to_cart || 0);
                const clicked = Number(r.clicked || 0);
                const hovered = Number(r.hovered || 0);
                return sum + (purchased * 1.0 + addedToCart * 0.5 + clicked * 0.2 + hovered * 0.1);
            }, 0
        );

        if (totalWeightedConversions < MIN_CONVERSED_SCORE) {
            logger.info({ storeId, totalWeightedConversions, minRequired: MIN_CONVERSED_SCORE },
                'WeightLearner: Insufficient conversion signals — keeping current weights');
            return { oldWeights: current, newWeights: current, feedbackCount: totalFeedback, skipped: true };
        }

        if (totalRate === 0) {
            logger.info({ storeId }, 'WeightLearner: Zero conversion rate — keeping current');
            return { oldWeights: current, newWeights: current, feedbackCount: totalFeedback, skipped: true };
        }

        // Step 4: Compute new weights (normalize rates, keep δ separate)
        const deltaWeight = current.delta; // Personalization stays manual
        const availableWeight = 1.0 - deltaWeight;

        const rawNew = {};
        for (const key of ['alpha', 'beta', 'gamma']) {
            rawNew[key] = (conversionRates[key] / totalRate) * availableWeight;
        }

        // Step 5: Smoothing + Clamp
        const newWeights = { delta: deltaWeight };
        for (const key of ['alpha', 'beta', 'gamma']) {
            let smoothed = (1 - SMOOTHING_FACTOR) * current[key] + SMOOTHING_FACTOR * rawNew[key];
            smoothed = Math.max(MIN_WEIGHT, Math.min(MAX_WEIGHT, smoothed));
            newWeights[key] = Math.round(smoothed * 10000) / 10000;
        }

        // Re-normalize to ensure sum = 1.0
        const sum = newWeights.alpha + newWeights.beta + newWeights.gamma + newWeights.delta;
        if (Math.abs(sum - 1.0) > 0.001) {
            const scale = (1.0 - newWeights.delta) / (newWeights.alpha + newWeights.beta + newWeights.gamma);
            newWeights.alpha = Math.round(newWeights.alpha * scale * 10000) / 10000;
            newWeights.beta = Math.round(newWeights.beta * scale * 10000) / 10000;
            newWeights.gamma = Math.round(newWeights.gamma * scale * 10000) / 10000;
        }

        // Step 6: Persist current weights
        await this.pool.query(`
            INSERT INTO ensemble_weights (store_id, alpha, beta, gamma, delta, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            ON CONFLICT (store_id)
            DO UPDATE SET alpha = $2, beta = $3, gamma = $4, delta = $5, updated_at = NOW()
        `, [storeId, newWeights.alpha, newWeights.beta, newWeights.gamma, newWeights.delta]);

        // Step 7: Log to history for trend visualization (Phase 5)
        try {
            await this.pool.query(`
                INSERT INTO ensemble_weights_history
                    (store_id, alpha, beta, gamma, delta, feedback_count, trigger_type)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            `, [storeId, newWeights.alpha, newWeights.beta, newWeights.gamma,
                newWeights.delta, totalFeedback, triggerType]);
        } catch (histErr) {
            logger.warn({ histErr }, 'WeightLearner: Failed to log history (non-critical)');
        }

        logger.info({
            storeId,
            old: current,
            new: newWeights,
            conversionRates,
            totalFeedback
        }, 'WeightLearner: Weights adjusted');

        return { oldWeights: current, newWeights, feedbackCount: totalFeedback, skipped: false };
    }
}

module.exports = WeightLearner;
