const OrderService = require('../../src/services/order.service');
const { ValidationError, NotFoundError, AppError } = require('../../../../shared/common/errors');

describe('OrderService Unit Tests', () => {
  let mockOrderRepo;
  let mockDetailRepo;
  let mockPool;
  let mockClient;
  let orderService;

  const storeId = 10;
  const userId = 99;

  beforeEach(() => {
    mockOrderRepo = {
      findAll: jest.fn(),
      findById: jest.fn(),
      createOrderWithClient: jest.fn(),
      updateStatusWithClient: jest.fn()
    };

    mockDetailRepo = {
      findByOrderId: jest.fn(),
      addDetailWithClient: jest.fn()
    };

    mockClient = {
      query: jest.fn(),
      release: jest.fn()
    };

    mockPool = {
      connect: jest.fn().mockResolvedValue(mockClient)
    };

    orderService = new OrderService(mockOrderRepo, mockDetailRepo, mockPool);
  });

  describe('createDraftOrder (ZONE 1)', () => {
    const validData = {
      customer_id: 1,
      delivery_type: 'pickup',
      address: '',
      discount_percentage: 10,
      shipping_fee: 0,
      items: [
        { product_name: 'P1', batch_id: 101, quantity: 2, unit_price: 100 }
      ]
    };

    beforeEach(() => {
      jest.spyOn(orderService, 'resolveCustomerDiscount').mockResolvedValue(10);
    });

    it('should create an order with details successfully', async () => {
      mockOrderRepo.createOrderWithClient.mockResolvedValue({ id: 50, store_id: 10, total_amount: 180 });
      mockDetailRepo.findByOrderId.mockResolvedValue([{ id: 1, order_id: 50 }]); // final fetch

      const result = await orderService.createDraftOrder(storeId, validData, userId);

      expect(mockPool.connect).toHaveBeenCalled();
      expect(mockClient.query).toHaveBeenCalledWith('BEGIN');

      // Check total calculation (2 * 100) * 0.9 = 180 
      expect(mockOrderRepo.createOrderWithClient).toHaveBeenCalledWith(
        mockClient, storeId, expect.objectContaining({
          total_amount: 180
        })
      );

      // Check detail insertion
      expect(mockDetailRepo.addDetailWithClient).toHaveBeenCalledWith(
        mockClient, 50, expect.objectContaining({
          product_name: 'P1',
          total_price: 200 // 2 * 100
        })
      );

      expect(mockClient.query).toHaveBeenCalledWith('COMMIT');
      expect(mockClient.release).toHaveBeenCalled();

      expect(result.id).toBe(50);
      expect(result.details).toHaveLength(1);
    });

    it('should throw ValidationError if items is empty', async () => {
      await expect(orderService.createDraftOrder(storeId, { items: [] }, userId))
        .rejects.toThrow(ValidationError);

      expect(mockPool.connect).not.toHaveBeenCalled();
    });

    it('should rollback transaction on error', async () => {
      mockOrderRepo.createOrderWithClient.mockRejectedValue(new Error('DB Failed'));

      await expect(orderService.createDraftOrder(storeId, validData, userId))
        .rejects.toThrow(AppError);

      expect(mockClient.query).toHaveBeenCalledWith('ROLLBACK');
      expect(mockClient.release).toHaveBeenCalled();
    });
  });

  describe('updateOrderStatus', () => {
    it('should properly update statuses', async () => {
      mockOrderRepo.findById.mockResolvedValue({ id: 50 });
      mockOrderRepo.updateStatusWithClient.mockResolvedValue({ id: 50, status: 'shipped', payment_status: 'paid' });

      const res = await orderService.updateOrderStatus(storeId, 50, 'shipped', 'paid');

      expect(mockOrderRepo.updateStatusWithClient).toHaveBeenCalledWith(mockClient, storeId, 50, 'shipped', 'paid', undefined);
      expect(res.status).toBe('shipped');
    });

    it('should cancel payment status for COD orders when order is cancelled', async () => {
      mockOrderRepo.findById.mockResolvedValue({ id: 50, payment_status: 'paid', payment_method: 'cash' });
      mockOrderRepo.updateStatusWithClient.mockResolvedValue({ id: 50, status: 'cancelled', payment_status: 'cancelled', payment_method: 'cash' });

      const res = await orderService.updateOrderStatus(storeId, 50, 'cancelled', undefined);

      expect(mockOrderRepo.updateStatusWithClient).toHaveBeenCalledWith(mockClient, storeId, 50, 'cancelled', 'cancelled', undefined);
      expect(res.paymentStatus).toBe('cancelled');
    });

    it('should keep payment status paid for VNPay orders when order is cancelled', async () => {
      mockOrderRepo.findById.mockResolvedValue({ id: 51, payment_status: 'paid', payment_method: 'vnpay' });
      mockOrderRepo.updateStatusWithClient.mockResolvedValue({ id: 51, status: 'cancelled', payment_status: 'paid', payment_method: 'vnpay' });

      const res = await orderService.updateOrderStatus(storeId, 51, 'cancelled', undefined);

      expect(mockOrderRepo.updateStatusWithClient).toHaveBeenCalledWith(mockClient, storeId, 51, 'cancelled', undefined, undefined);
      expect(res.paymentStatus).toBe('paid');
    });

    it('should cancel payment status for orders with NULL payment method when order is cancelled (smart cancelled)', async () => {
      mockOrderRepo.findById.mockResolvedValue({ id: 54, payment_status: 'paid', payment_method: null });
      mockOrderRepo.updateStatusWithClient.mockResolvedValue({ id: 54, status: 'cancelled', payment_status: 'cancelled', payment_method: null });

      const res = await orderService.updateOrderStatus(storeId, 54, 'cancelled', undefined);

      expect(mockOrderRepo.updateStatusWithClient).toHaveBeenCalledWith(mockClient, storeId, 54, 'cancelled', 'cancelled', undefined);
      expect(res.paymentStatus).toBe('cancelled');
    });
  });

  describe('updateOrder', () => {
    beforeEach(() => {
      mockOrderRepo.updateWithClient = jest.fn();
    });

    it('should cancel payment status for COD orders when cancelled via updateOrder', async () => {
      mockOrderRepo.findById.mockResolvedValue({ id: 50, status: 'shipping', payment_status: 'paid', payment_method: 'cash' });
      mockOrderRepo.updateWithClient.mockResolvedValue({ id: 50, status: 'cancelled', payment_status: 'cancelled', payment_method: 'cash' });

      const res = await orderService.updateOrder(storeId, 50, { status: 'cancelled' });

      expect(mockOrderRepo.updateWithClient).toHaveBeenCalledWith(
        mockClient, storeId, 50, expect.objectContaining({
          status: 'cancelled',
          payment_status: 'cancelled'
        })
      );
      expect(res.paymentStatus).toBe('cancelled');
    });

    it('should keep payment status paid for VNPay orders when cancelled via updateOrder', async () => {
      mockOrderRepo.findById.mockResolvedValue({ id: 51, status: 'shipping', payment_status: 'paid', payment_method: 'vnpay' });
      mockOrderRepo.updateWithClient.mockResolvedValue({ id: 51, status: 'cancelled', payment_status: 'paid', payment_method: 'vnpay' });

      const res = await orderService.updateOrder(storeId, 51, { status: 'cancelled' });

      expect(mockOrderRepo.updateWithClient).toHaveBeenCalledWith(
        mockClient, storeId, 51, expect.objectContaining({
          status: 'cancelled'
        })
      );
      expect(mockOrderRepo.updateWithClient).not.toHaveBeenCalledWith(
        mockClient, storeId, 51, expect.objectContaining({
          payment_status: 'cancelled'
        })
      );
      expect(res.paymentStatus).toBe('paid');
    });

    it('should cancel payment status for COD orders when cancelled via updateOrder sending redundant paymentStatus: paid (frontend style)', async () => {
      mockOrderRepo.findById.mockResolvedValue({ id: 52, status: 'shipping', payment_status: 'paid', payment_method: 'cash' });
      mockOrderRepo.updateWithClient.mockResolvedValue({ id: 52, status: 'cancelled', payment_status: 'cancelled', payment_method: 'cash' });

      const res = await orderService.updateOrder(storeId, 52, { status: 'cancelled', paymentStatus: 'paid' });

      expect(mockOrderRepo.updateWithClient).toHaveBeenCalledWith(
        mockClient, storeId, 52, expect.objectContaining({
          status: 'cancelled',
          payment_status: 'cancelled'
        })
      );
      expect(res.paymentStatus).toBe('cancelled');
    });

    it('should keep payment status paid for VNPay orders when cancelled via updateOrder sending redundant paymentStatus: paid (frontend style)', async () => {
      mockOrderRepo.findById.mockResolvedValue({ id: 53, status: 'shipping', payment_status: 'paid', payment_method: 'vnpay' });
      mockOrderRepo.updateWithClient.mockResolvedValue({ id: 53, status: 'cancelled', payment_status: 'paid', payment_method: 'vnpay' });

      const res = await orderService.updateOrder(storeId, 53, { status: 'cancelled', paymentStatus: 'paid' });

      expect(mockOrderRepo.updateWithClient).toHaveBeenCalledWith(
        mockClient, storeId, 53, expect.objectContaining({
          status: 'cancelled',
          payment_status: 'paid'
        })
      );
      expect(res.paymentStatus).toBe('paid');
    });

    it('should cancel payment status for orders with NULL payment method when cancelled via updateOrder', async () => {
      mockOrderRepo.findById.mockResolvedValue({ id: 55, status: 'shipping', payment_status: 'paid', payment_method: null });
      mockOrderRepo.updateWithClient.mockResolvedValue({ id: 55, status: 'cancelled', payment_status: 'cancelled', payment_method: null });

      const res = await orderService.updateOrder(storeId, 55, { status: 'cancelled', paymentStatus: 'paid' });

      expect(mockOrderRepo.updateWithClient).toHaveBeenCalledWith(
        mockClient, storeId, 55, expect.objectContaining({
          status: 'cancelled',
          payment_status: 'cancelled'
        })
      );
      expect(res.paymentStatus).toBe('cancelled');
    });
  });
});
