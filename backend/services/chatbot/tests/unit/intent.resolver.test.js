const { resolveIntent, getAllIntents, INTENT_PATTERNS } = require('../../src/services/intent.resolver');

describe('Intent Resolver', () => {
    describe('resolveIntent', () => {
        it('should detect CHECK_STOCK intent', () => {
            const result = resolveIntent('Sản phẩm Coca Cola còn hàng không?');
            expect(result.intent).toBe('CHECK_STOCK');
            expect(result.matchedKeyword).toBe('còn hàng');
        });

        it('should detect CHECK_STOCK with "tồn kho"', () => {
            const result = resolveIntent('Kiểm tra tồn kho mì gói');
            expect(result.intent).toBe('CHECK_STOCK');
        });

        it('should detect CHECK_PRICE intent', () => {
            const result = resolveIntent('Nước ngọt Pepsi giá bao nhiêu?');
            expect(result.intent).toBe('CHECK_PRICE');
            expect(result.matchedKeyword).toBe('giá');
        });

        it('should detect ORDER_STATUS intent', () => {
            const result = resolveIntent('Kiểm tra trạng thái đơn hàng #123');
            expect(result.intent).toBe('ORDER_STATUS');
        });

        it('should detect TRACK_ORDER intent', () => {
            const result = resolveIntent('Đơn hàng #123 đang ở đâu rồi?');
            expect(result.intent).toBe('TRACK_ORDER');
        });

        it('should detect SEARCH_PRODUCT intent', () => {
            const result = resolveIntent('Tìm sản phẩm giống nước rửa tay');
            expect(result.intent).toBe('SEARCH_PRODUCT');
        });

        it('should detect HELP intent', () => {
            const result = resolveIntent('Hướng dẫn sử dụng ứng dụng');
            expect(result.intent).toBe('HELP');
        });

        it('should return FREE_CHAT for unrecognized messages', () => {
            const result = resolveIntent('Hôm nay trời đẹp quá');
            expect(result.intent).toBe('FREE_CHAT');
            expect(result.confidence).toBe('default');
            expect(result.matchedKeyword).toBeNull();
        });

        it('should be case-insensitive', () => {
            const result = resolveIntent('STOCK còn không?');
            expect(result.intent).toBe('CHECK_STOCK');
        });

        it('should handle empty string', () => {
            const result = resolveIntent('');
            expect(result.intent).toBe('FREE_CHAT');
        });

        it('should prioritize first matching intent', () => {
            // "giá" matches CHECK_PRICE before "tìm" matches SEARCH
            const result = resolveIntent('giá sản phẩm này');
            expect(result.intent).toBe('CHECK_PRICE');
        });

        it('should allow managerOnly intents for manager', () => {
            const result = resolveIntent('doanh thu hôm nay', 'manager');
            expect(result.intent).toBe('REPORT_SALES');
        });

        it('should block managerOnly intents for customer', () => {
            const result = resolveIntent('doanh thu hôm nay', 'customer');
            expect(result.intent).toBe('FREE_CHAT'); // falls back to FREE_CHAT
        });

        it('should block managerOnly intents for employee', () => {
            const result = resolveIntent('doanh thu hôm nay', 'employee');
            expect(result.intent).toBe('FREE_CHAT');
        });

        it('should allow employeeOnly intents for employee', () => {
            const result = resolveIntent('lịch sử đơn hàng', 'employee');
            expect(result.intent).toBe('VIEW_ORDER_HISTORY');
        });

        it('should block employeeOnly intents for customer', () => {
            const result = resolveIntent('lịch sử đơn hàng', 'customer');
            expect(result.intent).toBe('ORDER_STATUS');
        });

        it('should resolve direct "thêm" patterns to ADD_TO_CART for customer', () => {
            const result = resolveIntent('thêm 2 coca', 'customer');
            expect(result.intent).toBe('ADD_TO_CART');
        });

        it('should resolve direct "thêm" patterns to POS_ADD_ITEM for employee', () => {
            const result = resolveIntent('thêm 2 coca', 'employee');
            expect(result.intent).toBe('POS_ADD_ITEM');
        });

        it('should not resolve "bán chạy" reporting queries to POS_ADD_ITEM for manager', () => {
            const result = resolveIntent('Sản phẩm nào bán chạy nhất tháng này?', 'manager');
            expect(result.intent).toBe('REPORT_TOP_PRODUCTS');
        });
    });

    describe('getAllIntents', () => {
        it('should return all defined intents', () => {
            const intents = getAllIntents();
            expect(intents.length).toBe(Object.keys(INTENT_PATTERNS).length);
            expect(intents[0]).toHaveProperty('intent');
            expect(intents[0]).toHaveProperty('keywords');
            expect(intents[0]).toHaveProperty('description');
        });
    });
});
