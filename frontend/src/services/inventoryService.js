import api from './api'

/**
 * Inventory Service
 * Handles API calls to inventory backend service
 * Backend: /api/inventory → inventory_service:3006
 */
const inventoryService = {
  /**
   * Get product-level inventory summary (with product info from catalog)
   * Backend returns: { success: true, data: [{productId, product: {name, productCode}, quantityOnHand, ...}] }
   */
  getAllInventories: async (params = {}) => {
    try {
      const response = await api.get('/inventory/summary', { params })
      // Backend returns { success: true, data: [...] }
      if (response.data?.success && Array.isArray(response.data?.data)) {
        return {
          success: true,
          data: { inventories: response.data.data }
        }
      }
      return response.data
    } catch (error) {
      console.error('Error fetching inventories:', error)
      throw error
    }
  },

  /**
   * Get movement history for a product
   */
  getMovementHistory: async (productId, limit = 50) => {
    try {
      const response = await api.get(`/inventory/movements/${productId}`, {
        params: { limit }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching movement history:', error)
      throw error
    }
  },

  /**
   * Get batches for a product
   */
  getBatchesByProduct: async (productId) => {
    try {
      const response = await api.get(`/inventory/batches/${productId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching batches:', error)
      throw error
    }
  },

  /**
   * Receive stock — POST /inventory/receive
   */
  receiveStock: async (batchId, locationId, quantity, reason) => {
    try {
      const response = await api.post('/inventory/receive', {
        batchId, locationId, quantity, reason
      })
      return response.data
    } catch (error) {
      console.error('Error receiving stock:', error)
      throw error
    }
  },

  /**
   * Transfer stock to shelf — POST /inventory/move-to-shelf
   */
  transferToShelf: async (batchId, locationId, moveQty) => {
    try {
      const response = await api.post('/inventory/move-to-shelf', {
        batchId, locationId, moveQty
      })
      return response.data
    } catch (error) {
      console.error('Error transferring to shelf:', error)
      throw error
    }
  },

  /**
   * Update reorder point for a product
   */
  updateReorderPoint: async (productId, reorderPoint) => {
    try {
      const response = await api.put('/inventory/reorder-point', {
        productId, reorderPoint
      })
      return response.data
    } catch (error) {
      console.error('Error updating reorder point:', error)
      throw error
    }
  },

  /**
   * Get inventory summary filtered by product
   */
  getInventoryByProduct: async (productId) => {
    try {
      const response = await api.get('/inventory/summary', {
        params: { productId }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching inventory by product:', error)
      throw error
    }
  },

  /**
   * Get inventory summary (raw format: { success, data: [{productId, product, quantityOnHand, ...}] })
   * Used by StockOut components to get products with available stock
   */
  getInventorySummary: async () => {
    try {
      const response = await api.get('/inventory/summary')
      return response.data
    } catch (error) {
      console.error('Error fetching inventory summary:', error)
      throw error
    }
  }
}

export default inventoryService
