const { ValidationError } = require('../../../../shared/common/errors');

class SettingsService {
  constructor({ securitySettingsRepo, salesSettingsRepo, historyRepo, couponRepo, pool }) {
    this.securityRepo = securitySettingsRepo;
    this.salesRepo = salesSettingsRepo;
    this.historyRepo = historyRepo;
    this.couponRepo = couponRepo;
    this.pool = pool;
  }

  async getSecuritySettings() {
    return this.securityRepo.get();
  }

  async getSalesSettings() {
    return this.salesRepo.get();
  }

  /**
   * Get customer discount rates from sales_settings
   * Returns { retail, wholesale, vip } format matching frontend expectations
   */
  async getCustomerDiscounts() {
    const sales = await this.salesRepo.get();
    return {
      retail: parseFloat(sales.discount_retail || 0),
      wholesale: parseFloat(sales.discount_wholesale || 5),
      vip: parseFloat(sales.discount_vip || 10)
    };
  }

  async getHistory(query) {
    return this.historyRepo.findAll(query);
  }

  /**
   * Transaction Zone 1: Update Security Settings & Log History atomically
   */
  async updateSecuritySettings(data, userId, reason) {
    if (!reason) throw new ValidationError('Change reason is required for audit trails');
    const allowed = ['max_failed_attempts', 'lock_duration_minutes'];
    const hasChanges = Object.keys(data).some(k => allowed.includes(k));
    if (!hasChanges) throw new ValidationError('No valid settings fields provided');

    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');

      const oldValue = await this.securityRepo.get();
      const updatedData = { ...data, updated_by: userId };

      const newValue = await this.securityRepo.updateWithClient(client, updatedData);

      await this.historyRepo.createWithClient(client, {
        setting_type: 'security', old_value: oldValue, new_value: newValue,
        changed_by: userId, change_reason: reason
      });

      await client.query('COMMIT');
      return newValue;
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }

  /**
   * Transaction Zone 1: Update Sales Settings & Log History atomically
   */
  async updateSalesSettings(data, userId, reason) {
    if (!reason) throw new ValidationError('Change reason is required for audit trails');
    const allowed = [
      'auto_promotion_enabled', 'promotion_start_time', 'promotion_discount_percentage',
      'discount_retail', 'discount_wholesale', 'discount_vip',
      'apply_to_expiring_today', 'apply_to_expiring_tomorrow'
    ];
    const hasChanges = Object.keys(data).some(k => allowed.includes(k));
    if (!hasChanges) throw new ValidationError('No valid settings fields provided');

    const promotionFields = ['auto_promotion_enabled', 'promotion_start_time', 'promotion_discount_percentage', 'apply_to_expiring_today', 'apply_to_expiring_tomorrow'];
    const promotionChanged = Object.keys(data).some(k => promotionFields.includes(k));

    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');

      const oldValue = await this.salesRepo.get();
      const updatedData = { ...data, updated_by: userId };

      const newValue = await this.salesRepo.updateWithClient(client, updatedData);

      await this.historyRepo.createWithClient(client, {
        setting_type: 'sales', old_value: oldValue, new_value: newValue,
        changed_by: userId, change_reason: reason
      });

      await client.query('COMMIT');

      // Notify Inventory scheduler if promotion config changed
      if (promotionChanged) {
        try {
          const eventBus = require('../../../../shared/event-bus');
          const EVENT = require('../../../../shared/event-bus/eventTypes');
          await eventBus.publish(EVENT.SETTINGS_PROMOTION_UPDATED, newValue);
        } catch (pubErr) {
          // Non-critical — scheduler will pick up on next restart
          console.error('Failed to publish promotion update event:', pubErr.message);
        }
      }

      return newValue;
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }

  /**
   * Get settings change history with pagination and optional type filter
   */
  async getHistory({ settingType, page, limit } = {}) {
    return this.historyRepo.findAll({
      settingType,
      page: parseInt(page) || 1,
      limit: parseInt(limit) || 20
    });
  }

  // ==========================================
  // OMNICHANNEL COUPONS AND USAGES
  // ==========================================

  async getCoupons({ page, limit, search, isActive } = {}) {
    return this.couponRepo.findAll({
      page: parseInt(page) || 1,
      limit: parseInt(limit) || 20,
      search,
      isActive
    });
  }

  async createCoupon(data) {
    if (!data.code) throw new ValidationError('Coupon code is required');

    // Normalize code to uppercase
    const code = data.code.trim().toUpperCase();

    // Check if code exists
    const existing = await this.couponRepo.findByCode(code);
    if (existing) throw new ValidationError('Coupon code already exists');

    return this.couponRepo.create({
      ...data,
      code
    });
  }

  async updateCoupon(id, data) {
    if (data.code) {
      data.code = data.code.trim().toUpperCase();
      const existing = await this.couponRepo.findByCode(data.code);
      if (existing && existing.id !== parseInt(id)) {
        throw new ValidationError('Coupon code already exists');
      }
    }
    const updated = await this.couponRepo.update(id, data);
    if (!updated) throw new ValidationError('Coupon not found');
    return updated;
  }

  async deleteCoupon(id) {
    const deleted = await this.couponRepo.softDelete(id);
    if (!deleted) throw new ValidationError('Coupon not found');
    return deleted;
  }

  async getCouponUsages(couponId, { page, limit } = {}) {
    return this.couponRepo.getUsageHistory(couponId, {
      page: parseInt(page) || 1,
      limit: parseInt(limit) || 20
    });
  }

  async getAvailableCoupons() {
    return this.couponRepo.findAvailable();
  }

  async validateCoupon(code, { customerId, subtotal }) {
    if (!code) throw new ValidationError('Coupon code is required');
    const coupon = await this.couponRepo.findByCode(code.toUpperCase());
    if (!coupon) {
      return { valid: false, error: 'Coupon code not found' };
    }
    if (!coupon.is_active) {
      return { valid: false, error: 'Coupon is inactive' };
    }
    const now = new Date();
    if (coupon.starts_at && new Date(coupon.starts_at) > now) {
      return { valid: false, error: 'Coupon promotion has not started yet' };
    }
    if (coupon.expires_at && new Date(coupon.expires_at) <= now) {
      return { valid: false, error: 'Coupon has expired' };
    }
    if (coupon.max_uses !== null && coupon.used_count >= coupon.max_uses) {
      return { valid: false, error: 'Coupon usage limit reached' };
    }
    if (Number(subtotal) < Number(coupon.min_order_amount)) {
      return {
        valid: false,
        error: `Minimum order amount of ${Number(coupon.min_order_amount).toLocaleString()} VND not met`
      };
    }

    // Check if customer already redeemed this coupon
    if (customerId && customerId !== 'virtual-guest') {
      const usageCount = await this.couponRepo.getCustomerUsageCount(coupon.id, customerId);
      if (usageCount >= 1) {
        return { valid: false, error: 'You have already used this coupon code' };
      }
    }

    return {
      valid: true,
      coupon: {
        id: coupon.id,
        code: coupon.code,
        description: coupon.description,
        discount_type: coupon.discount_type,
        discount_value: Number(coupon.discount_value),
        min_order_amount: Number(coupon.min_order_amount)
      }
    };
  }

  async redeemCoupon(code, customerId, orderId) {
    if (!code) throw new ValidationError('Coupon code is required');
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const coupon = await this.couponRepo.findByCode(code.toUpperCase());
      if (!coupon) {
        throw new ValidationError('Coupon code not found');
      }

      // Perform final check inside transaction
      if (!coupon.is_active) throw new ValidationError('Coupon is inactive');
      if (coupon.max_uses !== null && coupon.used_count >= coupon.max_uses) {
        throw new ValidationError('Coupon usage limit reached');
      }

      if (customerId && customerId !== 'virtual-guest') {
        const usageCount = await this.couponRepo.getCustomerUsageCount(coupon.id, customerId);
        if (usageCount >= 1) {
          throw new ValidationError('You have already used this coupon code');
        }
      }

      // Increment used count
      await this.couponRepo.incrementUsedCount(client, coupon.id);

      // Log usage
      if (customerId) {
        await this.couponRepo.logUsage(client, {
          couponId: coupon.id,
          customerId,
          orderId
        });
      }

      await client.query('COMMIT');
      return { success: true };
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
  }
}

module.exports = SettingsService;
