import api from './api'

/**
 * Detail Inventory Service
 * Handles all API calls related to batch-level inventories
 * Backend: /api/inventory → inventory_service:3006 (PostgreSQL microservice)
 */
const detailInventoryService = {
  /**
   * Get detail inventories by product ID
   * Calls microservice: GET /api/inventory/items/:productId
   */
  getDetailInventoriesByProduct: async (productId, params = {}) => {
    try {
      const response = await api.get(`/inventory/items/${productId}`, { params })
      return response.data
    } catch (error) {
      console.error('Error fetching detail inventories by product:', error)
      throw error
    }
  },

  /**
   * Get movement history for a specific inventory item
   * Calls microservice: GET /api/inventory/items/:itemId/movements
   */
  getMovementsByItem: async (itemId, limit = 50) => {
    try {
      const response = await api.get(`/inventory/items/${itemId}/movements`, {
        params: { limit }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching movements by item:', error)
      throw error
    }
  },

  /**
   * Adjust batch stock via inventory service
   * Calls: POST /api/inventory/receive (for stock in adjustments)
   */
  adjustBatchStock: async (batchId, locationId, quantity, reason = 'manual_adjustment') => {
    try {
      const response = await api.post('/inventory/receive', {
        batchId,
        locationId: locationId || null,
        quantity,
        reason
      })
      return response.data
    } catch (error) {
      console.error('Error adjusting batch stock:', error)
      throw error
    }
  },

  /**
   * Transfer stock to shelf
   * Calls: POST /api/inventory/move-to-shelf
   */
  transferBatchToShelf: async (batchId, locationId, moveQty) => {
    try {
      const response = await api.post('/inventory/move-to-shelf', {
        batchId,
        locationId: locationId || null,
        moveQty
      })
      return response.data
    } catch (error) {
      console.error('Error transferring batch to shelf:', error)
      throw error
    }
  },

  /**
   * Get movement history for a product (all batches)
   * Calls: GET /api/inventory/movements/:productId
   */
  getMovementsByProduct: async (productId, limit = 50) => {
    try {
      const response = await api.get(`/inventory/movements/${productId}`, {
        params: { limit }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching movements by product:', error)
      throw error
    }
  },

  /**
   * Get batches for a product
   * Calls: GET /api/inventory/batches/:productId
   */
  getBatchesByProduct: async (productId) => {
    try {
      const response = await api.get(`/inventory/batches/${productId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching batches:', error)
      throw error
    }
  }
}

export default detailInventoryService
