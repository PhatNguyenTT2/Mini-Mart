const SettingsService = require('../../src/services/settings.service');
const { mockSecurityRepo, mockSalesRepo, mockHistoryRepo, createMockPool } = require('../helpers');

function mockCouponRepo() {
  return {
    findAll: jest.fn(),
    findByCode: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    softDelete: jest.fn(),
    getUsageHistory: jest.fn(),
    findAvailable: jest.fn(),
    getCustomerUsageCount: jest.fn(),
    incrementUsedCount: jest.fn(),
    logUsage: jest.fn()
  };
}

describe('SettingsService - Coupons & Validation', () => {
  let service, securityRepo, salesRepo, historyRepo, couponRepo, pool;

  beforeEach(() => {
    securityRepo = mockSecurityRepo();
    salesRepo = mockSalesRepo();
    historyRepo = mockHistoryRepo();
    couponRepo = mockCouponRepo();
    pool = createMockPool();

    service = new SettingsService({
      securitySettingsRepo: securityRepo,
      salesSettingsRepo: salesRepo,
      historyRepo,
      couponRepo,
      pool
    });
  });

  describe('validateCoupon()', () => {
    it('should fail validation if coupon code does not exist', async () => {
      couponRepo.findByCode.mockResolvedValue(null);
      const res = await service.validateCoupon('NONEXISTENT', { subtotal: 100000 });
      expect(res.valid).toBe(false);
      expect(res.error).toBe('Coupon code not found');
    });

    it('should fail validation if coupon is inactive', async () => {
      couponRepo.findByCode.mockResolvedValue({
        id: 1,
        code: 'TEST10',
        is_active: false,
        discount_type: 'percent',
        discount_value: 10
      });
      const res = await service.validateCoupon('TEST10', { subtotal: 100000 });
      expect(res.valid).toBe(false);
      expect(res.error).toBe('Coupon is inactive');
    });

    it('should fail validation if coupon is expired', async () => {
      const expiredDate = new Date(Date.now() - 3600000).toISOString(); // 1 hour ago
      couponRepo.findByCode.mockResolvedValue({
        id: 1,
        code: 'TEST10',
        is_active: true,
        expires_at: expiredDate,
        discount_type: 'percent',
        discount_value: 10
      });
      const res = await service.validateCoupon('TEST10', { subtotal: 100000 });
      expect(res.valid).toBe(false);
      expect(res.error).toBe('Coupon has expired');
    });

    it('should fail validation if minimum order amount is not met', async () => {
      couponRepo.findByCode.mockResolvedValue({
        id: 1,
        code: 'TEST10',
        is_active: true,
        min_order_amount: 150000,
        discount_type: 'percent',
        discount_value: 10
      });
      const res = await service.validateCoupon('TEST10', { subtotal: 100000 });
      expect(res.valid).toBe(false);
      expect(res.error).toContain('Minimum order amount of 150,000 VND not met');
    });

    it('should fail validation if customer has already used it', async () => {
      couponRepo.findByCode.mockResolvedValue({
        id: 1,
        code: 'WELCOME100',
        is_active: true,
        min_order_amount: 50000,
        discount_type: 'percent',
        discount_value: 10
      });
      couponRepo.getCustomerUsageCount.mockResolvedValue(1); // Already used once

      const res = await service.validateCoupon('WELCOME100', { customerId: 'cust_123', subtotal: 100000 });
      expect(res.valid).toBe(false);
      expect(res.error).toBe('You have already used this coupon code');
    });

    it('should pass validation for valid coupon and meet minimum spend', async () => {
      couponRepo.findByCode.mockResolvedValue({
        id: 1,
        code: 'WELCOME100',
        is_active: true,
        min_order_amount: 50000,
        discount_type: 'percent',
        discount_value: 10,
        description: 'Welcome discount'
      });
      couponRepo.getCustomerUsageCount.mockResolvedValue(0);

      const res = await service.validateCoupon('WELCOME100', { customerId: 'cust_123', subtotal: 100000 });
      expect(res.valid).toBe(true);
      expect(res.coupon.code).toBe('WELCOME100');
      expect(res.coupon.discount_value).toBe(10);
    });
  });

  describe('redeemCoupon()', () => {
    it('should successfully redeem coupon inside transaction and log usage', async () => {
      couponRepo.findByCode.mockResolvedValue({
        id: 5,
        code: 'WELCOME100',
        is_active: true,
        max_uses: 100,
        used_count: 5
      });
      couponRepo.getCustomerUsageCount.mockResolvedValue(0);

      const res = await service.redeemCoupon('WELCOME100', 'cust_123', 99);

      expect(pool._client.query).toHaveBeenCalledWith('BEGIN');
      expect(couponRepo.incrementUsedCount).toHaveBeenCalledWith(pool._client, 5);
      expect(couponRepo.logUsage).toHaveBeenCalledWith(pool._client, {
        couponId: 5,
        customerId: 'cust_123',
        orderId: 99
      });
      expect(pool._client.query).toHaveBeenCalledWith('COMMIT');
      expect(res.success).toBe(true);
    });

    it('should rollback transaction on error', async () => {
      couponRepo.findByCode.mockResolvedValue({
        id: 5,
        code: 'WELCOME150',
        is_active: true,
        max_uses: 10,
        used_count: 10 // Max reached
      });

      await expect(service.redeemCoupon('WELCOME150', 'cust_123', 101))
        .rejects.toThrow('Coupon usage limit reached');

      expect(pool._client.query).toHaveBeenCalledWith('ROLLBACK');
    });
  });
});
