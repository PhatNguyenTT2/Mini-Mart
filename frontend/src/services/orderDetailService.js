import api from './api'

/**
 * OrderDetail Service
 * Handles read-only API calls to order details
 * Note: CUD operations are handled via orderService.createOrder / updateDraftItems
 */
const orderDetailService = {
  /**
   * Get order details by order ID
   * Backend: GET /api/order-details?order={orderId}
   */
  getDetailsByOrder: async (orderId, params = {}) => {
    try {
      const response = await api.get('/order-details', {
        params: { order: orderId, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching order details by order:', error)
      throw error
    }
  },

  /**
   * Get order detail by ID
   * Backend: GET /api/order-details/:id
   */
  getOrderDetailById: async (orderDetailId) => {
    try {
      const response = await api.get(`/order-details/${orderDetailId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching order detail:', error)
      throw error
    }
  }
}

export default orderDetailService
