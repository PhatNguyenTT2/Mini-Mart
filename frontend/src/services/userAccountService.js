import api from './api'

/**
 * User Account Service
 * Handles all API calls related to user accounts
 */
const userAccountService = {
  /**
   * Get all user accounts with optional filters
   * @param {Object} params - Query parameters
   * @param {boolean} params.isActive - Filter by active status
   * @param {string} params.search - Search by username or email
   * @param {string} params.role - Filter by role ID
   * @returns {Promise<Object>} Response with users array and count
   */
  getAllUsers: async (params = {}) => {
    try {
      const response = await api.get('/user-accounts', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching users:', error)
      throw error
    }
  },

  /**
   * Get user account by ID
   * @param {string} userId - User ID
   * @returns {Promise<Object>} User account data
   */
  getUserById: async (userId) => {
    try {
      const response = await api.get(`/user-accounts/${userId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching user:', error)
      throw error
    }
  },

  /**
   * Create new user account
   * @param {Object} userData - User data
   * @param {string} userData.username - Username
   * @param {string} userData.email - Email
   * @param {string} userData.password - Password
   * @param {string} userData.role - Role ID
   * @param {boolean} userData.isActive - Active status (optional, default true)
   * @returns {Promise<Object>} Created user data
   */
  createUser: async (userData) => {
    try {
      const response = await api.post('/user-accounts', userData)
      return response.data
    } catch (error) {
      console.error('Error creating user:', error)
      throw error
    }
  },

  /**
   * Update user account
   * @param {string} userId - User ID
   * @param {Object} userData - Updated user data
   * @param {string} userData.username - Username (optional)
   * @param {string} userData.email - Email (optional)
   * @param {string} userData.password - New password (optional)
   * @param {string} userData.role - Role ID (optional)
   * @param {boolean} userData.isActive - Active status (optional)
   * @returns {Promise<Object>} Updated user data
   */
  updateUser: async (userId, userData) => {
    try {
      const response = await api.put(`/user-accounts/${userId}`, userData)
      return response.data
    } catch (error) {
      console.error('Error updating user:', error)
      throw error
    }
  },

  /**
   * Delete/Deactivate user account (soft delete)
   * @param {string} userId - User ID
   * @returns {Promise<Object>} Success message
   */
  deleteUser: async (userId) => {
    try {
      const response = await api.delete(`/user-accounts/${userId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting user:', error)
      throw error
    }
  },

  /**
   * Search users by username or email
   * @param {string} searchTerm - Search term
   * @returns {Promise<Object>} Search results
   */
  searchUsers: async (searchTerm) => {
    try {
      const response = await api.get('/user-accounts', {
        params: { search: searchTerm }
      })
      return response.data
    } catch (error) {
      console.error('Error searching users:', error)
      throw error
    }
  },

  /**
   * Get users by role
   * @param {string} roleId - Role ID
   * @returns {Promise<Object>} Users with specified role
   */
  getUsersByRole: async (roleId) => {
    try {
      const response = await api.get('/user-accounts', {
        params: { role: roleId }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching users by role:', error)
      throw error
    }
  },

  /**
   * Get active users only
   * @returns {Promise<Object>} Active users
   */
  getActiveUsers: async () => {
    try {
      const response = await api.get('/user-accounts', {
        params: { isActive: true }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching active users:', error)
      throw error
    }
  },

  /**
   * Get inactive users only
   * @returns {Promise<Object>} Inactive users
   */
  getInactiveUsers: async () => {
    try {
      const response = await api.get('/user-accounts', {
        params: { isActive: false }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching inactive users:', error)
      throw error
    }
  },

  /**
   * Request password reset
   * @param {string} email - User email
   * @returns {Promise<Object>} Reset request response
   */
  forgotPassword: async (email) => {
    try {
      const response = await api.post('/user-accounts/forgot-password', { email })
      return response.data
    } catch (error) {
      console.error('Error requesting password reset:', error)
      throw error
    }
  },

  /**
   * Reset password using reset token
   * @param {Object} resetData - Reset data
   * @param {string} resetData.resetToken - Reset token
   * @param {string} resetData.newPassword - New password
   * @returns {Promise<Object>} Reset response
   */
  resetPassword: async (resetData) => {
    try {
      const response = await api.post('/user-accounts/reset-password', resetData)
      return response.data
    } catch (error) {
      console.error('Error resetting password:', error)
      throw error
    }
  },

  /**
   * Verify reset token validity
   * @param {string} resetToken - Reset token
   * @returns {Promise<Object>} Token verification response
   */
  verifyResetToken: async (resetToken) => {
    try {
      const response = await api.post('/user-accounts/verify-reset-token', { resetToken })
      return response.data
    } catch (error) {
      console.error('Error verifying reset token:', error)
      throw error
    }
  }
}

export default userAccountService