import api from './api'

/**
 * Store Service
 * Fetches store list from Auth microservice (no auth required)
 */
const storeService = {
  /**
   * Get all active stores
   * @returns {Promise<Object>} Response with stores array
   */
  getStores: async () => {
    try {
      const response = await api.get('/stores')
      return response.data
    } catch (error) {
      console.error('Error fetching stores:', error)
      throw error
    }
  },

  /**
   * Get store by ID
   * @param {string|number} storeId - Store ID
   * @returns {Promise<Object>} Store data
   */
  getStoreById: async (storeId) => {
    try {
      const response = await api.get(`/stores/${storeId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching store:', error)
      throw error
    }
  }
}

export default storeService
