import api from './api'

/**
 * Product Batch Service
 * Handles all API calls related to product batches
 */
const productBatchService = {
  /**
   * Get all product batches with optional filters
   * @param {Object} params - Query parameters
   * @param {string} params.product - Filter by product ID
   * @param {string} params.status - Filter by status (active/expired)
   * @param {boolean} params.nearExpiry - Filter batches expiring within 30 days
   * @param {boolean} params.expired - Filter expired batches
   * @param {string} params.search - Search by batch code
   * @param {number} params.minQuantity - Filter by minimum quantity
   * @param {number} params.maxQuantity - Filter by maximum quantity
   * @param {string} params.promotionApplied - Filter by promotion type (none/discount/flash-sale)
   * @param {number} params.page - Page number for pagination
   * @param {number} params.limit - Items per page
   * @returns {Promise<Object>} Response with batches array and pagination
   */
  getAllBatches: async (params = {}) => {
    try {
      const response = await api.get('/product-batches', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching product batches:', error)
      throw error
    }
  },

  /**
   * Get product batch by ID
   * @param {string} batchId - Batch ID
   * @returns {Promise<Object>} Batch data with product and detail inventory
   */
  getBatchById: async (batchId) => {
    try {
      const response = await api.get(`/product-batches/${batchId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching product batch:', error)
      throw error
    }
  },

  /**
   * Create new product batch
   * @param {Object} batchData - Batch data
   * @param {string} batchData.product - Product ID (required)
   * @param {number} batchData.costPrice - Cost price (required)
   * @param {number} batchData.unitPrice - Unit price (required)
   * @param {number} batchData.quantity - Quantity (required)
   * @param {string} batchData.promotionApplied - Promotion type (optional: none/discount/flash-sale)
   * @param {number} batchData.discountPercentage - Discount percentage (optional)
   * @param {Date} batchData.mfgDate - Manufacturing date (optional)
   * @param {Date} batchData.expiryDate - Expiry date (optional)
   * @param {string} batchData.status - Status (optional: active/expired)
   * @param {string} batchData.notes - Notes (optional)
   * @returns {Promise<Object>} Created batch data
   */
  createBatch: async (batchData) => {
    try {
      const response = await api.post('/product-batches', batchData)
      return response.data
    } catch (error) {
      console.error('Error creating product batch:', error)
      throw error
    }
  },

  /**
   * Update product batch
   * @param {string} batchId - Batch ID
   * @param {Object} batchData - Updated batch data
   * @param {number} batchData.costPrice - Cost price (optional)
   * @param {number} batchData.unitPrice - Unit price (optional)
   * @param {number} batchData.quantity - Quantity (optional)
   * @param {string} batchData.promotionApplied - Promotion type (optional)
   * @param {number} batchData.discountPercentage - Discount percentage (optional)
   * @param {Date} batchData.mfgDate - Manufacturing date (optional)
   * @param {Date} batchData.expiryDate - Expiry date (optional)
   * @param {string} batchData.status - Status (optional)
   * @param {string} batchData.notes - Notes (optional)
   * @returns {Promise<Object>} Updated batch data
   */
  updateBatch: async (batchId, batchData) => {
    try {
      const response = await api.put(`/product-batches/${batchId}`, batchData)
      return response.data
    } catch (error) {
      console.error('Error updating product batch:', error)
      throw error
    }
  },

  /**
   * Delete product batch
   * @param {string} batchId - Batch ID
   * @returns {Promise<Object>} Success message
   * @note Cannot delete batch if it has inventory or remaining quantity
   */
  deleteBatch: async (batchId) => {
    try {
      const response = await api.delete(`/product-batches/${batchId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting product batch:', error)
      throw error
    }
  },

  /**
   * Get batches by product ID
   * @param {string} productId - Product ID
   * @param {Object} options - Additional options
   * @param {string} options.status - Filter by status (optional)
   * @param {number} options.page - Page number (optional)
   * @param {number} options.limit - Items per page (optional)
   * @returns {Promise<Object>} Batches for the product
   */
  getBatchesByProduct: async (productId, options = {}) => {
    try {
      const response = await api.get('/product-batches', {
        params: { product: productId, ...options }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching batches by product:', error)
      throw error
    }
  },

  /**
   * Get expired batches
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Expired batches
   */
  getExpiredBatches: async (params = {}) => {
    try {
      const response = await api.get('/product-batches', {
        params: { expired: true, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching expired batches:', error)
      throw error
    }
  },

  /**
   * Get batches near expiry (within 30 days)
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Batches expiring soon
   */
  getNearExpiryBatches: async (params = {}) => {
    try {
      const response = await api.get('/product-batches', {
        params: { nearExpiry: true, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching near expiry batches:', error)
      throw error
    }
  },

  /**
   * Get active batches only
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Active batches
   */
  getActiveBatches: async (params = {}) => {
    try {
      const response = await api.get('/product-batches', {
        params: { status: 'active', ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching active batches:', error)
      throw error
    }
  },

  /**
   * Get batches with promotion applied
   * @param {string} promotionType - Promotion type (discount/flash-sale)
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Batches with promotion
   */
  getBatchesWithPromotion: async (promotionType, params = {}) => {
    try {
      const response = await api.get('/product-batches', {
        params: { promotionApplied: promotionType, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching batches with promotion:', error)
      throw error
    }
  },

  /**
   * Search batches by batch code
   * @param {string} searchTerm - Search term
   * @param {number} limit - Maximum results (optional, default 20)
   * @returns {Promise<Object>} Matching batches
   */
  searchBatches: async (searchTerm, limit = 20) => {
    try {
      const response = await api.get('/product-batches', {
        params: { search: searchTerm, limit }
      })
      return response.data
    } catch (error) {
      console.error('Error searching batches:', error)
      throw error
    }
  },

  /**
   * Update batch quantity
   * @param {string} batchId - Batch ID
   * @param {number} quantity - New quantity
   * @returns {Promise<Object>} Updated batch data
   */
  updateBatchQuantity: async (batchId, quantity) => {
    try {
      const response = await api.put(`/product-batches/${batchId}`, { quantity })
      return response.data
    } catch (error) {
      console.error('Error updating batch quantity:', error)
      throw error
    }
  },

  /**
   * Update batch status
   * @param {string} batchId - Batch ID
   * @param {string} status - New status (active/expired)
   * @returns {Promise<Object>} Updated batch data
   */
  updateBatchStatus: async (batchId, status) => {
    try {
      const response = await api.put(`/product-batches/${batchId}`, { status })
      return response.data
    } catch (error) {
      console.error('Error updating batch status:', error)
      throw error
    }
  },

  /**
   * Update batch prices
   * @param {string} batchId - Batch ID
   * @param {Object} priceData - Price data
   * @param {number} priceData.costPrice - Cost price (optional)
   * @param {number} priceData.unitPrice - Unit price (optional)
   * @returns {Promise<Object>} Updated batch data
   */
  updateBatchPrices: async (batchId, priceData) => {
    try {
      const response = await api.put(`/product-batches/${batchId}`, priceData)
      return response.data
    } catch (error) {
      console.error('Error updating batch prices:', error)
      throw error
    }
  },

  /**
   * Apply promotion to batch
   * @param {string} batchId - Batch ID
   * @param {string} promotionType - Promotion type (discount/flash-sale/none)
   * @param {number} discountPercentage - Discount percentage (required if promotionType is discount)
   * @returns {Promise<Object>} Updated batch data
   */
  applyPromotion: async (batchId, promotionType, discountPercentage = 0) => {
    try {
      const response = await api.put(`/product-batches/${batchId}`, {
        promotionApplied: promotionType,
        discountPercentage: discountPercentage
      })
      return response.data
    } catch (error) {
      console.error('Error applying promotion to batch:', error)
      throw error
    }
  },

  /**
   * Remove promotion from batch
   * @param {string} batchId - Batch ID
   * @returns {Promise<Object>} Updated batch data
   */
  removePromotion: async (batchId) => {
    try {
      const response = await api.put(`/product-batches/${batchId}`, {
        promotionApplied: 'none',
        discountPercentage: 0
      })
      return response.data
    } catch (error) {
      console.error('Error removing promotion from batch:', error)
      throw error
    }
  },

  /**
   * Get batches with low quantity
   * @param {number} threshold - Quantity threshold (default 10)
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Batches with quantity below threshold
   */
  getLowQuantityBatches: async (threshold = 10, params = {}) => {
    try {
      const response = await api.get('/product-batches', {
        params: { maxQuantity: threshold, status: 'active', ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching low quantity batches:', error)
      throw error
    }
  }
}

export default productBatchService
