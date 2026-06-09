import api from './api'

/**
 * Settings Service
 * Handles API calls to Settings microservice (:3004)
 * Endpoints: /api/settings/security, /api/settings/sales, /api/settings/history
 */
const settingsService = {
  // ========== SECURITY SETTINGS ==========

  /**
   * Get security settings (POS PIN auth config)
   * @returns {Promise<Object>} { max_failed_attempts, lock_duration_minutes }
   */
  getSecuritySettings: async () => {
    try {
      const response = await api.get('/settings/security')
      return response.data
    } catch (error) {
      console.error('Error fetching security settings:', error)
      throw error
    }
  },

  /**
   * Alias for POS Management page compatibility
   */
  getPOSSecurity: async () => {
    try {
      const response = await api.get('/settings/security')
      const data = response.data?.data || response.data
      return {
        success: true,
        data: {
          maxFailedAttempts: data.max_failed_attempts ?? 5,
          lockDurationMinutes: data.lock_duration_minutes ?? 15
        }
      }
    } catch (error) {
      console.error('Error fetching POS security:', error)
      return { success: false, data: { maxFailedAttempts: 5, lockDurationMinutes: 15 } }
    }
  },

  /**
   * Update security settings
   * @param {Object} settings - { maxFailedAttempts, lockDurationMinutes }
   * @param {string} reason - Reason for change (required for audit)
   */
  updateSecuritySettings: async (settings, reason = 'Manual update') => {
    try {
      const response = await api.put('/settings/security', {
        max_failed_attempts: parseInt(settings.maxFailedAttempts),
        lock_duration_minutes: parseInt(settings.lockDurationMinutes),
        change_reason: reason
      })
      return response.data
    } catch (error) {
      console.error('Error updating security settings:', error)
      throw error
    }
  },

  /**
   * Alias: Update POS security (used by POSSecuritySettings component)
   */
  updatePOSSecurity: async (security, reason = 'Manual update') => {
    return settingsService.updateSecuritySettings(security, reason)
  },

  /**
   * Reset POS security to defaults
   */
  resetPOSSecurity: async () => {
    try {
      const response = await api.put('/settings/security', {
        max_failed_attempts: 5,
        lock_duration_minutes: 30,
        change_reason: 'Reset to default values'
      })
      const data = response.data?.data || response.data
      return {
        success: true,
        data: {
          maxFailedAttempts: data.max_failed_attempts ?? 5,
          lockDurationMinutes: data.lock_duration_minutes ?? 30
        }
      }
    } catch (error) {
      console.error('Error resetting POS security:', error)
      throw error
    }
  },

  /**
   * Validate POS security settings (client-side)
   */
  validatePOSSecurity: (security) => {
    const errors = []
    if (security.maxFailedAttempts !== undefined) {
      const attempts = parseInt(security.maxFailedAttempts)
      if (isNaN(attempts) || attempts < 1 || attempts > 10) {
        errors.push('Max failed attempts must be between 1 and 10')
      }
    }
    if (security.lockDurationMinutes !== undefined) {
      const duration = parseInt(security.lockDurationMinutes)
      if (isNaN(duration) || duration < 1 || duration > 1440) {
        errors.push('Lock duration must be between 1 and 1440 minutes')
      }
    }
    return { valid: errors.length === 0, errors }
  },

  /**
   * Format lock duration for display
   */
  formatLockDuration: (minutes) => {
    const mins = parseInt(minutes)
    if (isNaN(mins)) return '0m'
    if (mins < 60) return `${mins}m`
    const hours = Math.floor(mins / 60)
    const remainingMins = mins % 60
    return remainingMins === 0 ? `${hours}h` : `${hours}h ${remainingMins}m`
  },

  // ========== SALES SETTINGS ==========

  /**
   * Get sales settings (discounts, promotion config)
   * @returns {Promise<Object>} sales_settings row
   */
  getSalesSettings: async () => {
    try {
      const response = await api.get('/settings/sales')
      return response.data
    } catch (error) {
      console.error('Error fetching sales settings:', error)
      throw error
    }
  },

  /**
   * Update sales settings
   * @param {Object} data - snake_case fields to update
   * @param {string} reason - Reason for change
   */
  updateSalesSettings: async (data, reason = 'Manual update') => {
    try {
      const response = await api.put('/settings/sales', {
        ...data,
        change_reason: reason
      })
      return response.data
    } catch (error) {
      console.error('Error updating sales settings:', error)
      throw error
    }
  },

  // ========== SETTINGS HISTORY ==========

  /**
   * Get settings change history
   * @param {Object} params - { settingType, page, limit }
   */
  getHistory: async (params = {}) => {
    try {
      const response = await api.get('/settings/history', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching settings history:', error)
      throw error
    }
  },

  // ========== LEGACY ALIASES (backwards-compat) ==========

  /**
   * Legacy: getSettings() → fetches both security + sales
   */
  getSettings: async () => {
    try {
      const [secRes, salesRes] = await Promise.all([
        api.get('/settings/security'),
        api.get('/settings/sales')
      ])
      const sec = secRes.data?.data || secRes.data
      const sales = salesRes.data?.data || salesRes.data
      return {
        success: true,
        data: {
          posSecurity: {
            maxFailedAttempts: sec.max_failed_attempts,
            lockDurationMinutes: sec.lock_duration_minutes
          },
          freshProductPromotion: {
            autoPromotionEnabled: sales.auto_promotion_enabled || false,
            promotionStartTime: sales.promotion_start_time || '18:00',
            discountPercentage: parseFloat(sales.promotion_discount_percentage) || 20,
            applyToExpiringToday: true,
            applyToExpiringTomorrow: false
          },
          customerDiscounts: {
            retail: parseFloat(sales.discount_retail) || 0,
            wholesale: parseFloat(sales.discount_wholesale) || 5,
            vip: parseFloat(sales.discount_vip) || 10
          }
        }
      }
    } catch (error) {
      console.error('Error fetching settings:', error)
      throw error
    }
  },

  /**
   * Legacy: updateSettings({ freshProductPromotion }) → PUT /settings/sales
   */
  updateSettings: async (settings) => {
    try {
      if (settings.freshProductPromotion) {
        const fp = settings.freshProductPromotion
        const response = await api.put('/settings/sales', {
          auto_promotion_enabled: fp.autoPromotionEnabled,
          promotion_start_time: fp.promotionStartTime,
          promotion_discount_percentage: fp.discountPercentage,
          change_reason: 'Fresh product promotion update'
        })
        return { success: true, data: response.data?.data || response.data }
      }
      return { success: false, error: 'No valid settings provided' }
    } catch (error) {
      console.error('Error updating settings:', error)
      throw error
    }
  },

  // ========== FRESH PRODUCT PROMOTION (Phase 2 — cross-service) ==========

  /**
   * Trigger promotion run — publishes event to Inventory via Settings
   * @returns {Promise<Object>} { requestId, status: 'pending' }
   */
  runPromotionNow: async () => {
    try {
      const response = await api.post('/settings/fresh-promotion/run')
      return response.data
    } catch (error) {
      console.error('Error triggering promotion:', error)
      throw error
    }
  },

  /**
   * Poll promotion status by requestId
   * @param {string} requestId
   * @returns {Promise<Object>} { requestId, status, result? }
   */
  pollPromotionStatus: async (requestId) => {
    try {
      const response = await api.get(`/settings/fresh-promotion/status/${requestId}`)
      return response.data
    } catch (error) {
      console.error('Error polling promotion status:', error)
      throw error
    }
  },

  /**
   * Helper: Run promotion and poll until complete
   * @param {Function} onProgress - callback with status updates
   * @param {number} intervalMs - poll interval (default 2000ms)
   * @param {number} timeoutMs - max wait time (default 30000ms)
   * @returns {Promise<Object>} final result
   */
  runPromotionAndWait: async (onProgress, intervalMs = 2000, timeoutMs = 30000) => {
    const triggerRes = await settingsService.runPromotionNow()
    const data = triggerRes?.data || triggerRes
    const requestId = data.requestId

    if (!requestId) throw new Error('No requestId returned from promotion trigger')

    if (onProgress) onProgress({ status: 'pending', requestId })

    return new Promise((resolve, reject) => {
      const startTime = Date.now()
      const poll = setInterval(async () => {
        try {
          const statusRes = await settingsService.pollPromotionStatus(requestId)
          const statusData = statusRes?.data || statusRes

          if (onProgress) onProgress(statusData)

          if (statusData.status === 'completed') {
            clearInterval(poll)
            resolve(statusData)
          } else if (statusData.status === 'not_found') {
            clearInterval(poll)
            reject(new Error('Promotion request not found'))
          } else if (Date.now() - startTime > timeoutMs) {
            clearInterval(poll)
            reject(new Error('Promotion timed out'))
          }
        } catch (err) {
          clearInterval(poll)
          reject(err)
        }
      }, intervalMs)
    })
  },

  getPromotionStats: async () => {
    return { success: false, error: 'Stats available via promotion run result' }
  },

  getSchedulerStatus: async () => {
    return { success: false, error: 'Scheduler runs in Inventory service' }
  },

  restartPromotionScheduler: async () => {
    return { success: true, message: 'Scheduler auto-restarts on settings change' }
  },
  // ========== OMNICHANNEL COUPONS AND USAGES ==========

  /**
   * Get available public coupons for customer checkout drawer
   */
  getAvailableCoupons: async () => {
    try {
      const response = await api.get('/coupons/available')
      return response.data
    } catch (error) {
      console.error('Error fetching available coupons:', error)
      throw error
    }
  },

  /**
   * Validate coupon before applying it at checkout
   */
  validateCoupon: async (code, subtotal) => {
    try {
      const response = await api.post('/coupons/validate', { code, subtotal })
      return response.data
    } catch (error) {
      console.error('Error validating coupon:', error)
      throw error
    }
  },

  /**
   * Admin: List coupons with pagination and filter
   */
  getCoupons: async (params = {}) => {
    try {
      const response = await api.get('/settings/coupons', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching coupons:', error)
      throw error
    }
  },

  /**
   * Admin: Create a new omnichannel coupon
   */
  createCoupon: async (data) => {
    try {
      const response = await api.post('/settings/coupons', data)
      return response.data
    } catch (error) {
      console.error('Error creating coupon:', error)
      throw error
    }
  },

  /**
   * Admin: Update coupon details
   */
  updateCoupon: async (id, data) => {
    try {
      const response = await api.put(`/settings/coupons/${id}`, data)
      return response.data
    } catch (error) {
      console.error('Error updating coupon:', error)
      throw error
    }
  },

  /**
   * Admin: Soft-delete/deactivate coupon
   */
  deleteCoupon: async (id) => {
    try {
      const response = await api.delete(`/settings/coupons/${id}`)
      return response.data
    } catch (error) {
      console.error('Error deleting coupon:', error)
      throw error
    }
  },

  /**
   * Admin: Get usage logs of a specific coupon
   */
  getCouponUsages: async (id, params = {}) => {
    try {
      const response = await api.get(`/settings/coupons/${id}/usages`, { params })
      return response.data
    } catch (error) {
      console.error('Error fetching coupon usages:', error)
      throw error
    }
  }
}

export default settingsService