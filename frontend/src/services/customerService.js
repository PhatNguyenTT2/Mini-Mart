import api from './api'

/**
 * Customer Service (Admin context)
 * Uses adminToken via api.js
 * POS customer operations are in posDataService.js
 */
const customerService = {
  getAllCustomers: async (params = {}) => {
    try {
      const response = await api.get('/customers', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching customers:', error)
      throw error
    }
  },

  getCustomerById: async (customerId) => {
    try {
      const response = await api.get(`/customers/${customerId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching customer:', error)
      throw error
    }
  },

  createCustomer: async (customerData) => {
    try {
      const response = await api.post('/customers', customerData)
      return response.data
    } catch (error) {
      console.error('Error creating customer:', error)
      throw error
    }
  },

  updateCustomer: async (customerId, customerData) => {
    try {
      const response = await api.put(`/customers/${customerId}`, customerData)
      return response.data
    } catch (error) {
      console.error('Error updating customer:', error)
      throw error
    }
  },

  deleteCustomer: async (customerId) => {
    try {
      const response = await api.delete(`/customers/${customerId}`)
      return response.data
    } catch (error) {
      throw error
    }
  },

  toggleActive: async (customerId, isActive) => {
    try {
      const response = await api.patch(`/customers/${customerId}/toggle-active`, { isActive })
      return response.data
    } catch (error) {
      console.error('Error toggling customer active status:', error)
      throw error
    }
  },

  searchCustomers: async (keyword, options = {}) => {
    try {
      const params = {
        search: keyword,
        ...options
      }
      const response = await api.get('/customers', { params })
      return response.data
    } catch (error) {
      console.error('Error searching customers:', error)
      throw error
    }
  },

  /**
   * Get customer orders — routes to Order Service via gateway
   * GET /api/orders?customer=<customerId>
   */
  getCustomerOrders: async (customerId, params = {}) => {
    try {
      const response = await api.get('/orders', {
        params: { customer: customerId, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching customer orders:', error)
      throw error
    }
  }
}

export default customerService
