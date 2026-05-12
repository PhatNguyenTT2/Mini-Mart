import api from './api'

/**
 * Employee Service
 * Handles all API calls related to employees
 */
const employeeService = {
  /**
   * Get all employees with optional filters
   * @param {Object} params - Query parameters
   * @param {string} params.search - Search by name or phone
   * @param {boolean} params.isActive - Filter by user account active status
   * @returns {Promise<Object>} Response with employees array and count
   */
  getAllEmployees: async (params = {}) => {
    try {
      const response = await api.get('/employees', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching employees:', error)
      throw error
    }
  },

  /**
   * Get employee by ID
   * @param {string} employeeId - Employee ID
   * @returns {Promise<Object>} Employee data with user account
   */
  getEmployeeById: async (employeeId) => {
    try {
      const response = await api.get(`/employees/${employeeId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching employee:', error)
      throw error
    }
  },

  /**
   * Create new employee with user account (all-in-one)
   * @param {Object} data - Employee and user data
   * @param {Object} data.userData - User account data
   * @param {string} data.userData.username - Username (required)
   * @param {string} data.userData.email - Email (required)
   * @param {string} data.userData.password - Password (required)
   * @param {string} data.userData.role - Role ID (required)
   * @param {boolean} data.userData.isActive - Active status (optional, default true)
   * @param {Object} data.employeeData - Employee profile data
   * @param {string} data.employeeData.fullName - Full name (required)
   * @param {string} data.employeeData.phone - Phone number (optional)
   * @param {string} data.employeeData.address - Address (optional)
   * @param {string} data.employeeData.dateOfBirth - Date of birth (optional)
   * @returns {Promise<Object>} Created employee data
   */
  createEmployee: async (data) => {
    try {
      const response = await api.post('/employees', data)
      return response.data
    } catch (error) {
      console.error('Error creating employee:', error)
      throw error
    }
  },

  /**
   * Update employee profile
   * @param {string} employeeId - Employee ID
   * @param {Object} profileData - Updated profile data
   * @param {string} profileData.fullName - Full name (optional)
   * @param {string} profileData.phone - Phone number (optional)
   * @param {string} profileData.address - Address (optional)
   * @param {string} profileData.dateOfBirth - Date of birth (optional)
   * @returns {Promise<Object>} Updated employee data
   */
  updateEmployee: async (employeeId, profileData) => {
    try {
      const response = await api.put(`/employees/${employeeId}`, profileData)
      return response.data
    } catch (error) {
      console.error('Error updating employee:', error)
      throw error
    }
  },

  /**
   * Delete employee (hard delete)
   * @param {string} employeeId - Employee ID
   * @returns {Promise<Object>} Success message
   * @note This is a hard delete. For soft delete, deactivate the user account instead
   */
  deleteEmployee: async (employeeId) => {
    try {
      const response = await api.delete(`/employees/${employeeId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting employee:', error)
      throw error
    }
  },

  /**
   * Search employees by name or phone
   * @param {string} searchTerm - Search term
   * @returns {Promise<Object>} Search results
   */
  searchEmployees: async (searchTerm) => {
    try {
      const response = await api.get('/employees', {
        params: { search: searchTerm }
      })
      return response.data
    } catch (error) {
      console.error('Error searching employees:', error)
      throw error
    }
  },

  /**
   * Get active employees only
   * @returns {Promise<Object>} Active employees
   */
  getActiveEmployees: async () => {
    try {
      const response = await api.get('/employees', {
        params: { isActive: true }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching active employees:', error)
      throw error
    }
  },

  /**
   * Get inactive employees only
   * @returns {Promise<Object>} Inactive employees
   */
  getInactiveEmployees: async () => {
    try {
      const response = await api.get('/employees', {
        params: { isActive: false }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching inactive employees:', error)
      throw error
    }
  },

  /**
   * Update employee contact information
   * @param {string} employeeId - Employee ID
   * @param {Object} contactData - Contact data
   * @param {string} contactData.phone - Phone number
   * @param {string} contactData.address - Address
   * @returns {Promise<Object>} Updated employee data
   */
  updateContactInfo: async (employeeId, contactData) => {
    try {
      const response = await api.put(`/employees/${employeeId}`, contactData)
      return response.data
    } catch (error) {
      console.error('Error updating contact info:', error)
      throw error
    }
  }
}

export default employeeService
