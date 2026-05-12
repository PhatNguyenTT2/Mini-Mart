import api from './api'

/**
 * Supplier Service
 * Handles all API calls related to suppliers
 */
const supplierService = {
  /**
   * Get all suppliers with optional filters
   * @param {Object} params - Query parameters
   * @param {boolean} params.isActive - Filter by active status
   * @param {string} params.search - Search by company name, supplier code, or phone
   * @param {string} params.paymentTerms - Filter by payment terms (cod/net15/net30/net60/net90)
   * @param {boolean} params.highDebt - Filter suppliers with high debt (>80% credit utilization)
   * @param {boolean} params.creditExceeded - Filter suppliers exceeding credit limit
   * @param {number} params.minCreditLimit - Filter by minimum credit limit
   * @param {number} params.maxCreditLimit - Filter by maximum credit limit
   * @param {boolean} params.withPurchaseOrders - Include purchase orders
   * @param {number} params.page - Page number for pagination
   * @param {number} params.limit - Items per page
   * @returns {Promise<Object>} Response with suppliers array and pagination
   */
  getAllSuppliers: async (params = {}) => {
    try {
      const response = await api.get('/suppliers', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching suppliers:', error)
      throw error
    }
  },

  /**
   * Get supplier by ID
   * @param {string} supplierId - Supplier ID
   * @returns {Promise<Object>} Supplier data with purchase orders and statistics
   */
  getSupplierById: async (supplierId) => {
    try {
      const response = await api.get(`/suppliers/${supplierId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching supplier:', error)
      throw error
    }
  },

  /**
   * Create new supplier
   * @param {Object} supplierData - Supplier data
   * @param {string} supplierData.companyName - Company name (required)
   * @param {string} supplierData.phone - Phone number (optional, 10-15 digits)
   * @param {string} supplierData.address - Address (optional)
   * @param {string} supplierData.accountNumber - Bank account number (optional)
   * @param {string} supplierData.paymentTerms - Payment terms (optional: cod/net15/net30/net60/net90, default: net30)
   * @param {number} supplierData.creditLimit - Credit limit (optional, default: 0)
   * @param {boolean} supplierData.isActive - Active status (optional, default: true)
   * @returns {Promise<Object>} Created supplier data
   */
  createSupplier: async (supplierData) => {
    try {
      const response = await api.post('/suppliers', supplierData)
      return response.data
    } catch (error) {
      console.error('Error creating supplier:', error)
      throw error
    }
  },

  /**
   * Update supplier
   * @param {string} supplierId - Supplier ID
   * @param {Object} supplierData - Updated supplier data
   * @param {string} supplierData.companyName - Company name (optional)
   * @param {string} supplierData.phone - Phone number (optional)
   * @param {string} supplierData.address - Address (optional)
   * @param {string} supplierData.accountNumber - Bank account number (optional)
   * @param {string} supplierData.paymentTerms - Payment terms (optional)
   * @param {number} supplierData.creditLimit - Credit limit (optional)
   * @param {number} supplierData.currentDebt - Current debt (optional, normally updated by system)
   * @param {boolean} supplierData.isActive - Active status (optional)
   * @returns {Promise<Object>} Updated supplier data
   */
  updateSupplier: async (supplierId, supplierData) => {
    try {
      const response = await api.put(`/suppliers/${supplierId}`, supplierData)
      return response.data
    } catch (error) {
      console.error('Error updating supplier:', error)
      throw error
    }
  },

  /**
   * Delete supplier (soft delete)
   * @param {string} supplierId - Supplier ID
   * @returns {Promise<Object>} Success message
   * @note Cannot delete supplier with outstanding debt or active purchase orders
   */
  deleteSupplier: async (supplierId) => {
    try {
      const response = await api.delete(`/suppliers/${supplierId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting supplier:', error)
      throw error
    }
  },

  /**
   * Search suppliers by company name, supplier code, or phone
   * @param {string} searchTerm - Search term
   * @param {number} limit - Maximum results (optional, default 20)
   * @returns {Promise<Object>} Matching suppliers
   */
  searchSuppliers: async (searchTerm, limit = 20) => {
    try {
      const response = await api.get('/suppliers', {
        params: { search: searchTerm, limit }
      })
      return response.data
    } catch (error) {
      console.error('Error searching suppliers:', error)
      throw error
    }
  },

  /**
   * Get active suppliers only
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Active suppliers
   */
  getActiveSuppliers: async (params = {}) => {
    try {
      const response = await api.get('/suppliers', {
        params: { isActive: true, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching active suppliers:', error)
      throw error
    }
  },

  /**
   * Get inactive suppliers only
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Inactive suppliers
   */
  getInactiveSuppliers: async (params = {}) => {
    try {
      const response = await api.get('/suppliers', {
        params: { isActive: false, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching inactive suppliers:', error)
      throw error
    }
  },

  /**
   * Get suppliers with high debt (>80% credit utilization)
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Suppliers with high debt
   */
  getHighDebtSuppliers: async (params = {}) => {
    try {
      const response = await api.get('/suppliers', {
        params: { highDebt: true, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching high debt suppliers:', error)
      throw error
    }
  },

  /**
   * Get suppliers exceeding credit limit
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Suppliers exceeding credit limit
   */
  getCreditExceededSuppliers: async (params = {}) => {
    try {
      const response = await api.get('/suppliers', {
        params: { creditExceeded: true, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching suppliers exceeding credit:', error)
      throw error
    }
  },

  /**
   * Get suppliers by payment terms
   * @param {string} paymentTerms - Payment terms (cod/net15/net30/net60/net90)
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Suppliers with specified payment terms
   */
  getSuppliersByPaymentTerms: async (paymentTerms, params = {}) => {
    try {
      const response = await api.get('/suppliers', {
        params: { paymentTerms, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching suppliers by payment terms:', error)
      throw error
    }
  },

  /**
   * Get suppliers with purchase orders
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Suppliers with purchase orders populated
   */
  getSuppliersWithPurchaseOrders: async (params = {}) => {
    try {
      const response = await api.get('/suppliers', {
        params: { withPurchaseOrders: true, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching suppliers with purchase orders:', error)
      throw error
    }
  },

  /**
   * Update supplier credit limit
   * @param {string} supplierId - Supplier ID
   * @param {number} creditLimit - New credit limit
   * @returns {Promise<Object>} Updated supplier data
   * @note Credit limit must be >= current debt
   */
  updateCreditLimit: async (supplierId, creditLimit) => {
    try {
      const response = await api.put(`/suppliers/${supplierId}`, { creditLimit })
      return response.data
    } catch (error) {
      console.error('Error updating credit limit:', error)
      throw error
    }
  },

  /**
   * Update supplier payment terms
   * @param {string} supplierId - Supplier ID
   * @param {string} paymentTerms - New payment terms (cod/net15/net30/net60/net90)
   * @returns {Promise<Object>} Updated supplier data
   */
  updatePaymentTerms: async (supplierId, paymentTerms) => {
    try {
      const response = await api.put(`/suppliers/${supplierId}`, { paymentTerms })
      return response.data
    } catch (error) {
      console.error('Error updating payment terms:', error)
      throw error
    }
  },

  /**
   * Activate supplier
   * @param {string} supplierId - Supplier ID
   * @returns {Promise<Object>} Updated supplier data
   */
  activateSupplier: async (supplierId) => {
    try {
      const response = await api.put(`/suppliers/${supplierId}`, { isActive: true })
      return response.data
    } catch (error) {
      console.error('Error activating supplier:', error)
      throw error
    }
  },

  /**
   * Deactivate supplier
   * @param {string} supplierId - Supplier ID
   * @returns {Promise<Object>} Updated supplier data
   */
  deactivateSupplier: async (supplierId) => {
    try {
      const response = await api.put(`/suppliers/${supplierId}`, { isActive: false })
      return response.data
    } catch (error) {
      console.error('Error deactivating supplier:', error)
      throw error
    }
  },

  /**
   * Toggle supplier active status
   * @param {string} supplierId - Supplier ID
   * @param {boolean} isActive - New active status
   * @returns {Promise<Object>} Updated supplier data
   */
  toggleActive: async (supplierId, isActive) => {
    try {
      const response = await api.put(`/suppliers/${supplierId}`, { isActive })
      return response.data
    } catch (error) {
      console.error('Error toggling supplier status:', error)
      throw error
    }
  },

  /**
   * Update supplier contact information
   * @param {string} supplierId - Supplier ID
   * @param {Object} contactData - Contact data
   * @param {string} contactData.phone - Phone number (optional)
   * @param {string} contactData.address - Address (optional)
   * @param {string} contactData.accountNumber - Bank account number (optional)
   * @returns {Promise<Object>} Updated supplier data
   */
  updateContact: async (supplierId, contactData) => {
    try {
      const response = await api.put(`/suppliers/${supplierId}`, contactData)
      return response.data
    } catch (error) {
      console.error('Error updating supplier contact:', error)
      throw error
    }
  },

  /**
   * Check if company name already exists
   * @param {string} companyName - Company name to check
   * @param {string} excludeId - Supplier ID to exclude from check (for update)
   * @returns {Promise<boolean>} True if company name exists
   */
  checkCompanyNameExists: async (companyName, excludeId = null) => {
    try {
      const response = await api.get('/suppliers', {
        params: { search: companyName }
      })

      const suppliers = response.data.data?.suppliers || []

      // Check if exact match exists (case-insensitive)
      const exists = suppliers.some(supplier =>
        supplier.companyName.toLowerCase() === companyName.toLowerCase() &&
        (!excludeId || supplier.id !== excludeId)
      )

      return exists
    } catch (error) {
      console.error('Error checking company name:', error)
      throw error
    }
  },

  /**
   * Check if phone number already exists
   * @param {string} phone - Phone number to check
   * @param {string} excludeId - Supplier ID to exclude from check (for update)
   * @returns {Promise<boolean>} True if phone exists
   */
  checkPhoneExists: async (phone, excludeId = null) => {
    try {
      const response = await api.get('/suppliers', {
        params: { search: phone }
      })

      const suppliers = response.data.data?.suppliers || []

      // Check if exact match exists
      const exists = suppliers.some(supplier =>
        supplier.phone === phone &&
        (!excludeId || supplier.id !== excludeId)
      )

      return exists
    } catch (error) {
      console.error('Error checking phone number:', error)
      throw error
    }
  },

  /**
   * Get suppliers with pagination
   * @param {number} page - Page number
   * @param {number} limit - Items per page
   * @returns {Promise<Object>} Paginated suppliers
   */
  getSuppliersPaginated: async (page = 1, limit = 20) => {
    try {
      const response = await api.get('/suppliers', {
        params: { page, limit }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching paginated suppliers:', error)
      throw error
    }
  }
}

export default supplierService
