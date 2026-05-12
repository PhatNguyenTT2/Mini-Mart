import api from './api'

/**
 * Category Service
 * Read-only API calls for customer category browsing (Catalog microservice)
 */
const categoryService = {
  /**
   * Get all categories (flat list, with optional filters)
   * @param {Object} params - Query parameters
   * @returns {Promise<Object>} Response with categories array
   */
  getAllCategories: async (params = {}) => {
    try {
      const response = await api.get('/categories', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching categories:', error)
      throw error
    }
  },

  /**
   * Get category tree (nested: roots with children[])
   * @returns {Promise<Object>} Response with nested categories
   */
  getCategoryTree: async () => {
    try {
      const response = await api.get('/categories/tree')
      return response.data
    } catch (error) {
      console.error('Error fetching category tree:', error)
      throw error
    }
  },

  /**
   * Get category by ID
   * @param {string} categoryId - Category ID
   * @returns {Promise<Object>} Category data
   */
  getCategoryById: async (categoryId) => {
    try {
      const response = await api.get(`/categories/${categoryId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching category:', error)
      throw error
    }
  }
}

export default categoryService
