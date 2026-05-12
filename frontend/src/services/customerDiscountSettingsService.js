import api from './api'

/**
 * Customer Discount Settings Service
 * Adapted for Settings microservice — reads/writes via /api/settings/sales
 * and /api/customer-discount-settings for public discount data
 */
const customerDiscountSettingsService = {
  /**
   * Get currently active customer discount rates
   * Uses the standalone public endpoint
   */
  getActiveDiscounts: async () => {
    try {
      const response = await api.get('/customer-discount-settings')
      return response.data
    } catch (error) {
      console.error('Error fetching active customer discounts:', error)
      throw error
    }
  },

  /**
   * Get version history of discount changes
   * Uses settings_history table filtered by 'sales' type
   */
  getHistory: async (limit = 50) => {
    try {
      const response = await api.get('/settings/history', {
        params: { settingType: 'sales', limit }
      })
      const apiData = response.data // { success, data: [...], pagination: { total, page, limit } }
      const rawItems = apiData?.data || []
      const total = apiData?.pagination?.total || rawItems.length
      const items = rawItems.map((item, idx) => {
        const oldVal = item.old_value || {}
        const newVal = item.new_value || {}

        // Build changes object — compare old vs new for each discount field
        const changes = {}
        const fields = { retail: 'discount_retail', wholesale: 'discount_wholesale', vip: 'discount_vip' }
        for (const [key, dbField] of Object.entries(fields)) {
          const from = parseFloat(oldVal[dbField] ?? 0)
          const to = parseFloat(newVal[dbField] ?? 0)
          if (from !== to) {
            changes[key] = { from, to }
          }
        }
        // Promotion field changes
        if (oldVal.auto_promotion_enabled !== newVal.auto_promotion_enabled) {
          changes.autoPromotion = { from: oldVal.auto_promotion_enabled, to: newVal.auto_promotion_enabled }
        }
        const oldPct = parseFloat(oldVal.promotion_discount_percentage ?? 0)
        const newPct = parseFloat(newVal.promotion_discount_percentage ?? 0)
        if (oldPct !== newPct) {
          changes.promoDiscount = { from: oldPct, to: newPct }
        }
        if (oldVal.promotion_start_time !== newVal.promotion_start_time) {
          changes.promoStartTime = { from: oldVal.promotion_start_time || '-', to: newVal.promotion_start_time || '-' }
        }

        return {
          version: total - idx,
          isActive: idx === 0,
          discounts: {
            retail: parseFloat(newVal.discount_retail ?? 0),
            wholesale: parseFloat(newVal.discount_wholesale ?? 5),
            vip: parseFloat(newVal.discount_vip ?? 10)
          },
          previousDiscounts: {
            retail: parseFloat(oldVal.discount_retail ?? 0),
            wholesale: parseFloat(oldVal.discount_wholesale ?? 5),
            vip: parseFloat(oldVal.discount_vip ?? 10)
          },
          effectiveFrom: item.changed_at,
          changedBy: { id: item.changed_by },
          changeReason: item.change_reason || 'No reason provided',
          changes
        }
      })
      return { success: true, data: items }
    } catch (error) {
      console.error('Error fetching customer discount history:', error)
      throw error
    }
  },

  /**
   * Update customer discount rates
   * Maps to PUT /settings/sales with change_reason
   */
  updateDiscounts: async ({ retail, wholesale, vip, reason, employeeId }) => {
    try {
      const response = await api.put('/settings/sales', {
        discount_retail: parseFloat(retail),
        discount_wholesale: parseFloat(wholesale),
        discount_vip: parseFloat(vip),
        change_reason: reason || 'Manual update'
      })
      return { success: true, data: response.data?.data || response.data }
    } catch (error) {
      console.error('Error updating customer discounts:', error)
      throw error
    }
  },

  /**
   * Reset discount settings to default values
   * Maps to PUT /settings/sales with default values
   */
  resetToDefaults: async ({ reason, employeeId } = {}) => {
    try {
      const response = await api.put('/settings/sales', {
        discount_retail: 0,
        discount_wholesale: 5,
        discount_vip: 10,
        change_reason: reason || 'Reset to default values'
      })
      const data = response.data?.data || response.data
      return {
        success: true,
        data: {
          discounts: {
            retail: parseFloat(data.discount_retail ?? 0),
            wholesale: parseFloat(data.discount_wholesale ?? 5),
            vip: parseFloat(data.discount_vip ?? 10)
          }
        }
      }
    } catch (error) {
      console.error('Error resetting customer discounts:', error)
      throw error
    }
  },

  /**
   * Rollback is no longer supported in microservice architecture
   * History entries are immutable audit trails
   */
  rollbackToVersion: async () => {
    return { success: false, error: 'Rollback not available. Create a new version instead.' }
  }
}

export default customerDiscountSettingsService
