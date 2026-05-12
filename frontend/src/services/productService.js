import api from './api'

/**
 * Product Service
 * Handles all API calls related to products (Catalog microservice)
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
   * Get product by ID
   * @param {string} productId - Product ID
   * @returns {Promise<Object>} Product data with category
   */
  getProductById: async (productId) => {
    try {
      const response = await api.get(`/products/${productId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching product:', error)
      throw error
    }
  },

  /**
   * Create new product
   * @param {Object} productData - Product data
   * @param {string} productData.name - Product name (required)
   * @param {string} productData.image - Product image URL (optional)
   * @param {number} productData.categoryId - Category ID (required)
   * @param {number} productData.unitPrice - Unit price (required)
   * @param {boolean} productData.isActive - Active status (optional, default true)
   * @param {string} productData.vendor - Vendor name (optional)
   * @returns {Promise<Object>} Created product data
   */
  createProduct: async (productData) => {
    try {
      const response = await api.post('/products', productData)
      return response.data
    } catch (error) {
      console.error('Error creating product:', error)
      throw error
    }
  },

  /**
   * Update product
   * @param {string} productId - Product ID
   * @param {Object} productData - Updated product data
   * @returns {Promise<Object>} Updated product data
   */
  updateProduct: async (productId, productData) => {
    try {
      const response = await api.put(`/products/${productId}`, productData)
      return response.data
    } catch (error) {
      console.error('Error updating product:', error)
      throw error
    }
  },

  /**
   * Delete product
   * @param {string} productId - Product ID
   * @returns {Promise<Object>} Success message
   */
  deleteProduct: async (productId) => {
    try {
      const response = await api.delete(`/products/${productId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting product:', error)
      throw error
    }
  },

  /**
   * Search products by name or vendor
   * @param {string} searchTerm - Search term
   * @param {number} limit - Maximum results (optional)
   * @returns {Promise<Object>} Matching products
   */
  searchProducts: async (searchTerm, limit = 20) => {
    try {
      const response = await api.get('/products', {
        params: { search: searchTerm, limit }
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
        params: { categoryId, ...options }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching products by category:', error)
      throw error
    }
  },

  /**
   * Get active products only
   * @param {Object} params - Additional query parameters (optional)
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
   * Toggle product active status
   * @param {string} productId - Product ID
   * @param {boolean} isActive - New active status
   * @returns {Promise<Object>} Updated product data
   */
  toggleProductActive: async (productId, isActive) => {
    try {
      const response = await api.put(`/products/${productId}/status`, { isActive })
      return response.data
    } catch (error) {
      console.error('Error toggling product active status:', error)
      throw error
    }
  },

  /**
   * Get product price history
   * @param {string} productId - Product ID
   * @returns {Promise<Object>} Price history array
   */
  getProductPriceHistory: async (productId) => {
    try {
      const response = await api.get(`/products/${productId}/price-history`)
      return response.data
    } catch (error) {
      console.error('Error fetching price history:', error)
      throw error
    }
  },

  /**
   * Update product price (with history tracking)
   * @param {string} productId - Product ID
   * @param {Object} data - { newPrice, reason }
   * @returns {Promise<Object>} Updated product and history entry
   */
  updateProductPrice: async (productId, data) => {
    try {
      const response = await api.post(`/products/${productId}/price-change`, data)
      return response.data
    } catch (error) {
      console.error('Error updating product price:', error)
      throw error
    }
  }
}

export default productService
