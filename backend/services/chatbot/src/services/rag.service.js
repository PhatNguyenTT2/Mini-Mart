/**
 * RAGService — Advanced RAG Pipeline
 * Step 1: Query Reformulation
 * Step 2: Embed query (Vietnamese SBERT)
 * Step 3: Hybrid Search (Semantic + Keyword in parallel)
 * Step 4: RRF Fusion → Top 5
 * Step 5: Co-purchase Enrichment
 * Step 6: Personalization
 * Step 5: Hybrid Ensemble (Phase 3: α×Content + β×CF + γ×Apriori + δ×Personal)
 * Step 6: Session Context Boost (Phase 3B: rule-based cluster detection)
 * Step 7: Augmented Generation (Qwen/Qwen2.5-7B-Instruct)
 */
const logger = require('../../../../shared/common/logger');
const { getPersonalizationContext, getCoPurchaseContext, getCFHint } = require('./context.helper');

// Vietnamese stop words + common action verbs that don't appear in product content
// plainto_tsquery('simple', ...) uses AND, so these extra tokens cause zero matches
const VN_STOP_WORDS = new Set([
    'tôi', 'tui', 'mình', 'bạn', 'anh', 'chị', 'em',
    'muốn', 'cần', 'tìm', 'mua', 'bán', 'cho', 'xin', 'hỏi',
    'có', 'không', 'là', 'và', 'của', 'để', 'với', 'trong', 'ngoài',
    'được', 'rồi', 'nhé', 'nha', 'ạ', 'vậy', 'thì', 'nào', 'gì',
    'hãy', 'đi', 'lại', 'ra', 'vào', 'lên', 'xuống',
    'gợi', 'ý', 'giới', 'thiệu', 'recommend', 'suggest',
    'ơi', 'à', 'ừ', 'ok', 'vâng', 'dạ', 'hey', 'hi', 'hello',
    'shop', 'cửa', 'hàng', 'siêu', 'thị'
]);

const cleanQueryForKeyword = (query) => {
    if (!query) return query;
    const cleaned = query
        .toLowerCase()
        .split(/\s+/)
        .filter(w => w.length > 0 && !VN_STOP_WORDS.has(w))
        .join(' ')
        .trim();
    // Fallback to original if everything was stripped
    return cleaned.length >= 2 ? cleaned : query;
};

// Helper: bỏ dấu tiếng Việt bằng Unicode NFD decomposition
const removeAccents = (str) => {
    if (!str) return '';
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
};

// Helper: lọc sản phẩm dựa trên text phản hồi của LLM
const syncProductsWithResponse = (products, reply) => {
    if (!reply) return products.slice(0, 3);

    const mutualContent = removeAccents(reply.toLowerCase());

    const mentionedProducts = products.filter(p => {
        const source = p.top_source || p.topSource || p.source;
        if (source && source !== 'content') return true;

        const name = p.content?.match(/"([^"]+)"/)?.[1] || p.name || '';
        if (!name) return false;

        const normalizedName = removeAccents(name.toLowerCase());

        // Match 1: Full name
        if (mutualContent.includes(normalizedName)) return true;

        // Match 2: Partial — ≥3 từ đầu (LLM hay viết tắt tên SP)
        const words = normalizedName.split(/\s+/);
        if (words.length >= 3) {
            const partial = words.slice(0, 3).join(' ');
            if (mutualContent.includes(partial)) return true;
        }

        // Match 3: Bigram minimum (≥2 từ) — KHÔNG dùng single-word
        // để tránh trúng các danh từ chung phổ biến: "Nước", "Bánh", "Kẹo", "Thịt"
        if (words.length >= 2) {
            const bigram = words.slice(0, 2).join(' ');
            if (mutualContent.includes(bigram)) return true;
        }

        return false;
    });

    return mentionedProducts.length > 0 ? mentionedProducts : products.slice(0, 3);
};

// Helper: phát hiện câu hỏi ngoài phạm vi nghiệp vụ siêu thị (đồ công nghệ - TC-06)
const detectOutOfScopeQuery = (message) => {
    if (!message) return null;
    const msg = message.toLowerCase();
    const techKeywords = [
        'iphone', 'samsung', 'oppo', 'xiaomi', 'nokia', 'ipad', 'macbook',
        'laptop', 'máy tính', 'điện thoại', 'tivi', 'television', 'tai nghe',
        'sạc dự phòng', 'chuột máy tính', 'bàn phím', 'công nghệ', 'đồ công nghệ'
    ];
    const isTech = techKeywords.some(kw => msg.includes(kw));
    if (isTech) {
        return 'Dạ siêu thị POSMART hiện tại chỉ chuyên cung cấp thực phẩm và đồ tiêu dùng nhanh, không kinh doanh mặt hàng đồ công nghệ ạ. Bạn có muốn tham khảo các loại nước ngọt hoặc đồ ăn vặt không?';
    }
    return null;
};

class RAGService {
    constructor({ knowledgeRepo, copurchaseRepo, cfService, hybridService, sessionContextService, embeddingClient, hfClient, apiClient, reformulator }) {
        this.knowledgeRepo = knowledgeRepo;
        this.copurchaseRepo = copurchaseRepo;
        this.cfService = cfService || null;
        this.hybridService = hybridService || null;
        this.sessionContextService = sessionContextService || null;
        this.embeddingClient = embeddingClient;
        this.hfClient = hfClient;
        this.apiClient = apiClient;
        this.reformulator = reformulator;
    }

    /**
     * Main RAG pipeline — recommend products
     * @param {string} userMessage - original user message
     * @param {number} storeId - current store (multi-tenancy)
     * @param {number|null} customerId - for personalization
     * @param {object[]} chatHistory - recent chat messages
     * @returns {object} { content, productIds, products, metadata }
     */
    async recommend(userMessage, storeId, customerId = null, chatHistory = []) {
        const startTime = Date.now();
        const metadata = { steps: {} };

        // Intercept out of scope queries immediately (TC-06)
        const outOfScopeResponse = detectOutOfScopeQuery(userMessage);
        if (outOfScopeResponse) {
            return {
                content: outOfScopeResponse,
                productIds: [],
                products: [],
                metadata: { outOfScope: true, totalLatencyMs: Date.now() - startTime }
            };
        }

        try {
            // Step 1: Query Reformulation
            const stepStart1 = Date.now();
            const query = await this.reformulator.reformulate(userMessage, chatHistory);
            metadata.steps.reformulation = {
                original: userMessage,
                reformulated: query,
                changed: query !== userMessage,
                latencyMs: Date.now() - stepStart1
            };

            // Step 2: Embed query
            const stepStart2 = Date.now();
            const queryVector = await this.embeddingClient.embed(query);
            metadata.steps.embedding = { latencyMs: Date.now() - stepStart2 };

            // Step 3: Hybrid Search (parallel)
            const stepStart3 = Date.now();
            const keywordQuery = cleanQueryForKeyword(query);
            const [rawSemanticResults, keywordResults] = await Promise.all([
                this.knowledgeRepo.searchSemantic(queryVector, storeId, 30),
                this.knowledgeRepo.searchKeyword(keywordQuery, storeId, 30)
            ]);

            // Step 3.5: Semantic Quality Gate
            // SBERT scores < 0.3 are near-random noise for Vietnamese product descriptions.
            // When semantic confidence is low, trust keyword search exclusively.
            const SEMANTIC_THRESHOLD = 0.3;
            const semanticResults = rawSemanticResults.filter(r => Number(r.score) >= SEMANTIC_THRESHOLD);

            metadata.steps.search = {
                semanticCount: rawSemanticResults.length,
                semanticAfterFilter: semanticResults.length,
                semanticThreshold: SEMANTIC_THRESHOLD,
                topSemanticScore: rawSemanticResults.length > 0 ? Number(rawSemanticResults[0].score).toFixed(4) : null,
                keywordCount: keywordResults.length,
                keywordQuery,
                latencyMs: Date.now() - stepStart3
            };

            // Step 4: RRF Fusion
            const fused = this._reciprocalRankFusion(semanticResults, keywordResults);

            // Step 4.5: Anchor Category Re-ranking
            // Use Top 1 RRF result's category as "anchor" — boost same-category, penalize others
            // NOTE: Use proportional boost/penalty to avoid making rrf_score negative
            // (keyword-only RRF scores ≈ 0.016 with k=60, fixed penalties would dominate)
            if (fused.length > 1) {
                const queryLower = query.toLowerCase();
                const anchorCategories = new Set();

                const catKeywords = {
                    'rau': ['Rau lá', 'Rau củ'],
                    'nấm': ['Rau củ', 'Nông sản khô'],
                    'thịt bò': ['Thịt bò'],
                    'thịt heo': ['Thịt heo'],
                    'trứng': ['Trứng'],
                    'cá': ['Hải sản', 'Thực phẩm đông lạnh'],
                    'tôm': ['Hải sản'],
                    'mực': ['Hải sản'],
                    'bún': ['Bún, phở tươi', 'Thức ăn chế biến, bún tươi'],
                    'phở': ['Bún, phở tươi', 'Phở, bún khô'],
                    'mì': ['Mì ăn liền'],
                    'sữa': ['Sữa tươi', 'Sữa chua & Phô mai'],
                    'bia': ['Bia'],
                    'nước ngọt': ['Nước ngọt có ga'],
                    'coca': ['Nước ngọt có ga'],
                    'pepsi': ['Nước ngọt có ga'],
                    'bánh mì': ['Bánh mì & Bánh ngọt'],
                    'bánh': ['Bánh mì & Bánh ngọt', 'Bánh quy & Kẹo'],
                    'kẹo': ['Bánh quy & Kẹo'],
                    'snack': ['Snack & Đồ nhắm'],
                    'bim bim': ['Snack & Đồ nhắm'],
                    'gia vị': ['Gia vị tẩm ướp'],
                    'nước mắm': ['Nước chấm'],
                    'nước tương': ['Nước chấm']
                };

                for (const [kw, cats] of Object.entries(catKeywords)) {
                    if (queryLower.includes(kw)) {
                        for (const c of cats) {
                            if (fused.some(item => item.category_name === c)) {
                                anchorCategories.add(c);
                            }
                        }
                    }
                }

                // Fallback to top RRF result's category if none detected via keywords
                if (anchorCategories.size === 0 && fused[0].category_name) {
                    anchorCategories.add(fused[0].category_name);
                }

                if (anchorCategories.size > 0) {
                    const maxScore = Math.max(...fused.map(r => r.rrf_score || 0));
                    const BOOST = maxScore * 0.5;    // +50% of max score
                    const PENALTY = maxScore * 0.2;  // -20% of max score

                    for (const item of fused) {
                        if (anchorCategories.has(item.category_name)) {
                            item.rrf_score += BOOST;
                        } else {
                            item.rrf_score = Math.max(0, item.rrf_score - PENALTY);
                        }
                    }
                    fused.sort((a, b) => b.rrf_score - a.rrf_score);

                    metadata.steps.anchorRerank = {
                        anchorCategories: Array.from(anchorCategories),
                        boost: BOOST.toFixed(4),
                        penalty: PENALTY.toFixed(4),
                        maxScoreBase: maxScore.toFixed(4)
                    };
                }
            }

            const top5 = fused.slice(0, 5);

            metadata.steps.fusion = {
                totalCandidates: fused.length,
                top5Scores: top5.map(r => ({ productId: r.product_id, rrfScore: r.rrf_score.toFixed(4) }))
            };

            if (top5.length === 0) {
                return this._buildNoResultsResponse(userMessage, storeId, startTime, metadata);
            }

            // ── Phase 3: Hybrid Ensemble (replaces separate CF/Apriori steps) ──
            let hybridResults = null;
            let sessionIntent = null;

            if (this.hybridService) {
                // Step 5: Hybrid Ensemble
                const stepStart5 = Date.now();
                const customerContext = await getPersonalizationContext(this.apiClient, customerId);

                hybridResults = await this.hybridService.score(
                    top5, customerId, storeId, customerContext.type
                );

                logger.info({
                    top5Ids: top5.map(r => r.product_id),
                    hybridAll: hybridResults.map(r => ({ pid: r.product_id, score: r.final_score, src: r.topSource, contentScore: r.scores?.content }))
                }, '[DEBUG] Hybrid scoring input/output');

                // Step 6: Session Context Boost
                if (this.sessionContextService && chatHistory.length > 0) {
                    const productSequence = this.sessionContextService.extractProductSequence(chatHistory);
                    sessionIntent = await this.sessionContextService.inferSessionIntent(
                        productSequence, query, this.knowledgeRepo.pool, storeId
                    );
                    if (sessionIntent) {
                        hybridResults = this.sessionContextService.applySessionBoost(hybridResults, sessionIntent);

                        // Attribute session-boosted products for feedback tracking
                        // Only override topSource for CF-only products (content=0).
                        // Content-matched products keep 'content' attribution — the user's query was the primary signal.
                        if (sessionIntent.cluster !== 'exploring') {
                            for (const r of hybridResults) {
                                if (r.session_boosted) {
                                    if (!r.sources.includes('session')) r.sources.push('session');
                                    // Only override topSource if content was NOT the primary match
                                    if (r.scores?.content === 0) {
                                        r.topSource = 'session';
                                    }
                                }
                            }
                        }
                    }
                }

                metadata.steps.hybrid = {
                    engine: 'ensemble',
                    weights: this.hybridService.getWeights(),
                    resultCount: hybridResults.length,
                    sessionCluster: sessionIntent?.cluster || null,
                    latencyMs: Date.now() - stepStart5
                };
                metadata.steps.personalization = {
                    customerType: customerContext.type,
                    latencyMs: 0 // included in hybrid step
                };

                // Re-rank top5 by ensemble score with partitioned ranking:
                // Content-matched → Slots 1-3, then dedicated Apriori + CF slots.
                const contentIds = new Set(top5.map(r => Number(r.product_id)));
                const contentMatched = hybridResults.filter(r => contentIds.has(r.product_id));

                // Detect broad category queries — disable cross-sell injection to eliminate noise.
                const contentCategories = new Set(
                    contentMatched.map(r => r.rawProduct?.category_name).filter(Boolean)
                );
                const isGeneralRecQuery = /gợi ý vài món|đề xuất vài món|gợi ý cho tôi|gợi ý các món|gợi ý sản phẩm/i.test(query.toLowerCase()) ||
                    (query.toLowerCase().includes('gợi ý') && query.toLowerCase().includes('món')) ||
                    (query.toLowerCase().includes('đề xuất') && query.toLowerCase().includes('món')) ||
                    (query.toLowerCase().trim() === 'gợi ý cho tôi vài món' || query.toLowerCase().includes('vài món'));
                const hasStrongAnchor = top5.length > 0 && top5[0].score >= 0.83;
                const isBroadQuery = !isGeneralRecQuery && !hasStrongAnchor && (contentCategories.size >= 3 || /đồ ăn vặt|ăn vặt|bánh kẹo/i.test(query.toLowerCase()));

                // Pick best Apriori candidates from non-content pool.
                const MIN_NON_CONTENT_SCORE = 0.12;
                const MIN_APRIORI_SCORE = 0.04;
                const nonContent = hybridResults.filter(r => !contentIds.has(r.product_id));
                const withApriori = nonContent
                    .filter(r => r.scores?.apriori > 0 && r.final_score >= MIN_APRIORI_SCORE)
                    .sort((a, b) => b.scores.apriori - a.scores.apriori);

                // Use anchor category from the rerank step (key is anchorCategories, plural)
                // Fallback to direct category_name on top5[0] (from pgvector search results)
                const anchorCategorySet = new Set(
                    metadata.steps.anchorRerank?.anchorCategories || []
                );
                if (anchorCategorySet.size === 0 && top5[0]?.category_name) {
                    anchorCategorySet.add(top5[0].category_name);
                }
                const anchorCategory = anchorCategorySet.size > 0 ? [...anchorCategorySet][0] : null;
                const anchorMatched = anchorCategory
                    ? contentMatched.filter(r => anchorCategorySet.has(r.rawProduct?.category_name))
                    : [];
                const otherContent = anchorCategory
                    ? contentMatched.filter(r => !anchorCategorySet.has(r.rawProduct?.category_name))
                    : contentMatched;

                // Detect transactional query: uses lower threshold (0.78) than hasStrongAnchor (0.83)
                // to catch queries like "mua bia Heineken" (score ~0.80) that are clearly transactional
                const hasAnchorIntent = top5.length > 0 && top5[0].score >= 0.78;
                const isTransactionalQuery = hasAnchorIntent && anchorMatched.length > 0;

                // Gating: Expand Apriori slots for transactional, suppress CF
                const aprioriPick = isBroadQuery ? [] : withApriori.slice(0, isTransactionalQuery ? 2 : 1);
                const aprioriPickIds = new Set(aprioriPick.map(r => r.product_id));
                const cfOnlyProducts = nonContent
                    .filter(r => !aprioriPickIds.has(r.product_id) && r.final_score >= MIN_NON_CONTENT_SCORE)
                    .sort((a, b) => b.final_score - a.final_score);

                const MAX_APRIORI_SLOTS = aprioriPick.length;
                const MAX_CF_SLOTS = (isBroadQuery || isTransactionalQuery || cfOnlyProducts.length === 0) ? 0 : 1;

                logger.info({
                    query,
                    isGeneralRecQuery,
                    isBroadQuery,
                    isTransactionalQuery,
                    hasAnchorIntent,
                    anchorCategory,
                    anchorCategoryArr: [...anchorCategorySet],
                    anchorMatchedCount: anchorMatched.length,
                    contentCategoriesSize: contentCategories.size,
                    contentMatchedCount: contentMatched.length,
                    nonContentCount: nonContent.length,
                    withAprioriCount: withApriori.length,
                    withAprioriTop3: withApriori.slice(0, 3).map(r => ({
                        id: r.product_id,
                        name: r.rawProduct?.product_name || r.product_name,
                        aprioriScore: r.scores?.apriori,
                        finalScore: r.final_score
                    })),
                    aprioriPickCount: aprioriPick.length,
                    cfOnlyProductsCount: cfOnlyProducts.length,
                    MIN_NON_CONTENT_SCORE,
                    top5Score: top5[0]?.score
                }, '[DIAGNOSTIC] Conditional gating heuristics');

                // Override topSource for dedicated apriori slot — but preserve CF attribution
                // when CF also contributed (CF is user-specific, more informative than apriori)
                for (const pick of aprioriPick) {
                    if (!pick.sources.includes('cf') || pick.scores?.cf === 0) {
                        pick.topSource = 'apriori';
                    }
                    if (!pick.sources.includes('apriori')) pick.sources.push('apriori');
                }

                // Masterful Slot Partitioning Layout:
                // Slot 1: Content
                // Slot 2: CF Personalized recommendation
                // Slot 3: Apriori Cross-sell recommendation
                // Slot 4 & 5: Next best content matches
                // Crucially preserves the 3-content minimum while raising CF/Apriori visibility.
                const activeContent = [
                    ...anchorMatched,
                    ...otherContent
                ];

                const partitioned = [];
                // Slot 1
                if (activeContent.length > 0) {
                    partitioned.push(activeContent[0]);
                }
                // Slot 2
                if (MAX_CF_SLOTS > 0 && cfOnlyProducts.length > 0) {
                    partitioned.push(cfOnlyProducts[0]);
                }
                // Slot 3 (& 4 for transactional): Apriori Cross-sell
                for (const pick of aprioriPick.slice(0, MAX_APRIORI_SLOTS)) {
                    partitioned.push(pick);
                }
                // Fill remaining slots with Content
                let contentIdx = 1;
                while (partitioned.length < 5 && contentIdx < activeContent.length) {
                    if (!partitioned.find(p => p.product_id === activeContent[contentIdx].product_id)) {
                        partitioned.push(activeContent[contentIdx]);
                    }
                    contentIdx++;
                }

                const rankedIds = partitioned.map(r => r.product_id);

                logger.info({
                    contentMatchedCount: contentMatched.length,
                    aprioriPickCount: aprioriPick.length,
                    aprioriPickDetail: aprioriPick.map(r => ({ pid: r.product_id, aprioriScore: r.scores?.apriori, cfScore: r.scores?.cf })),
                    cfOnlyCount: cfOnlyProducts.length,
                    rankedIds,
                    topScores: partitioned.map(r => ({ pid: r.product_id, score: r.final_score, src: r.topSource }))
                }, 'Partitioned ranking applied');

                // ── Hydrate CF-only products (missing rawProduct metadata) ──
                const cfOnlyIds = rankedIds.filter(pid => {
                    const inContent = top5.some(r => Number(r.product_id) === pid);
                    const hasRaw = hybridResults.find(r => Number(r.product_id) === pid)?.rawProduct;
                    return !inContent && !hasRaw;
                });

                if (cfOnlyIds.length > 0) {
                    const stepStartHydrate = Date.now();

                    // Strategy 1: Check local product_knowledge_base first (faster, no network)
                    const { rows: localProducts } = await this.knowledgeRepo.pool.query(`
                        SELECT product_id, content, category_name, unit_price,
                               is_in_stock, quantity_on_shelf
                        FROM product_knowledge_base
                        WHERE product_id = ANY($1::bigint[]) AND store_id = $2
                    `, [cfOnlyIds, storeId]);

                    const localMap = new Map(localProducts.map(p => [Number(p.product_id), p]));
                    const stillMissing = cfOnlyIds.filter(id => !localMap.has(id));

                    // Strategy 2: Fetch remaining from Catalog API (batch, single request)
                    if (stillMissing.length > 0) {
                        try {
                            const catalogResult = await this.apiClient.getProductsByIds(stillMissing);
                            if (catalogResult.success && catalogResult.data?.products) {
                                for (const p of catalogResult.data.products) {
                                    const qtyOnShelf = p.quantityOnShelf ?? p.quantity_on_shelf ?? 0;
                                    localMap.set(Number(p.id), {
                                        product_id: p.id,
                                        content: `"${p.name}"`,
                                        category_name: p.category_name || p.categoryName || '',
                                        unit_price: Number(p.price || p.unitPrice || 0),
                                        is_in_stock: qtyOnShelf > 0,
                                        quantity_on_shelf: qtyOnShelf
                                    });
                                }
                            }
                        } catch (err) {
                            logger.warn({ err, stillMissing }, 'Catalog batch fetch failed — CF products will be excluded');
                        }
                    }

                    // Inject metadata into hybridResults
                    for (const pid of cfOnlyIds) {
                        const meta = localMap.get(pid);
                        if (meta) {
                            const hybrid = hybridResults.find(r => Number(r.product_id) === pid);
                            if (hybrid) hybrid.rawProduct = meta;
                        }
                    }

                    metadata.steps.cfHydration = {
                        cfOnlyCount: cfOnlyIds.length,
                        localHits: localProducts.length,
                        apiFetched: stillMissing.length - cfOnlyIds.filter(id => !localMap.has(id)).length,
                        latencyMs: Date.now() - stepStartHydrate
                    };
                }
                const enrichedTop5 = rankedIds.map(pid => {
                    const original = top5.find(r => Number(r.product_id) === pid);
                    const hybrid = hybridResults.find(r => Number(r.product_id) === pid);
                    return original
                        ? { ...original, ensemble_score: hybrid?.final_score, ensemble_sources: hybrid?.sources, top_source: hybrid?.topSource }
                        : hybrid?.rawProduct
                            ? { ...hybrid.rawProduct, ensemble_score: hybrid.final_score, ensemble_sources: hybrid.sources, top_source: hybrid.topSource }
                            : null;
                }).filter(Boolean);

                logger.info({
                    enrichedIds: enrichedTop5.map(r => ({ pid: r.product_id, src: r.top_source, cat: r.category_name })),
                    rankedIds
                }, '[DEBUG] enrichedTop5 details');

                // Use enriched results if available
                const finalProducts = enrichedTop5.length > 0 ? enrichedTop5 : top5;

                // Step 7: Augmented Generation
                const stepStart7 = Date.now();
                const coPurchaseData = isBroadQuery
                    ? []
                    : await getCoPurchaseContext(this.copurchaseRepo, finalProducts, storeId);
                const response = await this._generateResponse(
                    userMessage, query, finalProducts, coPurchaseData, [], customerContext
                );
                metadata.steps.generation = { latencyMs: Date.now() - stepStart7 };

                const totalMs = Date.now() - startTime;
                metadata.totalLatencyMs = totalMs;
                logger.info({ storeId, customerId, totalMs, productCount: finalProducts.length, engine: 'hybrid' }, 'RAG pipeline completed');

                // Auto-track: record 'recommended' feedback for weight learning
                // Use partitioned results (not raw hybridResults) to correctly attribute content-based
                if (customerId && partitioned.length > 0) {
                    for (const r of partitioned) {
                        this.hybridService.recordFeedback(
                            customerId, r.product_id, storeId,
                            r.topSource, 'recommended',
                            null, r.final_score
                        ).catch(() => { }); // fire-and-forget
                    }
                }

                const syncedProducts = syncProductsWithResponse(finalProducts, response.content);
                logger.info({ before: finalProducts.length, after: syncedProducts.length, responseSnippet: response.content?.substring(0, 100) }, '[DEBUG] Sync filter Phase 3');
                const hydratedProducts = await this._hydrateProductsWithCatalog(syncedProducts);
                logger.info({ hydratedCount: hydratedProducts.length, hasImages: hydratedProducts.filter(p => p.image).length }, '[DEBUG] Catalog hydration Phase 3');

                return {
                    content: response.content,
                    productIds: hydratedProducts.map(r => r.id),
                    products: hydratedProducts,
                    metadata
                };
            }

            // ── Fallback: Phase 2 pipeline (no hybrid service) ──

            // Step 5: Co-purchase Enrichment
            const stepStart5 = Date.now();
            const coPurchaseData = await getCoPurchaseContext(this.copurchaseRepo, top5, storeId);
            metadata.steps.coPurchase = { latencyMs: Date.now() - stepStart5 };

            // Step 5.5: CF Enrichment (Phase 2 — if available)
            let cfData = [];
            if (this.cfService && customerId) {
                try {
                    const stepStartCF = Date.now();
                    cfData = await this.cfService.getRecommendations(customerId, storeId, 3);
                    metadata.steps.cf = {
                        recommendations: cfData.length,
                        latencyMs: Date.now() - stepStartCF
                    };
                } catch (err) {
                    logger.warn({ err }, 'CF enrichment failed — skipping');
                }
            }

            // Step 6: Personalization
            const stepStart6 = Date.now();
            const customerContext = await getPersonalizationContext(this.apiClient, customerId);
            metadata.steps.personalization = {
                customerType: customerContext.type,
                latencyMs: Date.now() - stepStart6
            };

            // Step 7: Augmented Generation
            const stepStart7 = Date.now();
            const response = await this._generateResponse(
                userMessage, query, top5, coPurchaseData, cfData, customerContext
            );
            metadata.steps.generation = { latencyMs: Date.now() - stepStart7 };

            const totalMs = Date.now() - startTime;
            metadata.totalLatencyMs = totalMs;

            logger.info({ storeId, customerId, totalMs, productCount: top5.length, engine: 'phase2-fallback' }, 'RAG pipeline completed');

            const syncedProducts = syncProductsWithResponse(top5, response.content);
            logger.info({ before: top5.length, after: syncedProducts.length, responseSnippet: response.content?.substring(0, 100) }, '[DEBUG] Sync filter Phase 2');
            const hydratedProducts = await this._hydrateProductsWithCatalog(syncedProducts);
            logger.info({ hydratedCount: hydratedProducts.length, hasImages: hydratedProducts.filter(p => p.image).length }, '[DEBUG] Catalog hydration Phase 2');

            return {
                content: response.content,
                productIds: hydratedProducts.map(r => r.id),
                products: hydratedProducts,
                metadata
            };
        } catch (err) {
            logger.error({ err, storeId, userMessage }, 'RAG pipeline error');
            return {
                content: 'Xin lỗi, hệ thống đang gặp sự cố khi tìm kiếm sản phẩm. Vui lòng thử lại sau.',
                productIds: [],
                products: [],
                metadata: { error: err.message, totalLatencyMs: Date.now() - startTime }
            };
        }
    }

    /**
     * Reciprocal Rank Fusion: score(d) = SUM(1 / (k + rank))
     * Items appearing in both lists get higher combined scores
     */
    _reciprocalRankFusion(semanticList, keywordList, k = 60) {
        const scoreMap = new Map();

        semanticList.forEach((item, rank) => {
            const key = `${item.product_id}_${item.store_id}`;
            if (!scoreMap.has(key)) {
                scoreMap.set(key, { score: 0, item });
            }
            scoreMap.get(key).score += 1 / (k + rank + 1);
        });

        keywordList.forEach((item, rank) => {
            const key = `${item.product_id}_${item.store_id}`;
            if (!scoreMap.has(key)) {
                scoreMap.set(key, { score: 0, item });
            }
            scoreMap.get(key).score += 1 / (k + rank + 1);
        });

        return [...scoreMap.values()]
            .sort((a, b) => b.score - a.score)
            .map(v => ({ ...v.item, rrf_score: v.score }));
    }



    async _getCoPurchaseContext(products, storeId) {
        return getCoPurchaseContext(this.copurchaseRepo, products, storeId);
    }

    async _getPersonalizationContext(customerId) {
        return getPersonalizationContext(this.apiClient, customerId);
    }

    /**
     * Generate natural language response using Qwen/Qwen2.5-7B-Instruct
     */
    async _generateResponse(originalMessage, reformulatedQuery, products, coPurchaseData, cfData, customerContext) {
        // Handle 5-arguments call signature from legacy tests
        if (customerContext === undefined && cfData && (cfData.type || cfData.prompt !== undefined)) {
            customerContext = cfData;
            cfData = [];
        }
        const productContext = products.map((p, i) => {
            const name = p.content.match(/"([^"]+)"/)?.[1] || `Product ${p.product_id}`;
            return `${i + 1}. ${name} — ${p.category_name}, ${Number(p.unit_price).toLocaleString('vi-VN')}đ, còn ${p.quantity_on_shelf} sản phẩm`;
        }).join('\n');

        let coPurchaseContext = '';
        if (coPurchaseData.length > 0) {
            coPurchaseContext = '\n\n[DỮ LIỆU MUA KÈM]:\n' +
                coPurchaseData.map(cp => {
                    const relatedNames = cp.relatedProducts.map(r => {
                        const found = products.find(p => Number(p.product_id) === Number(r.product_id_b));
                        if (found) return found.content.match(/"([^"]+)"/)?.[1] || `Product ${r.product_id_b}`;
                        return null;
                    }).filter(Boolean);
                    if (relatedNames.length === 0) return '';
                    return `- Khách mua "${cp.productName}" thường mua kèm: ${relatedNames.join(', ')}`;
                }).filter(Boolean).join('\n');
        }

        let cfContext = '';
        if (cfData.length > 0) {
            cfContext = '\n\nGợi ý phù hợp nhất với bạn (dựa trên hành vi cá nhân):\n' +
                cfData.map(r => `- Product #${r.product_id} (điểm gợi ý: ${r.prediction_score})`).join('\n');
        }

        const productCount = products.length;
        const systemPrompt = `Bạn là tư vấn viên siêu thị POSMART. Trả lời tiếng Việt, thân thiện.
CHỈ dùng dữ liệu bên dưới. KHÔNG bịa sản phẩm/giá.

QUY TẮC NGHIÊM NGẶT:
1. Mở đầu ngắn gọn (1 câu).
2. Liệt kê ĐÚNG ${productCount} sản phẩm: tên + giá. KHÔNG mô tả chi tiết.
3. Nếu có [DỮ LIỆU MUA KÈM], viết 1 câu: "Nhiều khách hàng mua [Sản phẩm A] cũng thường mua kèm [B, C]".
   CHỈ nêu sản phẩm có trong [DỮ LIỆU MUA KÈM]. TUYỆT ĐỐI KHÔNG gom các sản phẩm khác vào câu mua kèm.
4. KHÔNG dùng từ "Apriori", "cá nhân hóa", "sự tương đồng" hay bất kì thuật ngữ kỹ thuật nào.
5. Kết thúc bằng 1 câu mời gọi.
${customerContext.prompt}

Sản phẩm (${productCount} sản phẩm):
${productContext}${coPurchaseContext}${cfContext}`;

        try {
            // Use raw HF client to inject custom RAG system prompt
            const response = await this.hfClient.client.chatCompletion({
                model: this.hfClient.model,
                messages: [
                    { role: 'system', content: systemPrompt },
                    { role: 'user', content: originalMessage }
                ],
                max_tokens: 500,
                temperature: 0.4
            });

            const reply = response.choices?.[0]?.message?.content;
            if (reply) return { content: reply };

            return { content: this._buildFallbackResponse(products, customerContext) };
        } catch (err) {
            logger.error({ err }, 'LLM generation failed — returning formatted fallback');
            return {
                content: this._buildFallbackResponse(products, customerContext)
            };
        }
    }

    /**
     * Fallback when LLM fails — structured text response
     */
    _buildFallbackResponse(products, customerContext) {
        const greeting = customerContext.type === 'vip'
            ? 'Chào anh/chị (khách VIP)! Dưới đây là sản phẩm gợi ý:'
            : 'Chào bạn! Dưới đây là sản phẩm phù hợp:';

        const items = products.map((p, i) => {
            const name = p.content.match(/"([^"]+)"/)?.[1] || `Sản phẩm #${p.product_id}`;
            return `  ${i + 1}. ${name} — ${Number(p.unit_price).toLocaleString('vi-VN')}đ (còn ${p.quantity_on_shelf} trên kệ)`;
        }).join('\n');

        return `${greeting}\n${items}\n\nCác sản phẩm trên đều đang có sẵn tại chi nhánh của bạn!`;
    }

    async _hydrateProductsWithCatalog(syncedProducts) {
        const ids = syncedProducts.map(r => Number(r.product_id || r.id));
        const catalogMap = new Map();

        if (this.apiClient && ids.length > 0) {
            try {
                // Fetch in batch: single API request to avoid N+1 query pattern
                const catalogResult = await this.apiClient.getProductsByIds(ids);
                if (catalogResult.success && catalogResult.data?.products) {
                    catalogResult.data.products.forEach(p => {
                        catalogMap.set(Number(p.id), p);
                    });
                }
            } catch (err) {
                logger.warn({ err, ids }, 'Failed to fetch catalog product details for image hydration');
            }
        }

        return syncedProducts.map(r => {
            const cp = catalogMap.get(Number(r.product_id || r.id));
            return {
                id: Number(r.product_id || r.id),
                name: cp?.name || r.content?.match(/"([^"]+)"/)?.[1] || r.name || `Product ${r.product_id || r.id}`,
                categoryName: cp?.categoryName || cp?.category_name || r.category_name || '',
                unitPrice: cp ? Number(cp.unitPrice || cp.price || 0) : Number(r.unit_price || r.unitPrice || r.price || 0),
                quantityOnShelf: cp?.quantityOnShelf ?? cp?.quantity_on_shelf ?? r.quantity_on_shelf ?? 0,
                isInStock: cp?.isInStock ?? cp?.is_in_stock ?? r.is_in_stock ?? ((cp?.quantityOnShelf ?? r.quantity_on_shelf ?? 0) > 0),
                image: cp?.image || cp?.image_url || r.image || r.image_url || null,
                rrfScore: r.rrf_score || null,
                ensembleScore: r.ensemble_score || null,
                ensemble_score: r.ensemble_score || null,
                ensembleSources: r.ensemble_sources || null,
                ensemble_sources: r.ensemble_sources || null,
                topSource: r.top_source || null,
                top_source: r.top_source || null
            };
        });
    }

    /**
     * Handle case when no products found
     */
    _buildNoResultsResponse(userMessage, storeId, startTime, metadata) {
        metadata.totalLatencyMs = Date.now() - startTime;
        return {
            content: `Xin lỗi, mình không tìm thấy sản phẩm phù hợp với "${userMessage}" tại chi nhánh của bạn. Bạn có thể mô tả chi tiết hơn được không?`,
            productIds: [],
            products: [],
            metadata
        };
    }
}

module.exports = RAGService;
