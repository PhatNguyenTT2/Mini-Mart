import api from './api'

/**
 * Detail Purchase Order Service
 * Handles all API calls related to purchase order line items
 */
const detailPurchaseOrderService = {
  /**
   * Get all detail purchase orders with optional filters
   * @param {Object} params - Query parameters
   * @param {string} params.purchaseOrder - Filter by purchase order ID
   * @param {string} params.product - Filter by product ID
   * @param {string} params.batch - Filter by batch ID
   * @param {number} params.minQuantity - Filter by minimum quantity
   * @param {number} params.maxQuantity - Filter by maximum quantity
   * @param {number} params.minPrice - Filter by minimum unit price
   * @param {number} params.maxPrice - Filter by maximum unit price
   * @param {number} params.minTotal - Filter by minimum total
   * @param {number} params.maxTotal - Filter by maximum total
   * @param {boolean} params.withPurchaseOrder - Include purchase order details
   * @param {boolean} params.withProduct - Include product details
   * @param {boolean} params.withBatch - Include batch details
   * @param {number} params.page - Page number for pagination
   * @param {number} params.limit - Items per page
   * @returns {Promise<Object>} Response with detailPurchaseOrders array and pagination
   */
  getAllDetailPurchaseOrders: async (params = {}) => {
    try {
      const response = await api.get('/detail-purchase-orders', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching detail purchase orders:', error)
      throw error
    }
  },

  /**
   * Get detail purchase order by ID
   * @param {string} detailPurchaseOrderId - Detail purchase order ID
   * @returns {Promise<Object>} Detail purchase order data with purchase order, product, and batch info
   */
  getDetailPurchaseOrderById: async (detailPurchaseOrderId) => {
    try {
      const response = await api.get(`/detail-purchase-orders/${detailPurchaseOrderId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching detail purchase order:', error)
      throw error
    }
  },

  /**
   * Create new detail purchase order (add item to purchase order)
   * @param {Object} detailData - Detail purchase order data
   * @param {string} detailData.purchaseOrder - Purchase order ID (required)
   * @param {string} detailData.product - Product ID (required)
   * @param {string} detailData.batch - Batch ID (required)
   * @param {number} detailData.quantity - Quantity (required, min: 1)
   * @param {number} detailData.unitPrice - Unit price (required, min: 0)
   * @returns {Promise<Object>} Created detail purchase order data
   * @note Batch must belong to the specified product
   * @note Cannot add to received or cancelled purchase orders
   * @note Total is auto-calculated from quantity * unitPrice
   */
  createDetailPurchaseOrder: async (detailData) => {
    try {
      const response = await api.post('/detail-purchase-orders', detailData)
      return response.data
    } catch (error) {
      console.error('Error creating detail purchase order:', error)
      throw error
    }
  },

  /**
   * Update detail purchase order
   * @param {string} detailPurchaseOrderId - Detail purchase order ID
   * @param {Object} detailData - Updated detail purchase order data
   * @param {number} detailData.quantity - Quantity (optional, min: 1)
   * @param {number} detailData.unitPrice - Unit price (optional, min: 0)
   * @returns {Promise<Object>} Updated detail purchase order data
   * @note Cannot update if purchase order is received or cancelled
   * @note Total is auto-recalculated
   */
  updateDetailPurchaseOrder: async (detailPurchaseOrderId, detailData) => {
    try {
      const response = await api.put(`/detail-purchase-orders/${detailPurchaseOrderId}`, detailData)
      return response.data
    } catch (error) {
      console.error('Error updating detail purchase order:', error)
      throw error
    }
  },

  /**
   * Delete detail purchase order (remove item from purchase order)
   * @param {string} detailPurchaseOrderId - Detail purchase order ID
   * @returns {Promise<Object>} Success message
   * @note Cannot delete from received or cancelled purchase orders
   */
  deleteDetailPurchaseOrder: async (detailPurchaseOrderId) => {
    try {
      const response = await api.delete(`/detail-purchase-orders/${detailPurchaseOrderId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting detail purchase order:', error)
      throw error
    }
  },

  /**
   * Get detail purchase orders by purchase order ID
   * @param {string} purchaseOrderId - Purchase order ID
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Detail purchase orders for the specified purchase order
   */
  getDetailsByPurchaseOrder: async (purchaseOrderId, params = {}) => {
    try {
      const response = await api.get('/detail-purchase-orders', {
        params: {
          purchaseOrder: purchaseOrderId,
          withProduct: true,
          withBatch: true,
          ...params
        }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching details by purchase order:', error)
      throw error
    }
  },

  /**
   * Get detail purchase orders by product ID
   * @param {string} productId - Product ID
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Detail purchase orders for the specified product
   */
  getDetailsByProduct: async (productId, params = {}) => {
    try {
      const response = await api.get('/detail-purchase-orders', {
        params: {
          product: productId,
          withPurchaseOrder: true,
          withBatch: true,
          ...params
        }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching details by product:', error)
      throw error
    }
  },

  /**
   * Get detail purchase orders by batch ID
   * @param {string} batchId - Batch ID
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Detail purchase orders for the specified batch
   */
  getDetailsByBatch: async (batchId, params = {}) => {
    try {
      const response = await api.get('/detail-purchase-orders', {
        params: {
          batch: batchId,
          withPurchaseOrder: true,
          withProduct: true,
          ...params
        }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching details by batch:', error)
      throw error
    }
  },

  /**
   * Get detail purchase orders with full details (PO, Product, Batch)
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Detail purchase orders with all relationships populated
   */
  getDetailsWithFullInfo: async (params = {}) => {
    try {
      const response = await api.get('/detail-purchase-orders', {
        params: {
          withPurchaseOrder: true,
          withProduct: true,
          withBatch: true,
          ...params
        }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching details with full info:', error)
      throw error
    }
  },

  /**
   * Update detail quantity
   * @param {string} detailPurchaseOrderId - Detail purchase order ID
   * @param {number} quantity - New quantity (min: 1)
   * @returns {Promise<Object>} Updated detail purchase order data
   */
  updateQuantity: async (detailPurchaseOrderId, quantity) => {
    try {
      const response = await api.put(`/detail-purchase-orders/${detailPurchaseOrderId}`, { quantity })
      return response.data
    } catch (error) {
      console.error('Error updating quantity:', error)
      throw error
    }
  },

  /**
   * Update detail unit price
   * @param {string} detailPurchaseOrderId - Detail purchase order ID
   * @param {number} unitPrice - New unit price (min: 0)
   * @returns {Promise<Object>} Updated detail purchase order data
   */
  updateUnitPrice: async (detailPurchaseOrderId, unitPrice) => {
    try {
      const response = await api.put(`/detail-purchase-orders/${detailPurchaseOrderId}`, { unitPrice })
      return response.data
    } catch (error) {
      console.error('Error updating unit price:', error)
      throw error
    }
  },

  /**
   * Update both quantity and unit price
   * @param {string} detailPurchaseOrderId - Detail purchase order ID
   * @param {number} quantity - New quantity (min: 1)
   * @param {number} unitPrice - New unit price (min: 0)
   * @returns {Promise<Object>} Updated detail purchase order data
   */
  updateQuantityAndPrice: async (detailPurchaseOrderId, quantity, unitPrice) => {
    try {
      const response = await api.put(`/detail-purchase-orders/${detailPurchaseOrderId}`, {
        quantity,
        unitPrice
      })
      return response.data
    } catch (error) {
      console.error('Error updating quantity and price:', error)
      throw error
    }
  },

  /**
   * Add multiple items to purchase order
   * @param {string} purchaseOrderId - Purchase order ID
   * @param {Array} items - Array of items to add
   * @param {string} items[].product - Product ID
   * @param {string} items[].batch - Batch ID
   * @param {number} items[].quantity - Quantity
   * @param {number} items[].unitPrice - Unit price
   * @returns {Promise<Object>} Results of all create operations
   */
  addMultipleItems: async (purchaseOrderId, items) => {
    try {
      const promises = items.map(item =>
        api.post('/detail-purchase-orders', {
          purchaseOrder: purchaseOrderId,
          ...item
        })
      )
      const results = await Promise.allSettled(promises)

      const succeeded = results.filter(r => r.status === 'fulfilled').map(r => r.value.data)
      const failed = results.filter(r => r.status === 'rejected').map(r => r.reason)

      return {
        success: true,
        data: {
          succeeded,
          failed,
          total: items.length,
          successCount: succeeded.length,
          failCount: failed.length
        }
      }
    } catch (error) {
      console.error('Error adding multiple items:', error)
      throw error
    }
  },

  /**
   * Delete multiple detail purchase orders
   * @param {Array<string>} detailIds - Array of detail purchase order IDs
   * @returns {Promise<Object>} Results of all delete operations
   */
  deleteMultipleDetails: async (detailIds) => {
    try {
      const promises = detailIds.map(id =>
        api.delete(`/detail-purchase-orders/${id}`)
      )
      const results = await Promise.allSettled(promises)

      const succeeded = results.filter(r => r.status === 'fulfilled').map(r => r.value.data)
      const failed = results.filter(r => r.status === 'rejected').map(r => r.reason)

      return {
        success: true,
        data: {
          succeeded,
          failed,
          total: detailIds.length,
          successCount: succeeded.length,
          failCount: failed.length
        }
      }
    } catch (error) {
      console.error('Error deleting multiple details:', error)
      throw error
    }
  },

  /**
   * Get detail purchase orders with pagination
   * @param {number} page - Page number
   * @param {number} limit - Items per page
   * @param {Object} filters - Additional filters (optional)
   * @returns {Promise<Object>} Paginated detail purchase orders
   */
  getDetailsPaginated: async (page = 1, limit = 20, filters = {}) => {
    try {
      const response = await api.get('/detail-purchase-orders', {
        params: {
          page,
          limit,
          withPurchaseOrder: true,
          withProduct: true,
          withBatch: true,
          ...filters
        }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching paginated details:', error)
      throw error
    }
  },

  /**
   * Calculate total for purchase order details
   * @param {Array} details - Array of detail objects with quantity and unitPrice
   * @returns {number} Total amount
   */
  calculateTotal: (details) => {
    if (!Array.isArray(details)) return 0

    return details.reduce((sum, detail) => {
      const quantity = detail.quantity || 0
      const unitPrice = detail.unitPrice || 0
      return sum + (quantity * unitPrice)
    }, 0)
  },

  /**
   * Calculate subtotal, discount, shipping, and total for purchase order
   * @param {Array} details - Array of detail objects
   * @param {number} discountPercentage - Discount percentage (0-100)
   * @param {number} shippingFee - Shipping fee
   * @returns {Object} Calculation breakdown
   */
  calculatePurchaseOrderTotal: (details, discountPercentage = 0, shippingFee = 0) => {
    const subtotal = detailPurchaseOrderService.calculateTotal(details)
    const discountAmount = subtotal * (discountPercentage / 100)
    const total = subtotal - discountAmount + shippingFee

    return {
      subtotal: parseFloat(subtotal.toFixed(2)),
      discountPercentage: parseFloat(discountPercentage.toFixed(2)),
      discountAmount: parseFloat(discountAmount.toFixed(2)),
      shippingFee: parseFloat(shippingFee.toFixed(2)),
      total: parseFloat(total.toFixed(2))
    }
  },

  /**
   * Validate detail purchase order data before submission
   * @param {Object} detailData - Detail data to validate
   * @returns {Object} Validation result with isValid and errors
   */
  validateDetailData: (detailData) => {
    const errors = []

    if (!detailData.purchaseOrder) {
      errors.push('Purchase order is required')
    }

    if (!detailData.product) {
      errors.push('Product is required')
    }

    if (!detailData.batch) {
      errors.push('Batch is required')
    }

    if (!detailData.quantity || detailData.quantity < 1) {
      errors.push('Quantity must be at least 1')
    }

    if (detailData.unitPrice === undefined || detailData.unitPrice < 0) {
      errors.push('Unit price must be 0 or greater')
    }

    return {
      isValid: errors.length === 0,
      errors
    }
  },

  /**
   * Check if detail can be edited (purchase order not received/cancelled)
   * @param {Object} purchaseOrder - Purchase order object
   * @returns {boolean} True if editable
   */
  canEditDetail: (purchaseOrder) => {
    if (!purchaseOrder) return false
    return purchaseOrder.status !== 'received' && purchaseOrder.status !== 'cancelled'
  },

  /**
   * Group details by product
   * @param {Array} details - Array of detail purchase orders
   * @returns {Object} Details grouped by product ID
   */
  groupByProduct: (details) => {
    if (!Array.isArray(details)) return {}

    return details.reduce((groups, detail) => {
      const productId = detail.product?.id || detail.product
      if (!groups[productId]) {
        groups[productId] = []
      }
      groups[productId].push(detail)
      return groups
    }, {})
  },

  /**
   * Group details by batch
   * @param {Array} details - Array of detail purchase orders
   * @returns {Object} Details grouped by batch ID
   */
  groupByBatch: (details) => {
    if (!Array.isArray(details)) return {}

    return details.reduce((groups, detail) => {
      const batchId = detail.batch?.id || detail.batch
      if (!groups[batchId]) {
        groups[batchId] = []
      }
      groups[batchId].push(detail)
      return groups
    }, {})
  },

  /**
   * Get summary statistics for detail purchase orders
   * @param {Array} details - Array of detail purchase orders
   * @returns {Object} Summary statistics
   */
  getSummary: (details) => {
    if (!Array.isArray(details) || details.length === 0) {
      return {
        totalItems: 0,
        uniqueProducts: 0,
        totalQuantity: 0,
        totalAmount: 0,
        averageUnitPrice: 0
      }
    }

    const uniqueProducts = new Set(details.map(d => d.product?.id || d.product)).size
    const totalQuantity = details.reduce((sum, d) => sum + (d.quantity || 0), 0)
    const totalAmount = detailPurchaseOrderService.calculateTotal(details)
    const averageUnitPrice = totalAmount / totalQuantity

    return {
      totalItems: details.length,
      uniqueProducts,
      totalQuantity,
      totalAmount: parseFloat(totalAmount.toFixed(2)),
      averageUnitPrice: parseFloat((averageUnitPrice || 0).toFixed(2))
    }
  }
}

export default detailPurchaseOrderService
