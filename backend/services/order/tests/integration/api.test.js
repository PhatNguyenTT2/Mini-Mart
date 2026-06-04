const request = require('supertest');
const createApp = require('../../src/app');

// Mock dependencies
jest.mock('../../../../shared/auth-middleware', () => ({
    verifyToken: (req, res, next) => {
        const auth = req.headers.authorization;
        if (!auth || !auth.startsWith('Bearer ')) {
            return res.status(401).json({ success: false, error: { message: 'No token', code: 'UNAUTHORIZED' } });
        }
        const storeId = req.headers['x-test-store-id'] ? parseInt(req.headers['x-test-store-id']) : 1;
        req.user = { id: 1, username: 'admin', role: 1, permissions: ['order.view', 'order.manage'], storeId };
        next();
    },
    requirePermission: () => (req, res, next) => next(),
    generateToken: jest.fn().mockReturnValue('mock-jwt-token')
}));

describe('Order API Integration', () => {
    let app, mockOrderService;

    beforeEach(() => {
        mockOrderService = {
            createDraftOrder: jest.fn(),
            getStoreOrders: jest.fn(),
            getOrderById: jest.fn(),
            updateOrderStatus: jest.fn()
        };

        app = createApp({ orderService: mockOrderService });
    });

    // === Orders ===
    describe('GET /api/orders', () => {
        it('should return paginated orders', async () => {
            mockOrderService.getStoreOrders.mockResolvedValue([{ id: 1 }]);
            const res = await request(app).get('/api/orders').set('Authorization', 'Bearer token');
            expect(res.status).toBe(200);
            expect(res.body.data.orders).toHaveLength(1);
        });
    });

    describe('GET /api/orders/:id', () => {
        it('should return order details by ID', async () => {
            mockOrderService.getOrderById.mockResolvedValue({ id: 1, status: 'completed' });
            const res = await request(app).get('/api/orders/1').set('Authorization', 'Bearer token');
            expect(res.status).toBe(200);
            expect(res.body.data.order.status).toBe('completed');
        });
    });

    describe('POST /api/orders', () => {
        it('should create order', async () => {
            mockOrderService.createDraftOrder.mockResolvedValue({ id: 1, status: 'draft' });
            const res = await request(app).post('/api/orders')
                .set('Authorization', 'Bearer token')
                .send({ customerPhone: '0123456789', customerName: 'Test', items: [] });
            expect(res.status).toBe(201);
        });
    });

    describe('PATCH /api/orders/:id/status', () => {
        it('should update status', async () => {
            mockOrderService.updateOrderStatus.mockResolvedValue({ id: 1, status: 'pending' });
            const res = await request(app).patch('/api/orders/1/status')
                .set('Authorization', 'Bearer token')
                .send({ status: 'pending' });
            expect(res.status).toBe(200);
        });
    });
});
