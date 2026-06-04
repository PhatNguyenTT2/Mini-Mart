const { ValidationError, NotFoundError } = require('../../../../shared/common/errors');
const { resolveIntent } = require('./intent.resolver');
const { getPersonalizationContext, getCoPurchaseHint } = require('./context.helper');
const ChatUtils = require('./chat.utils');
const ReadHandler = require('./handlers/read.handler');
const CartHandler = require('./handlers/cart.handler');
const OrderHandler = require('./handlers/order.handler');
const PosHandler = require('./handlers/pos.handler');
const logger = require('../../../../shared/common/logger');

class ChatService {
    constructor(chatRepo, hfClient, apiClient = null, ragService = null, copurchaseRepo = null) {
        this.chatRepo = chatRepo;
        this.hfClient = hfClient;
        this.apiClient = apiClient;
        this.ragService = ragService;
        this.copurchaseRepo = copurchaseRepo;

        // Shared utilities (DI context)
        this.utils = new ChatUtils({ chatRepo, hfClient, apiClient, ragService, copurchaseRepo });
        this.actionExecutor = this.utils.actionExecutor;

        // Domain handlers
        const handlerCtx = { chatRepo, hfClient, apiClient, ragService, copurchaseRepo, utils: this.utils };
        this.readHandler = new ReadHandler(handlerCtx);
        this.cartHandler = new CartHandler(handlerCtx);
        this.orderHandler = new OrderHandler(handlerCtx);
        this.posHandler = new PosHandler(handlerCtx);
    }

    /** Hot-swap RAG service after background model loading */
    updateRAGService(ragService) {
        this.ragService = ragService;
        this.utils.ragService = ragService;
        this.readHandler.ragService = ragService;
        this.posHandler.ragService = ragService;
        logger.info('RAG Service hot-swapped into ChatService');
    }

    async startSession(userId, userType, storeId = null) {
        if (!userId) throw new ValidationError('user_id is required');
        if (!['customer', 'employee'].includes(userType)) {
            throw new ValidationError('user_type must be customer or employee');
        }
        return await this.chatRepo.createSession(userId, userType, storeId);
    }

    async getSession(sessionId) {
        const session = await this.chatRepo.findSessionById(sessionId);
        if (!session) throw new NotFoundError('Chat session');
        return session;
    }

    async getUserSessions(userId) {
        return await this.chatRepo.findSessionsByUser(userId);
    }

    async getSessionMessages(sessionId) {
        const session = await this.chatRepo.findSessionById(sessionId);
        if (!session) throw new NotFoundError('Chat session');
        return await this.chatRepo.getMessagesBySession(sessionId);
    }

    async endSession(sessionId) {
        const session = await this.chatRepo.findSessionById(sessionId);
        if (!session) throw new NotFoundError('Chat session');
        return await this.chatRepo.endSession(sessionId);
    }

    async sendMessage(sessionId, userMessage) {
        if (!userMessage || userMessage.trim().length === 0) {
            throw new ValidationError('Message cannot be empty');
        }

        if (!this.ragService && process.env.NODE_ENV !== 'test') {
            return {
                intent: 'INITIALIZING',
                reply: 'I am currently initializing my AI capabilities (this usually takes about 30-60 seconds). Please try asking again shortly!',
                products: null,
                metadata: {
                    model: 'system',
                    latencyMs: 0,
                    intent: { intent: 'INITIALIZING', matchedKeyword: '' },
                    isFallback: true
                }
            };
        }

        const session = await this.chatRepo.findSessionById(sessionId);
        if (!session) throw new NotFoundError('Chat session');
        if (!session.is_active) throw new ValidationError('Chat session has ended');

        // Check for pending action (Clarification/Confirmation)
        if (session.metadata && session.metadata.pendingAction) {
            const resolvedAction = await this.utils.handleClarification(session, userMessage, this._getClarificationHandlers());
            if (resolvedAction) {
                // Save user message first since clarification flow intercepts before normal resolveIntent
                await this.chatRepo.addMessage(sessionId, 'user', userMessage, resolvedAction.intent);

                // Save assistant message
                await this.chatRepo.addMessage(sessionId, 'assistant', resolvedAction.reply, resolvedAction.intent, {
                    model: 'system-agent',
                    intent: resolvedAction.intent,
                    action: resolvedAction.action || null
                });

                // Update session's lastMentionedProducts in metadata if response returned products
                if (resolvedAction.products && resolvedAction.products.length > 0) {
                    const metadata = session.metadata || {};
                    metadata.lastMentionedProducts = resolvedAction.products.map(p => ({
                        id: p.id,
                        name: p.name,
                        unitPrice: p.unitPrice || p.price || p.unit_price,
                        quantityOnShelf: p.quantityOnShelf || 0,
                        image: p.image || null
                    }));
                    await this.chatRepo.updateSessionMetadata(sessionId, metadata);
                }

                return {
                    intent: resolvedAction.intent,
                    reply: resolvedAction.reply,
                    products: resolvedAction.products || null,
                    action: resolvedAction.action || null,
                    metadata: {
                        model: 'system-agent',
                        intent: { intent: resolvedAction.intent, matchedKeyword: '' }
                    }
                };
            }
        }

        const userType = session.userType || session.user_type || 'customer';
        const intentResult = resolveIntent(userMessage, userType);
        logger.info({ sessionId, intent: intentResult.intent, keyword: intentResult.matchedKeyword }, 'Intent resolved');

        await this.chatRepo.addMessage(sessionId, 'user', userMessage, intentResult.intent);

        let response;
        switch (intentResult.intent) {
            case 'CHECK_STOCK':
                response = await this.readHandler.handleCheckStock(session, userMessage);
                break;
            case 'CHECK_PRICE':
                response = await this.readHandler.handleCheckPrice(session, userMessage);
                break;
            case 'ORDER_STATUS':
                response = await this.readHandler.handleOrderStatus(session, userMessage);
                break;
            case 'RECOMMENDATION':
                response = await this.readHandler.handleRecommendation(session, userMessage);
                break;
            case 'SEARCH_PRODUCT':
                response = await this.readHandler.handleSearchProduct(session, userMessage);
                break;
            case 'HELP':
                response = this.utils.handleHelp();
                break;
            case 'ADD_TO_CART':
                response = await this.cartHandler.handleAddToCart(session, userMessage);
                break;
            case 'REMOVE_FROM_CART':
                response = await this.cartHandler.handleRemoveFromCart(session, userMessage);
                break;
            case 'UPDATE_CART_ITEM':
                response = await this.cartHandler.handleUpdateCartItem(session, userMessage);
                break;
            case 'VIEW_CART':
                response = this.cartHandler.handleViewCart(session);
                break;
            case 'TRACK_ORDER':
                response = await this.orderHandler.handleTrackOrder(session, userMessage);
                break;
            case 'CANCEL_ORDER':
                response = await this.orderHandler.handleCustomerCancelOrder(session, userMessage);
                break;
            case 'CHECKOUT_GUIDE':
                response = this.cartHandler.handleCheckoutGuide(session);
                break;
            case 'POS_ADD_ITEM':
                response = await this.posHandler.handlePosAddItem(session, userMessage);
                break;
            case 'CREATE_ORDER':
                response = await this.posHandler.processOrderCollection(session, userMessage);
                break;
            case 'PAYMENT_CHECK':
                response = await this.posHandler.handlePaymentCheck(session, userMessage);
                break;
            case 'FREE_CHAT':
            default:
                response = await this.utils.handleFreeChat(sessionId, userMessage);
                break;
        }

        const reply = response.content || response.reply;
        await this.chatRepo.addMessage(sessionId, 'assistant', reply, intentResult.intent, {
            model: response.model || 'system-agent',
            latencyMs: response.latencyMs || null,
            intent: intentResult.intent,
            apiCalled: response.apiCalled || null,
            error: response.error || null,
            action: response.action || null
        });

        // Centralized lastMentionedProducts update for any standard intents that return products
        if (response.products && response.products.length > 0) {
            const metadata = session.metadata || {};
            metadata.lastMentionedProducts = response.products.map(p => ({
                id: p.id,
                name: p.name,
                unitPrice: p.unitPrice || p.price || p.unit_price,
                quantityOnShelf: p.quantityOnShelf || 0,
                image: p.image || null
            }));
            await this.chatRepo.updateSessionMetadata(sessionId, metadata);
        }

        return {
            intent: intentResult.intent,
            reply: reply,
            products: response.products || null,
            action: response.action || null,
            metadata: {
                model: response.model || 'system-agent',
                latencyMs: response.latencyMs || 0,
                intent: intentResult,
                apiCalled: response.apiCalled || null,
                ragMetadata: response.ragMetadata || null
            }
        };
    }

    // ── Read Handler Delegations ─────────────────
    // Retained as thin wrappers for backward compatibility

    async _handleRecommendation(session, userMessage) {
        return this.readHandler.handleRecommendation(session, userMessage);
    }

    async _handleCheckStock(session, userMessage) {
        return this.readHandler.handleCheckStock(session, userMessage);
    }

    async _handleCheckPrice(session, userMessage) {
        return this.readHandler.handleCheckPrice(session, userMessage);
    }

    async _handleOrderStatus(session, userMessage) {
        return this.readHandler.handleOrderStatus(session, userMessage);
    }

    async _handleSearchProduct(session, userMessage) {
        return this.readHandler.handleSearchProduct(session, userMessage);
    }

    async _handleSearchProductFallback(sessionId, userMessage) {
        return this.readHandler.handleSearchProductFallback(sessionId, userMessage);
    }

    // ── Cart, Order, POS Handler Delegations ───────
    // Thin wrappers for backward compat + clarification callbacks

    async _handleAddToCart(s, m) { return this.cartHandler.handleAddToCart(s, m); }
    async _executeAddToCart(s, p, q) { return this.cartHandler.executeAddToCart(s, p, q); }
    async _handleRemoveFromCart(s, m) { return this.cartHandler.handleRemoveFromCart(s, m); }
    async _handleUpdateCartItem(s, m) { return this.cartHandler.handleUpdateCartItem(s, m); }
    _handleViewCart(s) { return this.cartHandler.handleViewCart(s); }
    _handleCheckoutGuide(s) { return this.cartHandler.handleCheckoutGuide(s); }
    async _handleTrackOrder(s, m) { return this.orderHandler.handleTrackOrder(s, m); }
    async _handleCustomerCancelOrder(s, m) { return this.orderHandler.handleCustomerCancelOrder(s, m); }
    async _handlePosAddItem(s, m) { return this.posHandler.handlePosAddItem(s, m); }
    async _executePosAddItem(s, p, q) { return this.posHandler.executePosAddItem(s, p, q); }
    async _processOrderCollection(s, m) { return this.posHandler.processOrderCollection(s, m); }
    async _handlePaymentCheck(s, m) { return this.posHandler.handlePaymentCheck(s, m); }

    _getClarificationHandlers() {
        return {
            executeAddToCart: (s, p, q) => this.cartHandler.executeAddToCart(s, p, q),
            executePosAddItem: (s, p, q) => this.posHandler.executePosAddItem(s, p, q),
            processOrderCollection: (s, m) => this.posHandler.processOrderCollection(s, m)
        };
    }

    _extractQuantityAndProduct(message) {
        return this.utils.extractQuantityAndProduct(message);
    }

    // ── Helpers ──────────────────────────────────

    async _resolveProductsByRAG(keyword, storeId, limit = 5) {
        return this.utils.resolveProductsByRAG(keyword, storeId, limit);
    }

    _extractKeyword(message, triggerWords) {
        return this.utils.extractKeyword(message, triggerWords);
    }

    _extractOrderId(message) {
        return this.utils.extractOrderId(message);
    }

    async _enrichWithAI(sessionId, userMessage, dataContext, opts = {}) {
        return this.utils.enrichWithAI(sessionId, userMessage, dataContext, opts);
    }

    _fallbackNoApi(intent, keyword) {
        return this.utils.fallbackNoApi(intent, keyword);
    }

    async _getRecentHistory(sessionId) {
        return this.utils.getRecentHistory(sessionId);
    }

    // ── Streaming Interface (WebSocket) ─────────────

    /**
     * Stream a response — yields { type, data } objects.
     * type = 'chunk' for text tokens, 'complete' for final metadata.
     * @param {number} sessionId
     * @param {string} userMessage
     * @yields {{ type: 'chunk', text: string } | { type: 'complete', intent: string, products: array, fullText: string }}
     */
    async * sendMessageStream(sessionId, userMessage) {
        if (!userMessage || userMessage.trim().length === 0) {
            throw new ValidationError('Message cannot be empty');
        }

        const session = await this.chatRepo.findSessionById(sessionId);
        if (!session) throw new NotFoundError('Chat session');
        if (!session.is_active) throw new ValidationError('Chat session has ended');

        // Check for pending action (Clarification/Confirmation)
        if (session.metadata && session.metadata.pendingAction) {
            const resolvedAction = await this.utils.handleClarification(session, userMessage, this._getClarificationHandlers());
            if (resolvedAction) {
                // Save user message first since clarification flow intercepts before normal resolveIntent
                await this.chatRepo.addMessage(sessionId, 'user', userMessage, resolvedAction.intent);

                const fullText = resolvedAction.reply;
                const products = resolvedAction.products || null;
                const action = resolvedAction.action || null;

                // Simulate streaming: yield 3-4 words at a time for smooth UX
                const words = fullText.split(/(\s+)/);
                let buffer = '';
                for (let i = 0; i < words.length; i++) {
                    buffer += words[i];
                    if ((i + 1) % 6 === 0 || i === words.length - 1) {
                        yield { type: 'chunk', text: buffer };
                        buffer = '';
                        // Small delay for visual effect (10ms)
                        await new Promise(r => setTimeout(r, 10));
                    }
                }

                // Save assistant message to DB
                await this.chatRepo.addMessage(sessionId, 'assistant', fullText, resolvedAction.intent, {
                    model: 'system-agent',
                    intent: resolvedAction.intent,
                    action: action
                });

                // Update session's lastMentionedProducts in metadata if response returned products
                if (products && products.length > 0) {
                    const metadata = session.metadata || {};
                    metadata.lastMentionedProducts = products.map(p => ({
                        id: p.id,
                        name: p.name,
                        unitPrice: p.unitPrice || p.price || p.unit_price,
                        quantityOnShelf: p.quantityOnShelf || 0,
                        image: p.image || null
                    }));
                    await this.chatRepo.updateSessionMetadata(sessionId, metadata);
                }

                // Final complete signal
                yield {
                    type: 'complete',
                    intent: resolvedAction.intent,
                    products,
                    fullText,
                    action,
                    metadata: { model: 'system-agent' }
                };
                return;
            }
        }

        const userType = session.userType || session.user_type || 'customer';
        const intentResult = resolveIntent(userMessage, userType);
        logger.info({ sessionId, intent: intentResult.intent }, 'Stream: Intent resolved');

        await this.chatRepo.addMessage(sessionId, 'user', userMessage, intentResult.intent);

        let fullText = '';
        let products = null;
        let suggestedPrompts = null;
        let metadata = {};
        let response = null;

        const needsRealStream = ['FREE_CHAT'].includes(intentResult.intent);

        if (needsRealStream) {
            // Real LLM streaming
            const chatHistory = await this.chatRepo.getRecentContext(sessionId, 8);
            const messages = [
                ...chatHistory.map(m => ({ role: m.role, content: m.content })),
                { role: 'user', content: userMessage }
            ];

            for await (const token of this.hfClient.chatCompletionStream(messages)) {
                fullText += token;
                yield { type: 'chunk', text: token };
            }

            metadata = { model: this.hfClient.model };
        } else {
            // Data or write intents — get full response then simulate stream
            switch (intentResult.intent) {
                case 'CHECK_STOCK':
                    response = await this.readHandler.handleCheckStock(session, userMessage);
                    break;
                case 'CHECK_PRICE':
                    response = await this.readHandler.handleCheckPrice(session, userMessage);
                    break;
                case 'ORDER_STATUS':
                    response = await this.readHandler.handleOrderStatus(session, userMessage);
                    break;
                case 'RECOMMENDATION':
                    response = await this.readHandler.handleRecommendation(session, userMessage);
                    break;
                case 'SEARCH_PRODUCT':
                    response = await this.readHandler.handleSearchProduct(session, userMessage);
                    break;
                case 'HELP':
                    response = this.utils.handleHelp();
                    break;
                case 'ADD_TO_CART':
                    response = await this._handleAddToCart(session, userMessage);
                    break;
                case 'REMOVE_FROM_CART':
                    response = await this._handleRemoveFromCart(session, userMessage);
                    break;
                case 'UPDATE_CART_ITEM':
                    response = await this._handleUpdateCartItem(session, userMessage);
                    break;
                case 'VIEW_CART':
                    response = this._handleViewCart(session);
                    break;
                case 'TRACK_ORDER':
                    response = await this._handleTrackOrder(session, userMessage);
                    break;
                case 'CANCEL_ORDER':
                    response = await this._handleCustomerCancelOrder(session, userMessage);
                    break;
                case 'CHECKOUT_GUIDE':
                    response = this._handleCheckoutGuide(session);
                    break;
                case 'POS_ADD_ITEM':
                    response = await this.posHandler.handlePosAddItem(session, userMessage);
                    break;
                case 'CREATE_ORDER':
                    response = await this.posHandler.processOrderCollection(session, userMessage);
                    break;
                case 'PAYMENT_CHECK':
                    response = await this.posHandler.handlePaymentCheck(session, userMessage);
                    break;
                default:
                    response = await this.utils.handleFreeChat(sessionId, userMessage);
                    break;
            }

            fullText = response.content || response.reply;
            products = response.products || null;
            suggestedPrompts = response.suggested_prompts || response.suggestedPrompts || null;
            metadata = {
                model: response.model || 'system-agent',
                ragMetadata: response.ragMetadata || null,
                apiCalled: response.apiCalled || null,
                latencyMs: response.latencyMs || null
            };

            // Simulate streaming: yield 3-4 words at a time for smooth UX
            const words = fullText.split(/(\s+)/);
            let buffer = '';
            for (let i = 0; i < words.length; i++) {
                buffer += words[i];
                if ((i + 1) % 6 === 0 || i === words.length - 1) {
                    yield { type: 'chunk', text: buffer };
                    buffer = '';
                    // Small delay for visual effect (10ms)
                    await new Promise(r => setTimeout(r, 10));
                }
            }
        }

        // Save assistant message to DB
        await this.chatRepo.addMessage(sessionId, 'assistant', fullText, intentResult.intent, {
            model: metadata.model || 'system-agent',
            intent: intentResult.intent,
            action: response?.action || null
        });

        // Centralized lastMentionedProducts update for any standard intents that return products
        if (products && products.length > 0) {
            const metadata = session.metadata || {};
            metadata.lastMentionedProducts = products.map(p => ({
                id: p.id,
                name: p.name,
                unitPrice: p.unitPrice || p.price || p.unit_price,
                quantityOnShelf: p.quantityOnShelf || 0,
                image: p.image || null
            }));
            await this.chatRepo.updateSessionMetadata(sessionId, metadata);
        }

        // Final complete signal
        yield {
            type: 'complete',
            intent: intentResult.intent,
            products,
            suggestedPrompts,
            fullText,
            action: response?.action || null,
            metadata
        };
    }
}

module.exports = ChatService;
