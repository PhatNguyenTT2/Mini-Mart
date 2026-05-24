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

// Helper: bỏ dấu tiếng Việt bằng Unicode NFD decomposition
const removeAccents = (str) => {
    if (!str) return '';
    return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
};

// Helper: lọc sản phẩm dựa trên text phản hồi của LLM
const syncProductsWithResponse = (products, reply) => {
    if (!reply) return products.slice(0, 3);

    const normalizedContent = removeAccents(reply.toLowerCase());

    const mentionedProducts = products.filter(p => {
        const name = p.content?.match(/"([^"]+)"/)?.[1] || p.name || '';
        if (!name) return false;

        const normalizedName = removeAccents(name.toLowerCase());

        // Match 1: Full name
        if (normalizedContent.includes(normalizedName)) return true;

        // Match 2: Partial — ≥3 từ đầu (LLM hay viết tắt tên SP)
        const words = normalizedName.split(/\s+/);
        if (words.length >= 3) {
            const partial = words.slice(0, 3).join(' ');
            if (normalizedContent.includes(partial)) return true;
        }

        // Match 3: Bigram minimum (≥2 từ) — KHÔNG dùng single-word
        // để tránh trúng các danh từ chung phổ biến: "Nước", "Bánh", "Kẹo", "Thịt"
        if (words.length >= 2) {
            const bigram = words.slice(0, 2).join(' ');
            if (normalizedContent.includes(bigram)) return true;
        }

        return false;
    });

    return mentionedProducts.length > 0 ? mentionedProducts : products.slice(0, 3);
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
            const [semanticResults, keywordResults] = await Promise.all([
                this.knowledgeRepo.searchSemantic(queryVector, storeId, 10),
                this.knowledgeRepo.searchKeyword(query, storeId, 10)
            ]);
            metadata.steps.search = {
                semanticCount: semanticResults.length,
                keywordCount: keywordResults.length,
                latencyMs: Date.now() - stepStart3
            };

            // Step 4: RRF Fusion
            const fused = this._reciprocalRankFusion(semanticResults, keywordResults);

            // Step 4.5: Anchor Category Re-ranking
            // Use Top 1 RRF result's category as "anchor" — boost same-category, penalize others
            if (fused.length > 1 && fused[0].category_name) {
                const anchorCategory = fused[0].category_name;
                const BOOST = 0.05;
                const PENALTY = 0.03;

                for (const item of fused) {
                    if (item.category_name === anchorCategory) {
                        item.rrf_score += BOOST;
                    } else {
                        item.rrf_score -= PENALTY;
                    }
                }
                // Re-sort by adjusted score
                fused.sort((a, b) => b.rrf_score - a.rrf_score);

                metadata.steps.anchorRerank = {
                    anchorCategory,
                    boost: BOOST,
                    penalty: PENALTY
                };
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

                // Step 6: Session Context Boost
                if (this.sessionContextService && chatHistory.length > 0) {
                    const productSequence = this.sessionContextService.extractProductSequence(chatHistory);
                    sessionIntent = this.sessionContextService.inferSessionIntent(productSequence, userMessage);
                    if (sessionIntent) {
                        hybridResults = this.sessionContextService.applySessionBoost(hybridResults, sessionIntent);

                        // Attribute session-boosted products for feedback tracking
                        if (sessionIntent.cluster !== 'exploring') {
                            for (const r of hybridResults) {
                                if (r.session_boosted) {
                                    r.topSource = 'session';
                                    if (!r.sources.includes('session')) r.sources.push('session');
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

                // Re-rank top5 by ensemble score
                const rankedIds = hybridResults.slice(0, 5).map(r => r.product_id);

                // ── Hydrate CF-only products (missing rawProduct metadata) ──
                const cfOnlyIds = rankedIds.filter(pid => {
                    const inContent = top5.some(r => Number(r.product_id) === pid);
                    const hasRaw = hybridResults.find(r => r.product_id === pid)?.rawProduct;
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
                            const hybrid = hybridResults.find(r => r.product_id === pid);
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
                    const hybrid = hybridResults.find(r => r.product_id === pid);
                    return original
                        ? { ...original, ensemble_score: hybrid?.final_score, ensemble_sources: hybrid?.sources, top_source: hybrid?.topSource }
                        : hybrid?.rawProduct
                            ? { ...hybrid.rawProduct, ensemble_score: hybrid.final_score, ensemble_sources: hybrid.sources, top_source: hybrid.topSource }
                            : null;
                }).filter(Boolean);

                // Use enriched results if available
                const finalProducts = enrichedTop5.length > 0 ? enrichedTop5 : top5;

                // Step 7: Augmented Generation
                const stepStart7 = Date.now();
                const coPurchaseData = await getCoPurchaseContext(this.copurchaseRepo, finalProducts, storeId);
                const response = await this._generateResponse(
                    userMessage, query, finalProducts, coPurchaseData, [], customerContext
                );
                metadata.steps.generation = { latencyMs: Date.now() - stepStart7 };

                const totalMs = Date.now() - startTime;
                metadata.totalLatencyMs = totalMs;
                logger.info({ storeId, customerId, totalMs, productCount: finalProducts.length, engine: 'hybrid' }, 'RAG pipeline completed');

                // Auto-track: record 'recommended' feedback for weight learning
                if (customerId && hybridResults.length > 0) {
                    for (const r of hybridResults.slice(0, 5)) {
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
            coPurchaseContext = '\n\nSản phẩm thường mua kèm (Apriori):\n' +
                coPurchaseData.map(cp => {
                    const items = cp.relatedProducts.map(r => {
                        const conf = Number(r.confidence) > 0
                            ? ` (${Math.round(r.confidence * 100)}% mua kèm)`
                            : '';
                        return `Product #${r.product_id_b}${conf}`;
                    });
                    return `- Khách mua "${cp.productName}" thường mua kèm: ${items.join(', ')}`;
                }).join('\n');
        }

        let cfContext = '';
        if (cfData.length > 0) {
            cfContext = '\n\nGợi ý cá nhân hóa (dựa trên lịch sử mua):\n' +
                cfData.map(r => `- Product #${r.product_id} (điểm phù hợp: ${r.prediction_score})`).join('\n');
        }

        const systemPrompt = `Bạn là nhân viên tư vấn siêu thị POSMART. Trả lời bằng tiếng Việt, thân thiện, ngắn gọn.
CHỈ sử dụng dữ liệu sản phẩm được cung cấp bên dưới. KHÔNG bịa thêm sản phẩm hay giá.
${customerContext.prompt}

Dữ liệu sản phẩm phù hợp:
${productContext}${coPurchaseContext}${cfContext}`;

        try {
            // Use raw HF client to inject custom RAG system prompt
            const response = await this.hfClient.client.chatCompletion({
                model: this.hfClient.model,
                messages: [
                    { role: 'system', content: systemPrompt },
                    { role: 'user', content: originalMessage }
                ],
                max_tokens: 400,
                temperature: 0.6
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
                ensembleSources: r.ensemble_sources || null,
                topSource: r.top_source || null
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
