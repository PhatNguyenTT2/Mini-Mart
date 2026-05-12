import api from './api'

/**
 * Inventory Movement Batch Service
 * Handles all API calls related to batch-level inventory movements
 * Backend: /api/inventory → inventory_service:3006 (PostgreSQL microservice)
 */
const inventoryMovementBatchService = {
  /**
   * Get movements for a specific inventory item
   * Calls: GET /api/inventory/items/:itemId/movements
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
   * Adjust stock (increase/decrease)
   * Calls: POST /api/inventory/adjust
   */
  adjustStock: async ({ batchId, locationId, quantity, targetLocation, reason }) => {
    try {
      const response = await api.post('/inventory/adjust', {
        batchId,
        locationId: locationId || null,
        quantity,
        targetLocation: targetLocation || 'onHand',
        reason: reason || 'manual_adjustment'
      })
      return response.data
    } catch (error) {
      console.error('Error adjusting stock:', error)
      throw error
    }
  },

  /**
   * Transfer stock to shelf
   * Calls: POST /api/inventory/move-to-shelf
   */
  moveToShelf: async (batchId, locationId, moveQty) => {
    try {
      const response = await api.post('/inventory/move-to-shelf', {
        batchId,
        locationId: locationId || null,
        moveQty
      })
      return response.data
    } catch (error) {
      console.error('Error moving stock to shelf:', error)
      throw error
    }
  },

  /**
   * Receive stock (for manual stock in)
   * Calls: POST /api/inventory/receive
   */
  receiveStock: async (batchId, locationId, quantity, reason = 'manual_receive') => {
    try {
      const response = await api.post('/inventory/receive', {
        batchId,
        locationId: locationId || null,
        quantity,
        reason
      })
      return response.data
    } catch (error) {
      console.error('Error receiving stock:', error)
      throw error
    }
  }
}

export default inventoryMovementBatchService