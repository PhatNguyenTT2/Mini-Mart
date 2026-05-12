import api from './api'

/**
 * Order Service
 * Handles all API calls related to orders
 * Adapted for Order Microservice (Service 3, port 3003)
 */
const orderService = {
  /**
   * Get all orders with optional filters
   */
  getAllOrders: async (params = {}) => {
    try {
      const response = await api.get('/orders', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching orders:', error)
      throw error
    }
  },

  /**
   * Get order by ID
   */
  getOrderById: async (orderId) => {
    try {
      const response = await api.get(`/orders/${orderId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching order:', error)
      throw error
    }
  },

  /**
   * Create new order
   * Maps frontend camelCase → backend snake_case
   * Backend handles FEFO batch allocation when batch_id is not provided
   */
  createOrder: async (orderData) => {
    try {
      const payload = {
        customer_id: orderData.customer_id || orderData.customer || orderData.customerId,
        delivery_type: orderData.delivery_type || orderData.deliveryType || 'pickup',
        address: orderData.address || '',
        shipping_fee: orderData.shipping_fee || orderData.shippingFee || 0,
        discount_percentage: orderData.discount_percentage || orderData.discountPercentage || 0,
        items: (orderData.items || orderData.details || []).map(item => ({
          product_id: item.product_id || item.productId,
          product_name: item.product_name || item.productName || item.product?.name || 'Product',
          batch_id: item.batch_id || item.batchId || null,  // null → backend FEFO auto
          quantity: item.quantity,
          unit_price: item.unit_price || item.unitPrice || item.price || 0
        }))
      }

      const response = await api.post('/orders', payload)
      return response.data
    } catch (error) {
      console.error('Error creating order:', error)
      throw error
    }
  },

  /**
   * Update order (general update — address, shipping, discount, status, paymentStatus)
   */
  updateOrder: async (orderId, orderData) => {
    try {
      const response = await api.put(`/orders/${orderId}`, orderData)
      return response.data
    } catch (error) {
      console.error('Error updating order:', error)
      throw error
    }
  },

  /**
   * Delete order
   */
  deleteOrder: async (orderId) => {
    try {
      const response = await api.delete(`/orders/${orderId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting order:', error)
      throw error
    }
  },

  /**
   * Delete all draft orders (bulk delete)
   */
  deleteAllDrafts: async () => {
    try {
      const response = await api.delete('/orders/bulk/draft')
      return response.data.data || response.data
    } catch (error) {
      console.error('Error deleting all draft orders:', error)
      throw error
    }
  },

  /**
   * Refund order
   */
  refundOrder: async (orderId, refundData = {}) => {
    try {
      const response = await api.post(`/orders/${orderId}/refund`, refundData)
      return response.data
    } catch (error) {
      console.error('Error refunding order:', error)
      throw error
    }
  },

  /**
   * Update draft order items (delete old → FEFO re-allocate → insert new)
   * Only works for orders with status='draft'
   */
  updateDraftItems: async (orderId, items) => {
    try {
      const payload = {
        items: items.map(item => ({
          product_id: item.product_id || item.productId,
          product_name: item.product_name || item.productName || item.product?.name || 'Product',
          batch_id: item.batch_id || item.batchId || null,
          quantity: item.quantity,
          unit_price: item.unit_price || item.unitPrice || item.price || 0
        }))
      }
      const response = await api.put(`/orders/${orderId}/items`, payload)
      return response.data
    } catch (error) {
      console.error('Error updating draft items:', error)
      throw error
    }
  },

  // ========== CONVENIENCE METHODS ==========

  searchOrders: async (keyword, options = {}) => {
    try {
      const params = { search: keyword, ...options }
      const response = await api.get('/orders', { params })
      return response.data
    } catch (error) {
      console.error('Error searching orders:', error)
      throw error
    }
  },

  getOrdersByStatus: async (status, params = {}) => {
    try {
      const response = await api.get('/orders', { params: { status, ...params } })
      return response.data
    } catch (error) {
      console.error('Error fetching orders by status:', error)
      throw error
    }
  },

  getPendingOrders: async (params = {}) => orderService.getOrdersByStatus('pending', params),
  getShippingOrders: async (params = {}) => orderService.getOrdersByStatus('shipping', params),
  getDeliveredOrders: async (params = {}) => orderService.getOrdersByStatus('delivered', params),
  getCancelledOrders: async (params = {}) => orderService.getOrdersByStatus('cancelled', params),

  getOrdersByPaymentStatus: async (paymentStatus, params = {}) => {
    try {
      const response = await api.get('/orders', { params: { paymentStatus, ...params } })
      return response.data
    } catch (error) {
      console.error('Error fetching orders by payment status:', error)
      throw error
    }
  },

  getUnpaidOrders: async (params = {}) => orderService.getOrdersByPaymentStatus('pending', params),
  getPaidOrders: async (params = {}) => orderService.getOrdersByPaymentStatus('paid', params),

  getOrdersByCustomer: async (customerId, params = {}) => {
    try {
      const response = await api.get('/orders', { params: { customer: customerId, ...params } })
      return response.data
    } catch (error) {
      console.error('Error fetching orders by customer:', error)
      throw error
    }
  },

  getOrdersByEmployee: async (employeeId, params = {}) => {
    try {
      const response = await api.get('/orders', { params: { createdBy: employeeId, ...params } })
      return response.data
    } catch (error) {
      console.error('Error fetching orders by employee:', error)
      throw error
    }
  },

  getOrdersByDateRange: async (startDate, endDate, params = {}) => {
    try {
      const response = await api.get('/orders', { params: { startDate, endDate, ...params } })
      return response.data
    } catch (error) {
      console.error('Error fetching orders by date range:', error)
      throw error
    }
  },

  getOrdersByDeliveryType: async (deliveryType, params = {}) => {
    try {
      const response = await api.get('/orders', { params: { deliveryType, ...params } })
      return response.data
    } catch (error) {
      console.error('Error fetching orders by delivery type:', error)
      throw error
    }
  },

  getDeliveryOrders: async (params = {}) => orderService.getOrdersByDeliveryType('delivery', params),
  getPickupOrders: async (params = {}) => orderService.getOrdersByDeliveryType('pickup', params),

  getTodayOrders: async (params = {}) => {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const tomorrow = new Date(today)
    tomorrow.setDate(tomorrow.getDate() + 1)
    return orderService.getOrdersByDateRange(today.toISOString(), tomorrow.toISOString(), params)
  },

  updateOrderStatus: async (orderId, newStatus) => orderService.updateOrder(orderId, { status: newStatus }),
  updatePaymentStatus: async (orderId, newPaymentStatus) => orderService.updateOrder(orderId, { paymentStatus: newPaymentStatus }),
  markAsPaid: async (orderId) => orderService.updatePaymentStatus(orderId, 'paid'),
  markAsPending: async (orderId) => orderService.updatePaymentStatus(orderId, 'pending'),
  cancelOrder: async (orderId) => orderService.updateOrderStatus(orderId, 'cancelled'),
  shipOrder: async (orderId) => orderService.updateOrderStatus(orderId, 'shipping'),
  deliverOrder: async (orderId) => orderService.updateOrderStatus(orderId, 'delivered'),
  updateShippingFee: async (orderId, shippingFee) => orderService.updateOrder(orderId, { shippingFee }),
  updateDiscount: async (orderId, discountPercentage) => orderService.updateOrder(orderId, { discountPercentage }),
  updateAddress: async (orderId, address) => orderService.updateOrder(orderId, { address }),
  changeDeliveryType: async (orderId, deliveryType) => orderService.updateOrder(orderId, { deliveryType })
}

export default orderService
