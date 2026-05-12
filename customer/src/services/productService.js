import api from './api'

/**
 * Product Service
 * Read-only API calls for customer product browsing (Catalog microservice)
 */
const productService = {
  /**
   * Get all products with optional filters
   * @param {Object} params - Query parameters
   * @param {boolean} params.isActive - Filter by active status
   * @param {string} params.categoryId - Filter by category ID
   * @param {string} params.search - Search by product name or vendor
   * @returns {Promise<Object>} Response with products array
   */
  getAllProducts: async (params = {}) => {
    try {
      const response = await api.get('/products', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching products:', error)
      throw error
    }
  },

  /**
   * Get active products only
   * @param {Object} params - Additional query parameters
   * @returns {Promise<Object>} Active products
   */
  getActiveProducts: async (params = {}) => {
    try {
      const response = await api.get('/products', {
        params: { isActive: true, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching active products:', error)
      throw error
    }
  },

  /**
   * Search products by name or vendor
   * @param {string} searchTerm - Search term
   * @param {number} limit - Maximum results
   * @returns {Promise<Object>} Matching products
   */
  searchProducts: async (searchTerm, limit = 20) => {
    try {
      const response = await api.get('/products', {
        params: { search: searchTerm, limit, isActive: true }
      })
      return response.data
    } catch (error) {
      console.error('Error searching products:', error)
      throw error
    }
  },

  /**
   * Get products by category
   * @param {string} categoryId - Category ID
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} Products in the category
   */
  getProductsByCategory: async (categoryId, options = {}) => {
    try {
      const response = await api.get('/products', {
        params: { categoryId, isActive: true, ...options }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching products by category:', error)
      throw error
    }
  },

  /**
   * Get product detail by ID — Catalog service
   * @param {number|string} productId
   * @returns {Promise<Object>} Product detail
   */
  getProductById: async (productId) => {
    try {
      const response = await api.get(`/products/${productId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching product detail:', error)
      throw error
    }
  },

  /**
   * Get FEFO batches for a product at a store — Inventory service (public)
   * Returns batches sorted by expiry_date ASC (First Expired, First Out)
   * @param {number} storeId
   * @param {number} productId
   * @returns {Promise<Object>} { batches[], totalOnShelf }
   */
  getProductBatches: async (storeId, productId) => {
    try {
      const response = await api.get(`/inventory/public/batches/${storeId}/${productId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching product batches:', error)
      throw error
    }
  },

  /**
   * Get public inventory summary for a store
   * @param {number} storeId 
   * @returns {Promise<Object>}
   */
  getStoreInventorySummary: async (storeId) => {
    try {
      const response = await api.get(`/inventory/public/summary/${storeId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching inventory summary:', error)
      throw error
    }
  }
}

export default productService
