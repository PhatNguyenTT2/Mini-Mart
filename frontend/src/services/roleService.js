import api from './api'

/**
 * Role Service
 * Handles all API calls related to roles (via auth microservice)
 */
const roleService = {
  /**
   * Get all roles with optional search
   * @param {Object} params - Query parameters
   * @param {string} params.search - Search by role name or description
   * @returns {Promise<Object>} Response with roles array and count
   */
  getAllRoles: async (params = {}) => {
    try {
      // withEmployees is always included by backend now — strip it
      const { withEmployees, code, ...queryParams } = params
      const response = await api.get('/roles', { params: queryParams })
      return response.data
    } catch (error) {
      console.error('Error fetching roles:', error)
      throw error
    }
  },

  /**
   * Get role by ID
   * @param {number} roleId - Role ID
   * @returns {Promise<Object>} Role data
   */
  getRoleById: async (roleId) => {
    try {
      const response = await api.get(`/roles/${roleId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching role:', error)
      throw error
    }
  },

  /**
   * Create new role
   * @param {Object} roleData - Role data
   * @param {string} roleData.roleName - Role name (required)
   * @param {string} roleData.description - Role description (optional)
   * @param {Array<string>} roleData.permissions - Array of permission codes (optional)
   * @returns {Promise<Object>} Created role data
   */
  createRole: async (roleData) => {
    try {
      const response = await api.post('/roles', roleData)
      return response.data
    } catch (error) {
      console.error('Error creating role:', error)
      throw error
    }
  },

  /**
   * Update role
   * @param {number} roleId - Role ID
   * @param {Object} roleData - Updated role data
   * @param {string} roleData.roleName - Role name (optional)
   * @param {string} roleData.description - Role description (optional)
   * @param {Array<string>} roleData.permissions - Array of permission codes (optional)
   * @returns {Promise<Object>} Updated role data
   */
  updateRole: async (roleId, roleData) => {
    try {
      const response = await api.put(`/roles/${roleId}`, roleData)
      return response.data
    } catch (error) {
      console.error('Error updating role:', error)
      throw error
    }
  },

  /**
   * Delete role
   * @param {number} roleId - Role ID
   * @returns {Promise<Object>} Success message
   */
  deleteRole: async (roleId) => {
    try {
      const response = await api.delete(`/roles/${roleId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting role:', error)
      throw error
    }
  },

  /**
   * Search roles by name or description
   * @param {string} searchTerm - Search term
   * @returns {Promise<Object>} Search results
   */
  searchRoles: async (searchTerm) => {
    try {
      const response = await api.get('/roles', {
        params: { search: searchTerm }
      })
      return response.data
    } catch (error) {
      console.error('Error searching roles:', error)
      throw error
    }
  },

  /**
   * Update multiple permissions at once
   * @param {number} roleId - Role ID
   * @param {Array<string>} permissions - Array of permission codes
   * @returns {Promise<Object>} Updated role data
   */
  updatePermissions: async (roleId, permissions) => {
    try {
      const response = await api.put(`/roles/${roleId}`, { permissions })
      return response.data
    } catch (error) {
      console.error('Error updating permissions:', error)
      throw error
    }
  }
}

export default roleService

