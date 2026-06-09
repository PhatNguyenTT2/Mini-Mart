import api from './api';

const couponService = {
  /**
   * Get available public coupons for the checkout coupon drawer
   */
  async getAvailableCoupons() {
    const res = await api.get('/coupons/available');
    return res.data;
  },

  /**
   * Validate a coupon code before applying it
   * body: { code, subtotal }
   */
  async validateCoupon(code, subtotal) {
    const res = await api.post('/coupons/validate', { code, subtotal });
    return res.data;
  },

  /**
   * Get customer discount settings (retail, wholesale, vip rates)
   */
  async getCustomerDiscounts() {
    const res = await api.get('/customer-discount-settings');
    return res.data;
  }
};

export default couponService;
