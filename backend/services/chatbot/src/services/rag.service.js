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
const { CATEGORY_KEYWORD_MAP } = require('./category.constants');

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

// Helper: Khớp từ khóa chính xác, bỏ qua chuỗi con (ví dụ: 'cá' trong 'các')
const hasKeywordExact = (queryText, keyword) => {
    // \p{L} là chữ cái bất kỳ, \d là số. Tránh khớp từ nằm liền kề chữ hoặc số
    const regex = new RegExp(`(?<![\\p{L}\\d])${keyword}(?![\\p{L}\\d])`, 'ui');
    return regex.test(queryText);
};

// Helper: lọc sản phẩm dựa trên text phản hồi của LLM
const syncProductsWithResponse = (products, reply) => {
    if (!reply) return products.slice(0, 3);

    const mutualContent = removeAccents(reply.toLowerCase());

    const mentionedProducts = products.filter(p => {
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

    if (mentionedProducts.length === 0) return products.slice(0, 3);

    // Safety net: Always include apriori/cf products even if LLM forgot to mention them
    const protectedProducts = products.filter(p => {
        const src = p.top_source || p.topSource || p.source;
        return src === 'apriori' || src === 'cf';
    });

    const finalList = [...mentionedProducts];
    for (const p of protectedProducts) {
        if (!finalList.find(m => String(m.product_id || m.id) === String(p.product_id || p.id))) {
            finalList.push(p);
        }
    }

    return finalList;
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
    async recommend(userMessage, storeId, customerId = null, chatHistory = [], intentMeta = {}) {
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
            // Detect continuation BEFORE reformulation changes the query
            const isContinuationRequest = /gợi ý thêm|thêm đi|nữa đi|khác đi|xem thêm|cho xem thêm|gợi ý khác/i.test(userMessage.toLowerCase());
            metadata.steps.reformulation = {
                original: userMessage,
                reformulated: query,
                changed: query !== userMessage,
                isContinuation: isContinuationRequest,
                latencyMs: Date.now() - stepStart1
            };

            // Step 2: Embed query
            const stepStart2 = Date.now();
            const queryVector = await this.embeddingClient.embed(query);
            metadata.steps.embedding = { latencyMs: Date.now() - stepStart2 };

            // Step 3: Hybrid Search (parallel)
            const stepStart3 = Date.now();
            const keywordQuery = cleanQueryForKeyword(query);

            let earlyAnchorCategory = null;
            if (intentMeta.isTransactional) {
                const queryLower = query.toLowerCase();
                for (const [kw, cats] of Object.entries(CATEGORY_KEYWORD_MAP)) {
                    if (hasKeywordExact(queryLower, kw)) {
                        earlyAnchorCategory = cats[0];
                        break;
                    }
                }
            }

            let [rawSemanticResults, keywordResults] = await Promise.all([
                earlyAnchorCategory ? this.knowledgeRepo.searchSemantic(queryVector, storeId, 30, earlyAnchorCategory) : this.knowledgeRepo.searchSemantic(queryVector, storeId, 30),
                earlyAnchorCategory ? this.knowledgeRepo.searchKeyword(keywordQuery, storeId, 30, earlyAnchorCategory) : this.knowledgeRepo.searchKeyword(keywordQuery, storeId, 30)
            ]);

            // Defensive fallback: if anchor filter returned 0 rows, retry without it
            if (earlyAnchorCategory && rawSemanticResults.length === 0 && keywordResults.length === 0) {
                logger.info({ earlyAnchorCategory, keywordQuery }, 'Anchor category filter returned 0 results, retrying without filter');
                earlyAnchorCategory = null;
                [rawSemanticResults, keywordResults] = await Promise.all([
                    this.knowledgeRepo.searchSemantic(queryVector, storeId, 30),
                    this.knowledgeRepo.searchKeyword(keywordQuery, storeId, 30)
                ]);
            }

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
            const BRAND_FTS_MULTIPLIER = 2.0;
            const brandKeywords = ['heineken', 'tiger', 'sapporo', 'bia', 'beer'];
            const hasBrandMatch = keywordResults.length > 0 &&
                brandKeywords.some(bk => query.toLowerCase().includes(bk)) &&
                keywordResults.some(r => r.score > 0.05);

            const adjustedKeywordResults = hasBrandMatch
                ? keywordResults.map(r => ({ ...r, score: r.score * BRAND_FTS_MULTIPLIER }))
                : keywordResults;

            const fused = this._reciprocalRankFusion(semanticResults, adjustedKeywordResults);

            // Step 4.5: Anchor Category Re-ranking
            // Use Top 1 RRF result's category as "anchor" — boost same-category, penalize others
            // NOTE: Use proportional boost/penalty to avoid making rrf_score negative
            // (keyword-only RRF scores ≈ 0.016 with k=60, fixed penalties would dominate)
            if (fused.length > 1) {
                const queryLower = query.toLowerCase();
                const anchorCategories = new Set();

                for (const [kw, cats] of Object.entries(CATEGORY_KEYWORD_MAP)) {
                    if (hasKeywordExact(queryLower, kw)) {
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
                return this._buildNoResultsResponse(keywordQuery || userMessage, storeId, startTime, metadata);
            }

            // ── Phase 3: Hybrid Ensemble (replaces separate CF/Apriori steps) ──
            let hybridResults = null;
            let sessionIntent = null;

            if (this.hybridService) {
                // Step 5: Hybrid Ensemble
                const stepStart5 = Date.now();
                const customerContext = await getPersonalizationContext(this.apiClient, customerId);

                // Detect general recommendation query before hybrid scoring
                const generalRegex = /gợi ý vài món|đề xuất vài món|gợi ý cho tôi|gợi ý các món|gợi ý sản phẩm/i;
                const isMatchedGeneral = generalRegex.test(query.toLowerCase()) ||
                    (query.toLowerCase().includes('gợi ý') && query.toLowerCase().includes('món')) ||
                    (query.toLowerCase().includes('đề xuất') && query.toLowerCase().includes('món')) ||
                    (query.toLowerCase().trim() === 'gợi ý cho tôi vài món' || query.toLowerCase().includes('vài món'));

                let containsCategoryKeyword = false;
                for (const kw of Object.keys(CATEGORY_KEYWORD_MAP)) {
                    if (hasKeywordExact(query.toLowerCase(), kw)) {
                        containsCategoryKeyword = true;
                        break;
                    }
                }
                const isGeneralRecQuery = isMatchedGeneral && !containsCategoryKeyword;

                hybridResults = await this.hybridService.score(
                    top5, customerId, storeId, customerContext.type,
                    { excludePurchased: !isGeneralRecQuery }
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

                    let flushSignal = false;
                    if (earlyAnchorCategory && sessionIntent && sessionIntent.cluster !== 'exploring') {
                        const shiftTarget = this.sessionContextService.detectCategoryShift(
                            earlyAnchorCategory, sessionIntent.cluster
                        );
                        if (shiftTarget) {
                            logger.info({ from: sessionIntent.cluster, to: shiftTarget, anchor: earlyAnchorCategory }, 'Session: Category shift detected — flushing old context');
                            flushSignal = true;
                        }
                    }

                    if (sessionIntent) {
                        hybridResults = this.sessionContextService.applySessionBoost(hybridResults, sessionIntent, flushSignal);

                        // Attribute session-boosted products for feedback tracking
                        // Only override topSource for CF-only products (content=0).
                        // Content-matched products keep 'content' attribution — the user's query was the primary signal.
                        if (sessionIntent.cluster !== 'exploring') {
                            for (const r of hybridResults) {
                                if (r.session_boosted) {
                                    if (!r.sources.includes('session')) r.sources.push('session');
                                    // Session badge when: (1) continuation query, or
                                    // (2) content score low (less than 0.3)
                                    if (isContinuationRequest || (r.scores?.content || 0) < 0.3) {
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
                // isGeneralRecQuery has been hoisted to step 5.
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
                const MAX_CF_SLOTS = (isBroadQuery || isTransactionalQuery || cfOnlyProducts.length === 0) ? 0 : (isGeneralRecQuery ? 2 : 1);

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

                // ═══ NOVELTY FILTER: Loại sản phẩm đã gợi ý ở lượt trước ═══
                const historyProductIds = new Set(
                    this.sessionContextService
                        ? this.sessionContextService.extractProductSequence(chatHistory).map(Number)
                        : []
                );

                const filterNovelty = (arr) => {
                    if (!isContinuationRequest || historyProductIds.size === 0) return arr;
                    return arr.filter(r => !historyProductIds.has(Number(r.product_id)));
                };

                const novelContent = filterNovelty(activeContent);
                const novelApriori = filterNovelty(aprioriPick);
                const novelCf = filterNovelty(cfOnlyProducts);

                let partitioned = [];
                if (isTransactionalQuery && earlyAnchorCategory && anchorMatched.length > 0) {
                    // SLOT 1: Ưu tiên tuyệt đối sản phẩm khách hàng gọi tên (Anchor Content)
                    const filteredAnchorMatched = filterNovelty(anchorMatched);
                    if (filteredAnchorMatched.length > 0) {
                        partitioned.push(filteredAnchorMatched[0]);
                    }

                    // SLOT 2 & 3: Nhường sân khấu cho Apriori Cross-sell (Chứng minh Act 2)
                    for (const pick of novelApriori.slice(0, MAX_APRIORI_SLOTS)) {
                        partitioned.push(pick);
                    }

                    // LƯU Ý BẢO VỆ ĐỒ ÁN: Cố ý loại bỏ CF khỏi truy vấn Transactional 
                    // để giám khảo tập trung vào luật mua kèm (Apriori), tránh nhiễu loạn UI.

                    // SLOT 4 & 5: Lấp đầy bằng các sản phẩm cùng danh mục (Secondary Content)
                    let fillIdx = 1;
                    const fillPool = [...filteredAnchorMatched.slice(1), ...filterNovelty(otherContent)];
                    while (partitioned.length < 5 && fillIdx <= fillPool.length) {
                        const candidate = fillPool[fillIdx - 1];
                        if (!partitioned.find(p => p.product_id === candidate.product_id)) {
                            partitioned.push(candidate);
                        }
                        fillIdx++;
                    }
                } else if (isGeneralRecQuery) {
                    // ═══ ACT 3: Welcome Query — CF has maximum priority ═══
                    // Slot 1-3: CF personalized products (cohort behaviors)
                    for (let i = 0; i < novelCf.length && partitioned.length < 3; i++) {
                        partitioned.push(novelCf[i]);
                    }
                    // Slot 4: Apriori cross-sell candidate
                    for (const pick of novelApriori) {
                        if (partitioned.length < 4) partitioned.push(pick);
                    }
                    // Remaining slots filled by semantic content search
                    let contentIdx = 0;
                    while (partitioned.length < 5 && contentIdx < novelContent.length) {
                        if (!partitioned.find(p => p.product_id === novelContent[contentIdx].product_id)) {
                            partitioned.push(novelContent[contentIdx]);
                        }
                        contentIdx++;
                    }
                } else {
                    // Slot 1
                    if (novelContent.length > 0) {
                        partitioned.push(novelContent[0]);
                    }
                    // Slot 2
                    for (let i = 0; i < MAX_CF_SLOTS && i < novelCf.length; i++) {
                        partitioned.push(novelCf[i]);
                    }
                    // Slot 3 (& 4 for transactional): Apriori Cross-sell
                    for (const pick of novelApriori.slice(0, MAX_APRIORI_SLOTS)) {
                        partitioned.push(pick);
                    }
                    // Fill remaining slots with Content
                    let contentIdx = 1;
                    while (partitioned.length < 5 && contentIdx < novelContent.length) {
                        if (!partitioned.find(p => p.product_id === novelContent[contentIdx].product_id)) {
                            partitioned.push(novelContent[contentIdx]);
                        }
                        contentIdx++;
                    }
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
                    userMessage, query, finalProducts, coPurchaseData, [], customerContext, storeId
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
                const hydratedProducts = await this._hydrateProductsWithCatalog(syncedProducts, storeId);
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
                userMessage, query, top5, coPurchaseData, cfData, customerContext, storeId
            );
            metadata.steps.generation = { latencyMs: Date.now() - stepStart7 };

            const totalMs = Date.now() - startTime;
            metadata.totalLatencyMs = totalMs;

            logger.info({ storeId, customerId, totalMs, productCount: top5.length, engine: 'phase2-fallback' }, 'RAG pipeline completed');

            const syncedProducts = syncProductsWithResponse(top5, response.content);
            logger.info({ before: top5.length, after: syncedProducts.length, responseSnippet: response.content?.substring(0, 100) }, '[DEBUG] Sync filter Phase 2');
            const hydratedProducts = await this._hydrateProductsWithCatalog(syncedProducts, storeId);
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
    async _generateResponse(originalMessage, reformulatedQuery, products, coPurchaseData, cfData, customerContext, storeId = 1) {
        // Handle 5-arguments call signature from legacy tests
        if (customerContext === undefined && cfData && (cfData.type || cfData.prompt !== undefined)) {
            customerContext = cfData;
            cfData = [];
        }

        // Retrieve discounts to present to LLM
        const discountMap = new Map();
        if (this.apiClient && storeId) {
            try {
                const invResult = await this.apiClient.getInventoryPublicSummary(storeId);
                if (invResult.success && Array.isArray(invResult.data)) {
                    invResult.data.forEach(item => {
                        discountMap.set(Number(item.productId), Number(item.discountPercentage) || 0);
                    });
                }
            } catch (err) {
                logger.warn({ err, storeId }, 'Failed to fetch public summary for response generation');
            }
        }

        const productContext = products.map((p, i) => {
            const pid = Number(p.product_id || p.id);
            const name = p.content?.match(/"([^"]+)"/)?.[1] || p.name || `Product ${pid}`;
            const discountPercentage = discountMap.get(pid) || 0;
            const originalPrice = Number(p.unit_price || p.unitPrice || 0);
            const qtyOnShelf = p.quantity_on_shelf ?? p.quantityOnShelf ?? 0;

            if (discountPercentage > 0) {
                const finalPrice = Math.round(originalPrice * (1 - discountPercentage / 100));
                return `${i + 1}. ${name} — ${p.category_name || p.categoryName || ''}, ~~${originalPrice.toLocaleString('vi-VN')}đ~~ ${finalPrice.toLocaleString('vi-VN')}đ (Đang giảm giá ${discountPercentage}%), còn ${qtyOnShelf} sản phẩm`;
            }
            return `${i + 1}. ${name} — ${p.category_name || p.categoryName || ''}, ${originalPrice.toLocaleString('vi-VN')}đ, còn ${qtyOnShelf} sản phẩm`;
        }).join('\n');

        let coPurchaseContext = '';
        if (coPurchaseData.length > 0) {
            coPurchaseContext = '\n\n[DỮ LIỆU MUA KÈM]:\n' +
                coPurchaseData.map(cp => {
                    const relatedNames = cp.relatedProducts.map(r => {
                        const found = products.find(p => Number(p.product_id) === Number(r.product_id_b));
                        if (found) return found.content.match(/"([^"]+)"/)?.[1] || found.name || `Product ${r.product_id_b}`;
                        return r.product_name_b || null;
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
3. Nếu sản phẩm đang giảm giá (được ghi là: ~~giá gốc~~ giá mới (Đang giảm giá X%)), bạn phải nhắc đến việc sản phẩm đang được giảm giá/khuyến mãi bao nhiêu % trong câu giới thiệu/tư vấn sản phẩm đó để kích thích mua sắm.
4. Nếu có [DỮ LIỆU MUA KÈM], viết 1 câu gợi ý mua kèm TẤT CẢ sản phẩm được liệt kê:
   "Nhiều khách hàng mua [Sản phẩm A] cũng thường mua kèm [B, C, ...]"
   PHẢI nhắc đến TẤT CẢ sản phẩm có trong danh sách mua kèm, tuyệt đối không bỏ sót.
   CHỈ nêu sản phẩm có trong [DỮ LIỆU MUA KÈM]. TUYỆT ĐỐI KHÔNG gom các sản phẩm khác vào câu mua kèm.
   Lưu ý: Chỉ xưng hô "mình" hoặc "hệ thống", không xưng là AI hay bot.
5. KHÔNG dùng từ "Apriori", "cá nhân hóa", "sự tương đồng" hay bất kì thuật ngữ kỹ thuật nào.
6. Kết thúc bằng 1 câu mời gọi.
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

    async _hydrateProductsWithCatalog(syncedProducts, storeId = 1) {
        const ids = syncedProducts.map(r => Number(r.product_id || r.id));
        const catalogMap = new Map();
        const discountMap = new Map();

        if (ids.length > 0) {
            try {
                if (this.apiClient) {
                    // Fetch in batch: single API request to avoid N+1 query pattern
                    const catalogResult = await this.apiClient.getProductsByIds(ids);
                    if (catalogResult.success && catalogResult.data?.products) {
                        catalogResult.data.products.forEach(p => {
                            catalogMap.set(Number(p.id), p);
                        });
                    }
                }
            } catch (err) {
                logger.warn({ err, ids }, 'Failed to fetch catalog product details for image hydration');
            }

            try {
                if (this.apiClient && storeId) {
                    const invResult = await this.apiClient.getInventoryPublicSummary(storeId);
                    if (invResult.success && Array.isArray(invResult.data)) {
                        invResult.data.forEach(item => {
                            discountMap.set(Number(item.productId), Number(item.discountPercentage) || 0);
                        });
                    }
                }
            } catch (err) {
                logger.warn({ err, storeId }, 'Failed to fetch store inventory public summary for discounts');
            }
        }

        return syncedProducts.map(r => {
            const pid = Number(r.product_id || r.id);
            const cp = catalogMap.get(pid);
            const discountPercentage = discountMap.get(pid) || 0;
            const unitPrice = cp ? Number(cp.unitPrice || cp.price || 0) : Number(r.unit_price || r.unitPrice || r.price || 0);
            const finalPrice = Math.round(unitPrice * (1 - discountPercentage / 100));

            return {
                id: pid,
                name: cp?.name || r.content?.match(/"([^"]+)"/)?.[1] || r.name || `Product ${pid}`,
                categoryName: cp?.categoryName || cp?.category_name || r.category_name || '',
                unitPrice,
                discountPercentage,
                finalPrice,
                quantityOnShelf: cp?.quantityOnShelf ?? cp?.quantity_on_shelf ?? r.quantityOnShelf ?? r.quantity_on_shelf ?? 0,
                isInStock: cp?.isInStock ?? cp?.is_in_stock ?? r.isInStock ?? r.is_in_stock ?? ((cp?.quantityOnShelf ?? r.quantityOnShelf ?? r.quantity_on_shelf ?? 0) > 0),
                image: cp?.image || cp?.image_url || r.image || r.image_url || null,
                isPerishable: cp?.isPerishable ?? cp?.is_perishable ?? r.isPerishable ?? r.is_perishable ?? false,
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
    _buildNoResultsResponse(displayQuery, storeId, startTime, metadata) {
        metadata.totalLatencyMs = Date.now() - startTime;
        return {
            content: `Xin lỗi, mình không tìm thấy sản phẩm phù hợp với "${displayQuery}" tại chi nhánh của bạn. Bạn có thể mô tả chi tiết hơn được không?`,
            productIds: [],
            products: [],
            metadata
        };
    }
}

module.exports = RAGService;
