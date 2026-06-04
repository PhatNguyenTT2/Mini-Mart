const ChatService = require('../../src/services/chat.service');
const { ValidationError, NotFoundError } = require('../../../../shared/common/errors');

describe('ChatService Unit Tests', () => {
    let mockChatRepo;
    let mockHFClient;
    let mockApiClient;
    let chatService;

    beforeEach(() => {
        mockChatRepo = {
            createSession: jest.fn(),
            findSessionById: jest.fn(),
            findSessionsByUser: jest.fn(),
            endSession: jest.fn(),
            addMessage: jest.fn().mockResolvedValue({ id: 1 }),
            getMessagesBySession: jest.fn(),
            getRecentContext: jest.fn().mockResolvedValue([]),
            updateSessionMetadata: jest.fn().mockResolvedValue(true)
        };

        mockHFClient = {
            chatCompletion: jest.fn().mockResolvedValue({
                content: 'AI response here',
                model: 'test-model',
                latencyMs: 150
            })
        };

        mockApiClient = {
            searchProducts: jest.fn(),
            getProductById: jest.fn(),
            getInventorySummary: jest.fn(),
            getOrderById: jest.fn(),
            getOrders: jest.fn(),
            cancelOrder: jest.fn(),
            createOrder: jest.fn()
        };

        chatService = new ChatService(mockChatRepo, mockHFClient, mockApiClient);
    });

    describe('startSession', () => {
        it('should create a new session', async () => {
            mockChatRepo.createSession.mockResolvedValue({ id: 1, user_id: 10, user_type: 'employee' });
            const session = await chatService.startSession(10, 'employee', 1);
            expect(mockChatRepo.createSession).toHaveBeenCalledWith(10, 'employee', 1);
            expect(session.id).toBe(1);
        });

        it('should throw ValidationError if userId missing', async () => {
            await expect(chatService.startSession(null, 'employee'))
                .rejects.toThrow(ValidationError);
        });

        it('should throw ValidationError if userType invalid', async () => {
            await expect(chatService.startSession(1, 'admin'))
                .rejects.toThrow(ValidationError);
        });
    });

    describe('sendMessage — base flow', () => {
        beforeEach(() => {
            mockChatRepo.findSessionById.mockResolvedValue({ id: 1, is_active: true });
        });

        it('should process FREE_CHAT and call HF', async () => {
            const result = await chatService.sendMessage(1, 'Xin chào, hôm nay thế nào?');
            expect(result.intent).toBe('FREE_CHAT');
            expect(result.reply).toBe('AI response here');
            expect(mockHFClient.chatCompletion).toHaveBeenCalled();
            expect(mockChatRepo.addMessage).toHaveBeenCalledTimes(2);
        });

        it('should return HELP without calling HF', async () => {
            const result = await chatService.sendMessage(1, 'Giúp tôi');
            expect(result.intent).toBe('HELP');
            expect(result.reply).toContain('tồn kho');
            expect(mockHFClient.chatCompletion).not.toHaveBeenCalled();
        });

        it('should throw ValidationError for empty message', async () => {
            await expect(chatService.sendMessage(1, '')).rejects.toThrow(ValidationError);
        });

        it('should throw NotFoundError for non-existent session', async () => {
            mockChatRepo.findSessionById.mockResolvedValue(null);
            await expect(chatService.sendMessage(999, 'Hello')).rejects.toThrow(NotFoundError);
        });

        it('should throw ValidationError for ended session', async () => {
            mockChatRepo.findSessionById.mockResolvedValue({ id: 1, is_active: false });
            await expect(chatService.sendMessage(1, 'Hello')).rejects.toThrow(ValidationError);
        });

        it('should save metadata with assistant response', async () => {
            await chatService.sendMessage(1, 'Hôm nay thế nào?');
            const assistantCall = mockChatRepo.addMessage.mock.calls[1];
            expect(assistantCall[1]).toBe('assistant');
            expect(assistantCall[4]).toHaveProperty('model');
            expect(assistantCall[4]).toHaveProperty('latencyMs');
        });
    });

    describe('sendMessage — CHECK_STOCK (with apiClient)', () => {
        beforeEach(() => {
            mockChatRepo.findSessionById.mockResolvedValue({ id: 1, is_active: true });
        });

        it('should call searchProducts + getInventorySummary and return AI-formatted response', async () => {
            mockApiClient.searchProducts.mockResolvedValue({
                success: true,
                data: { products: [{ id: 5, name: 'Coca Cola 330ml' }] }
            });
            mockApiClient.getInventorySummary.mockResolvedValue({
                success: true,
                data: { summary: [{ quantity_on_hand: 50, quantity_on_shelf: 30 }] }
            });

            const result = await chatService.sendMessage(1, 'Coca Cola còn hàng không?');

            expect(result.intent).toBe('CHECK_STOCK');
            expect(mockApiClient.searchProducts).toHaveBeenCalled();
            expect(mockApiClient.getInventorySummary).toHaveBeenCalled();
            expect(mockHFClient.chatCompletion).toHaveBeenCalled();
            expect(result.metadata.apiCalled).toBe('inventory:summary');
        });

        it('should handle product not found', async () => {
            mockApiClient.searchProducts.mockResolvedValue({
                success: true,
                data: { products: [] }
            });

            const result = await chatService.sendMessage(1, 'ABC XYZ còn hàng không?');

            expect(result.intent).toBe('CHECK_STOCK');
            expect(mockApiClient.getInventorySummary).not.toHaveBeenCalled();
            expect(mockHFClient.chatCompletion).toHaveBeenCalled();
        });
    });

    describe('sendMessage — CHECK_PRICE (with apiClient)', () => {
        beforeEach(() => {
            mockChatRepo.findSessionById.mockResolvedValue({ id: 1, is_active: true });
        });

        it('should return price list from Catalog', async () => {
            mockApiClient.searchProducts.mockResolvedValue({
                success: true,
                data: {
                    products: [
                        { name: 'Pepsi 330ml', selling_price: 12000 },
                        { name: 'Pepsi 500ml', selling_price: 15000 }
                    ]
                }
            });

            const result = await chatService.sendMessage(1, 'Pepsi giá bao nhiêu?');

            expect(result.intent).toBe('CHECK_PRICE');
            expect(mockApiClient.searchProducts).toHaveBeenCalled();
            expect(mockHFClient.chatCompletion).toHaveBeenCalled();
            expect(result.metadata.apiCalled).toBe('catalog:products');
        });
    });

    describe('sendMessage — ORDER_STATUS (with apiClient)', () => {
        beforeEach(() => {
            mockChatRepo.findSessionById.mockResolvedValue({ id: 1, is_active: true });
        });

        it('should fetch order by ID when # is present', async () => {
            mockApiClient.getOrderById.mockResolvedValue({
                success: true,
                data: { order: { id: 123, status: 'completed', payment_status: 'paid', total_amount: 500000 } }
            });

            const result = await chatService.sendMessage(1, 'Đơn hàng #123 đến đâu rồi?');

            expect(result.intent).toBe('ORDER_STATUS');
            expect(mockApiClient.getOrderById).toHaveBeenCalledWith('123');
            expect(result.metadata.apiCalled).toBe('order:detail');
        });

        it('should list recent orders when no ID', async () => {
            mockApiClient.getOrders.mockResolvedValue({
                success: true,
                data: {
                    orders: [
                        { id: 1, status: 'draft', payment_status: 'pending', total_amount: 100000 }
                    ]
                }
            });

            const result = await chatService.sendMessage(1, 'Kiểm tra đơn hàng');

            expect(result.intent).toBe('ORDER_STATUS');
            expect(mockApiClient.getOrders).toHaveBeenCalled();
            expect(result.metadata.apiCalled).toBe('order:list');
        });

        it('should handle order not found', async () => {
            mockApiClient.getOrderById.mockResolvedValue({
                success: false,
                error: 'Not found'
            });

            const result = await chatService.sendMessage(1, 'Đơn hàng #999 đến đâu?');

            expect(result.intent).toBe('ORDER_STATUS');
            expect(mockHFClient.chatCompletion).toHaveBeenCalled();
        });
    });

    describe('sendMessage — SEARCH_PRODUCT (with apiClient)', () => {
        beforeEach(() => {
            mockChatRepo.findSessionById.mockResolvedValue({ id: 1, is_active: true });
        });

        it('should search and return product list', async () => {
            mockApiClient.searchProducts.mockResolvedValue({
                success: true,
                data: {
                    products: [
                        { name: 'Nước rửa tay Lifebuoy', selling_price: 35000, is_active: true },
                        { name: 'Nước rửa tay Dettol', selling_price: 42000, is_active: true }
                    ]
                }
            });

            const result = await chatService.sendMessage(1, 'Tìm nước rửa tay');

            expect(result.intent).toBe('SEARCH_PRODUCT');
            expect(mockApiClient.searchProducts).toHaveBeenCalled();
            expect(result.metadata.apiCalled).toBe('catalog:search');
        });
    });

    describe('sendMessage — fallback without apiClient', () => {
        let chatServiceNoApi;

        beforeEach(() => {
            chatServiceNoApi = new ChatService(mockChatRepo, mockHFClient, null);
            mockChatRepo.findSessionById.mockResolvedValue({ id: 1, is_active: true });
        });

        it('should return fallback for CHECK_STOCK when no apiClient', async () => {
            const result = await chatServiceNoApi.sendMessage(1, 'Coca Cola còn hàng không?');
            expect(result.intent).toBe('CHECK_STOCK');
            expect(result.reply).toContain('kiểm tra tồn kho');
            expect(mockHFClient.chatCompletion).not.toHaveBeenCalled();
        });

        it('should return fallback for CHECK_PRICE when no apiClient', async () => {
            const result = await chatServiceNoApi.sendMessage(1, 'Pepsi giá bao nhiêu?');
            expect(result.intent).toBe('CHECK_PRICE');
            expect(result.reply).toContain('kiểm tra giá');
        });
    });

    describe('sendMessage — RECOMMENDATION (with RAG)', () => {
        let chatServiceWithRag;
        let mockRagService;

        beforeEach(() => {
            mockRagService = {
                recommend: jest.fn().mockResolvedValue({
                    content: 'Gợi ý: Bia Tiger 15.000đ',
                    productIds: [42, 55],
                    products: [
                        { id: 42, name: 'Bia Tiger', unitPrice: 15000, rrfScore: 0.032 }
                    ],
                    metadata: { totalLatencyMs: 200 }
                })
            };
            chatServiceWithRag = new ChatService(mockChatRepo, mockHFClient, mockApiClient, mockRagService);
            mockChatRepo.findSessionById.mockResolvedValue({
                id: 1, user_id: 10, user_type: 'customer', store_id: 1, is_active: true
            });
        });

        it('should delegate to ragService.recommend for RECOMMENDATION intent', async () => {
            const result = await chatServiceWithRag.sendMessage(1, 'Gợi ý bia ngon đi');

            expect(result.intent).toBe('RECOMMENDATION');
            expect(mockRagService.recommend).toHaveBeenCalledWith(
                'Gợi ý bia ngon đi', 1, 10, expect.any(Array)
            );
            expect(result.reply).toContain('Bia Tiger');
            expect(result.products).toBeDefined();
        });

        it('should fallback to search when ragService is null', async () => {
            const noRagService = new ChatService(mockChatRepo, mockHFClient, mockApiClient, null);
            mockApiClient.searchProducts.mockResolvedValue({
                success: true, data: { products: [{ name: 'Test', unitPrice: 1000, isActive: true }] }
            });

            const result = await noRagService.sendMessage(1, 'Gợi ý sản phẩm cho tôi');

            expect(result.intent).toBe('RECOMMENDATION');
            // Should fallback to search
            expect(mockApiClient.searchProducts).toHaveBeenCalled();
        });
    });

    describe('sendMessage — SEARCH_PRODUCT (with RAG)', () => {
        let chatServiceWithRag;
        let mockRagService;

        beforeEach(() => {
            mockRagService = {
                recommend: jest.fn().mockResolvedValue({
                    content: 'Tìm thấy: Nước rửa tay Lifebuoy',
                    productIds: [10],
                    products: [{ id: 10, name: 'Lifebuoy', unitPrice: 35000 }],
                    metadata: {}
                })
            };
            chatServiceWithRag = new ChatService(mockChatRepo, mockHFClient, mockApiClient, mockRagService);
            mockChatRepo.findSessionById.mockResolvedValue({
                id: 1, user_id: 10, user_type: 'customer', store_id: 1, is_active: true
            });
        });

        it('should use RAG pipeline when ragService available', async () => {
            const result = await chatServiceWithRag.sendMessage(1, 'Tìm nước rửa tay');

            expect(result.intent).toBe('SEARCH_PRODUCT');
            expect(mockRagService.recommend).toHaveBeenCalled();
            expect(result.products).toBeDefined();
        });

        it('should fallback to HTTP search when no RAG', async () => {
            const noRag = new ChatService(mockChatRepo, mockHFClient, mockApiClient, null);
            mockApiClient.searchProducts.mockResolvedValue({
                success: true, data: { products: [{ name: 'Dettol', unitPrice: 42000, isActive: true }] }
            });

            const result = await noRag.sendMessage(1, 'Tìm nước rửa tay');

            expect(result.intent).toBe('SEARCH_PRODUCT');
            expect(mockApiClient.searchProducts).toHaveBeenCalled();
        });
    });

    describe('getSession / endSession', () => {
        it('should return session if found', async () => {
            mockChatRepo.findSessionById.mockResolvedValue({ id: 1 });
            expect((await chatService.getSession(1)).id).toBe(1);
        });

        it('should throw NotFoundError if not found', async () => {
            mockChatRepo.findSessionById.mockResolvedValue(null);
            await expect(chatService.getSession(999)).rejects.toThrow(NotFoundError);
        });

        it('should end active session', async () => {
            mockChatRepo.findSessionById.mockResolvedValue({ id: 1, is_active: true });
            mockChatRepo.endSession.mockResolvedValue({ id: 1, is_active: false });
            expect((await chatService.endSession(1)).is_active).toBe(false);
        });
    });

    describe('sendMessage — Phase 2 customer actions', () => {
        beforeEach(() => {
            mockChatRepo.findSessionById.mockResolvedValue({
                id: 1,
                is_active: true,
                store_id: 1,
                user_id: 10,
                user_type: 'customer',
                metadata: {}
            });
            chatService.ragService = {
                embeddingClient: {
                    isReady: true,
                    embed: jest.fn().mockResolvedValue(new Array(768).fill(0.1))
                },
                knowledgeRepo: {
                    searchSemantic: jest.fn(),
                    searchKeyword: jest.fn().mockResolvedValue([])
                }
            };
            chatService.utils.ragService = chatService.ragService;
            chatService.readHandler.ragService = chatService.ragService;
        });

        it('should handle ADD_TO_CART with single RAG match', async () => {
            chatService.ragService.knowledgeRepo.searchSemantic.mockResolvedValue([
                { product_id: 4, content: 'Tên: "Sting dâu"', score: 0.92, unit_price: 10000 }
            ]);
            mockApiClient.getInventorySummary.mockResolvedValue({
                success: true, data: [{ productId: 4, quantityOnShelf: 15 }]
            });

            const result = await chatService.sendMessage(1, 'Thêm 3 chai sting dâu vào giỏ hàng');
            expect(result.intent).toBe('ADD_TO_CART');
            expect(result.reply).toContain('Đã thêm 3 "Sting dâu" vào giỏ hàng thành công.');
            expect(result.action).toEqual({
                type: 'ADD_TO_CART',
                payload: { productId: 4, quantity: 3, name: 'Sting dâu', price: 10000 }
            });
        });

        it('should trigger CLARIFYING state for ambiguous matches', async () => {
            chatService.ragService.knowledgeRepo.searchSemantic.mockResolvedValue([
                { product_id: 4, content: 'Tên: "Sting dâu"', score: 0.88, unit_price: 10000 },
                { product_id: 5, content: 'Tên: "Sting vàng"', score: 0.85, unit_price: 10000 }
            ]);

            const result = await chatService.sendMessage(1, 'Thêm sting vào giỏ');
            expect(result.intent).toBe('ADD_TO_CART');
            expect(result.reply).toContain('Tôi tìm thấy một vài sản phẩm phù hợp');
            expect(mockChatRepo.updateSessionMetadata).toHaveBeenCalled();
        });

        it('should resolve clarification state on selecting matching index', async () => {
            mockChatRepo.findSessionById.mockResolvedValue({
                id: 1,
                is_active: true,
                store_id: 1,
                user_id: 10,
                user_type: 'customer',
                metadata: {
                    pendingAction: {
                        type: 'ADD_TO_CART',
                        state: 'CLARIFYING',
                        data: {
                            quantity: 2,
                            candidates: [
                                { id: 4, name: 'Sting dâu', unitPrice: 10000 },
                                { id: 5, name: 'Sting vàng', unitPrice: 10000 }
                            ]
                        }
                    }
                }
            });

            mockApiClient.getInventorySummary.mockResolvedValue({
                success: true, data: [{ productId: 4, quantityOnShelf: 10 }]
            });

            const result = await chatService.sendMessage(1, '1');
            expect(result.intent).toBe('ADD_TO_CART');
            expect(result.reply).toContain('Đã thêm 2 "Sting dâu"');
        });

        it('should guide to checkout', async () => {
            const result = await chatService.sendMessage(1, 'Thanh toán giỏ hàng');
            expect(result.intent).toBe('CHECKOUT_GUIDE');
            expect(result.action).toEqual({
                type: 'NAVIGATE',
                payload: { path: '/checkout' }
            });
        });

        it('should trigger confirmation gate for CANCEL_ORDER', async () => {
            mockApiClient.getOrderById.mockResolvedValue({
                success: true, data: { id: 123, customerId: 10, status: 'draft' }
            });

            const result = await chatService.sendMessage(1, 'Hủy đơn hàng 123');
            expect(result.intent).toBe('CANCEL_ORDER');
            expect(result.reply).toContain('Bạn có chắc chắn muốn hủy đơn hàng #123 không?');
        });

        it('should execute order cancellation after user confirmation', async () => {
            mockChatRepo.findSessionById.mockResolvedValue({
                id: 1,
                is_active: true,
                user_id: 10,
                user_type: 'customer',
                metadata: {
                    pendingAction: {
                        type: 'CANCEL_ORDER',
                        state: 'CONFIRMING',
                        data: { orderId: 123 }
                    }
                }
            });

            mockApiClient.getOrderById.mockResolvedValue({
                success: true, data: { id: 123, customerId: 10, status: 'draft' }
            });
            mockApiClient.cancelOrder.mockResolvedValue({ success: true });

            const result = await chatService.sendMessage(1, 'Đồng ý');
            expect(result.reply).toContain('Đã hủy đơn hàng #123 thành công.');
            expect(mockApiClient.cancelOrder).toHaveBeenCalledWith(123);
        });

        it('should enforce employee role for POS_ADD_ITEM and CREATE_ORDER', async () => {
            chatService.ragService.knowledgeRepo.searchSemantic.mockResolvedValue([
                { product_id: 4, content: 'Tên: "Sting dâu"', score: 0.92, unit_price: 10000 }
            ]);

            const result = await chatService._handlePosAddItem({
                id: 1,
                user_id: 10,
                user_type: 'customer',
                metadata: {}
            }, 'Thêm Sting vào POS');
            expect(result.reply).toContain('Access denied');
        });

        it('should handle POS_ADD_ITEM for employee', async () => {
            mockChatRepo.findSessionById.mockResolvedValue({
                id: 1,
                is_active: true,
                user_type: 'employee',
                metadata: {}
            });
            chatService.ragService.knowledgeRepo.searchSemantic.mockResolvedValue([
                { product_id: 4, content: 'Tên: "Sting dâu"', score: 0.92, unit_price: 10000 }
            ]);
            mockApiClient.getInventorySummary.mockResolvedValue({
                success: true,
                data: [{ quantityOnShelf: 10 }]
            });

            const result = await chatService.sendMessage(1, 'Thêm 2 Sting vào POS');
            expect(result.intent).toBe('POS_ADD_ITEM');
            expect(result.reply).toContain('Đã thêm 2 "Sting dâu" vào POS thành công.');
        });

        it('should run multi-turn CREATE_ORDER flow', async () => {
            // 1. Initial trigger with "tạo đơn" -> COLLECTIONS state
            mockChatRepo.findSessionById.mockResolvedValue({
                id: 1,
                is_active: true,
                user_type: 'employee',
                user_id: 10,
                store_id: 1,
                metadata: {}
            });

            let result = await chatService.sendMessage(1, 'Tạo đơn');
            expect(result.intent).toBe('CREATE_ORDER');
            expect(result.reply).toContain('Vui lòng cung cấp danh sách sản phẩm');

            // 2. Feed items -> CONFIRMATION State
            mockChatRepo.findSessionById.mockResolvedValue({
                id: 1,
                is_active: true,
                user_type: 'employee',
                user_id: 10,
                store_id: 1,
                metadata: {
                    pendingAction: {
                        type: 'CREATE_ORDER',
                        state: 'COLLECTING',
                        data: { items: [] }
                    }
                }
            });
            chatService.ragService.knowledgeRepo.searchSemantic.mockResolvedValue([
                { product_id: 4, content: 'Tên: "Sting dâu"', score: 0.92, unit_price: 10000 }
            ]);

            result = await chatService.sendMessage(1, '2 Sting dâu');
            expect(result.intent).toBe('CREATE_ORDER');
            expect(result.reply).toContain('Bạn có chắc muốn tạo đơn hàng mới');

            // 3. Confirm target execution
            mockChatRepo.findSessionById.mockResolvedValue({
                id: 1,
                is_active: true,
                user_type: 'employee',
                user_id: 10,
                store_id: 1,
                metadata: {
                    pendingAction: {
                        type: 'CREATE_ORDER',
                        state: 'CONFIRMING',
                        data: {
                            orderData: {
                                customerId: 10,
                                storeId: 1,
                                items: [{ productId: 4, quantity: 2, price: 10000 }]
                            },
                            items: [{ productId: 4, name: 'Sting dâu', quantity: 2, price: 10000 }]
                        }
                    }
                }
            });
            mockApiClient.createOrder.mockResolvedValue({ success: true, id: 999 });

            result = await chatService.sendMessage(1, 'Đồng ý');
            expect(result.reply).toContain('Đã tạo đơn hàng mới thành công. ID đơn hàng: #999');
        });

        it('should perform PAYMENT_CHECK', async () => {
            mockChatRepo.findSessionById.mockResolvedValue({
                id: 1,
                is_active: true,
                user_type: 'employee',
                metadata: {}
            });
            mockApiClient.getOrderById.mockResolvedValue({
                success: true,
                data: { id: 123, paymentStatus: 'paid' }
            });

            const result = await chatService.sendMessage(1, 'Kiểm tra thanh toán đơn #123');
            expect(result.intent).toBe('PAYMENT_CHECK');
            expect(result.reply).toContain('Trạng thái thanh toán của đơn hàng #123 hiện tại là: **Đã thanh toán**.');
        });
    });
});
