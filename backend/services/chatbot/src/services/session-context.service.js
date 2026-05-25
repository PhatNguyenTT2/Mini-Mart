/**
 * SessionContextService — Rule-based Session Intent Detection (Phase 3B1)
 * 
 * Phân tích chuỗi products trong phiên chat hiện tại để nhận diện
 * "ý định" của user (đang nấu lẩu? chuẩn bị bữa sáng? mua nhậu?).
 * 
 * Khi nhận diện được cluster → boost products cùng cluster trong ensemble.
 */
const logger = require('../../../../shared/common/logger');

// Category-driven cluster definitions (scalable, no magic product IDs)
const CLUSTER_DEFINITIONS = {
    lau_bo: {
        name: 'Lẩu Bò / Nấu ăn',
        categoryNames: [
            'Rau lá', 'Rau củ', 'Thịt heo', 'Thịt bò',
            'Bún, phở tươi', 'Gia vị tẩm ướp'
        ],
        keywords: ['lẩu', 'bò', 'nấm', 'rau', 'nấu', 'gia vị', 'bún'],
        boost: 0.15
    },
    bua_sang: {
        name: 'Bữa Sáng / Ăn nhẹ',
        categoryNames: ['Trứng', 'Chế biến sẵn', 'Sữa tươi', 'Bánh mì & Bánh ngọt'],
        keywords: ['sáng', 'bánh mì', 'sữa', 'trứng', 'sandwich', 'xúc xích'],
        boost: 0.12
    },
    an_vat: {
        name: 'Ăn vặt / Sinh viên',
        categoryNames: ['Mì ăn liền', 'Nước ngọt có ga', 'Snack & Đồ nhắm'],
        keywords: ['mì', 'snack', 'nước ngọt', 'ăn vặt', 'gói', 'coca'],
        boost: 0.12
    },
    nhau: {
        name: 'Nhậu / Giải khát',
        categoryNames: ['Bia', 'Nước ngọt có ga', 'Snack & Đồ nhắm'],
        keywords: ['bia', 'nhậu', 'khô', 'đậu phộng', 'mồi', 'giải khát'],
        boost: 0.15
    },
    gia_vi: {
        name: 'Gia vị / Nêm nếm',
        categoryNames: ['Dầu ăn', 'Gia vị tẩm ướp', 'Nước chấm'],
        keywords: ['gia vị', 'nước mắm', 'muối', 'đường', 'bột ngọt', 'hạt nêm', 'dầu ăn'],
        boost: 0.10
    }
};

class SessionContextService {
    constructor() {
        // Resolved at warmup: map from categoryNames → productIds
        this._clusters = null;
    }

    async warmUp(pool, storeId) {
        try {
            // Load product→category mapping from knowledge base (1 query, no cross-DB join)
            const { rows } = await pool.query(`
                SELECT product_id, category_name
                FROM product_knowledge_base
                WHERE store_id = $1 AND is_in_stock = TRUE
            `, [storeId]);

            // Build resolved clusters with real product IDs
            this._clusters = {};
            for (const [key, def] of Object.entries(CLUSTER_DEFINITIONS)) {
                const productIds = rows
                    .filter(r => def.categoryNames.includes(r.category_name))
                    .map(r => Number(r.product_id));
                this._clusters[key] = { ...def, productIds };
            }

            logger.info({
                storeId,
                clusters: Object.fromEntries(
                    Object.entries(this._clusters).map(([k, v]) => [k, v.productIds.length])
                )
            }, 'Session: Clusters warmed up (category-driven)');
        } catch (error) {
            logger.error({ error, storeId }, 'Session: Failed to warm up clusters');
            throw error;
        }
    }

    /**
     * Extract product IDs mentioned/recommended in chat history
     * @param {object[]} chatHistory - array of { role, content, productIds? }
     * @returns {number[]} ordered product IDs from session
     */
    extractProductSequence(chatHistory) {
        if (!chatHistory?.length) return [];

        const sequence = [];
        const seen = new Set();

        for (const msg of chatHistory) {
            // From structured productIds (if available)
            if (msg.productIds && Array.isArray(msg.productIds)) {
                for (const pid of msg.productIds) {
                    const id = Number(pid);
                    if (!seen.has(id)) {
                        sequence.push(id);
                        seen.add(id);
                    }
                }
            }

            // From text content (pattern: "Product #XX" or product names)
            if (msg.content) {
                const productRefs = msg.content.match(/Product\s*#(\d+)/gi);
                if (productRefs) {
                    for (const ref of productRefs) {
                        const id = Number(ref.match(/\d+/)[0]);
                        if (!seen.has(id)) {
                            sequence.push(id);
                            seen.add(id);
                        }
                    }
                }
            }
        }

        return sequence;
    }

    /**
     * Infer session intent from product sequence + message text
     * @param {number[]} productSequence - ordered product IDs
     * @param {string} lastMessage - latest user message
     * @param {object} pool - PG database pool for dynamic category resolution
     * @param {number} storeId
     * @returns {Promise<{ cluster: string, name: string, confidence: number, boost: number } | null>}
     */
    async inferSessionIntent(productSequence, lastMessage = '', pool = null, storeId = 1) {
        const scores = {};
        const activeClusters = CLUSTER_DEFINITIONS;

        // Resolve product categories from DB if productSequence has items and pool is provided
        const productCategories = new Map(); // pid -> categoryName
        if (productSequence && productSequence.length > 0 && pool) {
            try {
                const pids = productSequence.map(id => Number(id));
                const { rows } = await pool.query(`
                    SELECT product_id, category_name
                    FROM product_knowledge_base
                    WHERE product_id = ANY($1::bigint[]) AND store_id = $2
                `, [pids, storeId]);
                rows.forEach(r => {
                    productCategories.set(Number(r.product_id), r.category_name);
                });
            } catch (err) {
                logger.warn({ err }, 'Session Context: Failed to resolve product categories for sequence');
            }
        }

        // Score by product matches
        for (const [clusterKey, cluster] of Object.entries(activeClusters)) {
            let productHits = 0;
            for (const pid of productSequence) {
                const cat = productCategories.get(pid);
                if (cat && cluster.categoryNames.includes(cat)) {
                    productHits++;
                }
            }

            // Score by keyword matches in message (boundary-safe for Vietnamese)
            let keywordHits = 0;
            if (lastMessage) {
                const msgLower = lastMessage.toLowerCase();
                for (const kw of cluster.keywords) {
                    const regex = new RegExp(`(^|[^a-z0-9àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ])${kw}([^a-z0-9àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]|$)`, 'i');
                    if (regex.test(msgLower)) {
                        keywordHits++;
                    }
                }
            }

            // Weighted: product match = 2, keyword match = 1
            const totalScore = productHits * 2 + keywordHits;
            if (totalScore > 0) {
                scores[clusterKey] = totalScore;
            }
        }

        if (Object.keys(scores).length === 0) return null;

        // Find top cluster
        const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
        const [topKey, topScore] = sorted[0];
        const secondScore = sorted.length > 1 ? sorted[1][1] : 0;

        // Confidence: how dominant is the top cluster?
        const totalAllScores = Object.values(scores).reduce((s, v) => s + v, 0);
        const confidence = totalAllScores > 0 ? topScore / totalAllScores : 0;

        // If top cluster is not clearly dominant, mark as "exploring"
        if (confidence < 0.4 || (secondScore > 0 && topScore / secondScore < 1.5)) {
            return {
                cluster: 'exploring',
                name: 'Đang khám phá',
                confidence: Math.round(confidence * 100) / 100,
                boost: 0
            };
        }

        const cluster = activeClusters[topKey];
        return {
            cluster: topKey,
            name: cluster.name,
            confidence: Math.round(confidence * 100) / 100,
            boost: cluster.boost
        };
    }

    /**
     * Apply session context boost to ensemble results
     * @param {object[]} ensembleResults - from hybrid.service score()
     * @param {object|null} sessionIntent - from inferSessionIntent()
     * @returns {object[]} re-sorted results with session boost applied
     */
    applySessionBoost(ensembleResults, sessionIntent) {
        if (!sessionIntent || sessionIntent.cluster === 'exploring') {
            return ensembleResults;
        }

        const clusterDef = CLUSTER_DEFINITIONS[sessionIntent.cluster];
        if (!clusterDef) return ensembleResults;

        const categoryNames = clusterDef.categoryNames || [];

        const boostedResults = ensembleResults.map(r => {
            const category = r.rawProduct?.category_name || r.category_name || r.categoryName || '';
            const inCluster = categoryNames.includes(category);
            const boostedScore = inCluster
                ? r.final_score + sessionIntent.boost
                : r.final_score;

            return {
                ...r,
                final_score: Math.round(boostedScore * 10000) / 10000,
                session_boosted: inCluster,
                session_cluster: inCluster ? sessionIntent.cluster : null
            };
        });

        boostedResults.sort((a, b) => b.final_score - a.final_score);

        logger.info({
            cluster: sessionIntent.cluster,
            confidence: sessionIntent.confidence,
            boostedCount: boostedResults.filter(r => r.session_boosted).length
        }, 'Session: Context boost applied');

        return boostedResults;
    }
}

module.exports = SessionContextService;
