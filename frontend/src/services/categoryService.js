import api from './api'

/**
 * Category Service
 * Handles all API calls related to categories (Catalog microservice)
 */
const categoryService = {
  /**
   * Get all categories (flat list, with optional filters)
   * @param {Object} params - Query parameters
   * @param {string} params.search - Search by category name
   * @param {string} params.parentId - Filter by parent ID (null = root only)
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
   * @returns {Promise<Object>} Category data with product count
   */
  getCategoryById: async (categoryId) => {
    try {
      const response = await api.get(`/categories/${categoryId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching category:', error)
      throw error
    }
  },

  /**
   * Get subcategories of a parent
   * @param {string} parentId - Parent category ID
   * @returns {Promise<Object>} Response with subcategories array
   */
  getSubcategories: async (parentId) => {
    try {
      const response = await api.get(`/categories/${parentId}/subcategories`)
      return response.data
    } catch (error) {
      console.error('Error fetching subcategories:', error)
      throw error
    }
  },

  /**
   * Create new category
   * @param {Object} categoryData - Category data
   * @param {string} categoryData.name - Category name (required)
   * @param {number} categoryData.parentId - Parent category ID (optional, null = root)
   * @param {string} categoryData.image - Category image URL (optional)
   * @param {string} categoryData.description - Category description (optional)
   * @param {number} categoryData.sortOrder - Sort order (optional)
   * @returns {Promise<Object>} Created category data
   */
  createCategory: async (categoryData) => {
    try {
      const response = await api.post('/categories', categoryData)
      return response.data
    } catch (error) {
      console.error('Error creating category:', error)
      throw error
    }
  },

  /**
   * Update category
   * @param {string} categoryId - Category ID
   * @param {Object} categoryData - Updated category data
   * @returns {Promise<Object>} Updated category data
   */
  updateCategory: async (categoryId, categoryData) => {
    try {
      const response = await api.put(`/categories/${categoryId}`, categoryData)
      return response.data
    } catch (error) {
      console.error('Error updating category:', error)
      throw error
    }
  },

  /**
   * Delete category
   * @param {string} categoryId - Category ID
   * @returns {Promise<Object>} Success message
   */
  deleteCategory: async (categoryId) => {
    try {
      const response = await api.delete(`/categories/${categoryId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting category:', error)
      throw error
    }
  },

  /**
   * Search categories by name
   * @param {string} searchTerm - Search term
   * @returns {Promise<Object>} Search results
   */
  searchCategories: async (searchTerm) => {
    try {
      const response = await api.get('/categories', {
        params: { search: searchTerm }
      })
      return response.data
    } catch (error) {
      console.error('Error searching categories:', error)
      throw error
    }
  },

  /**
   * Check if category name exists
   * @param {string} name - Category name to check
   * @param {string} excludeId - Category ID to exclude from check (for update)
   * @returns {Promise<boolean>} True if name exists
   */
  checkNameExists: async (name, excludeId = null) => {
    try {
      const response = await api.get('/categories', {
        params: { search: name }
      })

      const categories = response.data?.data?.categories || []

      const exists = categories.some(cat =>
        cat.name.toLowerCase() === name.toLowerCase() &&
        (!excludeId || cat.id !== excludeId)
      )

      return exists
    } catch (error) {
      console.error('Error checking category name:', error)
      throw error
    }
  }
}

export default categoryService
