import api from './api'

/**
 * Payment Service
 * Handles API calls to payment microservice
 * Backend: /api/payments → payment_service:3007
 *
 * The backend handles field mapping:
 * - paymentMethod ↔ method
 * - referenceType 'Order' ↔ DB 'SaleOrder'
 * - Response is camelCase with generated paymentNumber
 */
const paymentService = {
  /**
   * Get all payments with optional filters
   * Backend returns: { status: 'success', data: { payments: [...] } }
   */
  getAllPayments: async (params = {}) => {
    try {
      const response = await api.get('/payments', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching payments:', error)
      throw error
    }
  },

  /**
   * Get payment by ID
   * Backend returns: { status: 'success', data: { payment: {...} } }
   */
  getPaymentById: async (paymentId) => {
    try {
      const response = await api.get(`/payments/${paymentId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching payment:', error)
      throw error
    }
  },

  /**
   * Create new payment (pending status — admin panel flow)
   * Backend accepts both camelCase and snake_case field names
   */
  createPayment: async (paymentData) => {
    try {
      const response = await api.post('/payments', paymentData)
      return response.data
    } catch (error) {
      console.error('Error creating payment:', error)
      throw error
    }
  },

  /**
   * Create direct payment (completed immediately — triggers saga event)
   * Use for cash/bank_transfer when admin wants to pay now
   * Backend: POST /payments/direct → auto-publishes payment.completed
   */
  createDirectPayment: async (paymentData) => {
    try {
      const response = await api.post('/payments/direct', paymentData)
      return response.data
    } catch (error) {
      console.error('Error creating direct payment:', error)
      throw error
    }
  },

  /**
   * Update payment (only pending payments can be edited)
   */
  updatePayment: async (paymentId, paymentData) => {
    try {
      const response = await api.put(`/payments/${paymentId}`, paymentData)
      return response.data
    } catch (error) {
      console.error('Error updating payment:', error)
      throw error
    }
  },

  /**
   * Delete payment (only pending/cancelled)
   */
  deletePayment: async (paymentId) => {
    try {
      const response = await api.delete(`/payments/${paymentId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting payment:', error)
      throw error
    }
  },

  /**
   * Refund a completed payment (financial only — inventory return is separate)
   * @param {number} paymentId
   */
  refundPayment: async (paymentId) => {
    try {
      const response = await api.post(`/payments/${paymentId}/refund`)
      return response.data
    } catch (error) {
      console.error('Error refunding payment:', error)
      throw error
    }
  },

  // ========== CONVENIENCE METHODS ==========

  /**
   * Get payments filtered by reference
   */
  getPaymentsForOrder: async (orderId, params = {}) => {
    return paymentService.getAllPayments({
      referenceType: 'Order',
      referenceId: orderId,
      ...params
    })
  },

  getPaymentsForPurchaseOrder: async (purchaseOrderId, params = {}) => {
    return paymentService.getAllPayments({
      referenceType: 'PurchaseOrder',
      referenceId: purchaseOrderId,
      ...params
    })
  },

  /**
   * Create payment for specific reference types
   */
  createOrderPayment: async (orderId, paymentData) => {
    return paymentService.createPayment({
      ...paymentData,
      referenceType: 'Order',
      referenceId: orderId
    })
  },

  createPurchaseOrderPayment: async (purchaseOrderId, paymentData) => {
    return paymentService.createPayment({
      ...paymentData,
      referenceType: 'PurchaseOrder',
      referenceId: purchaseOrderId
    })
  },

  /**
   * Update payment status
   * When changing to 'completed', backend publishes payment.completed event
   */
  updatePaymentStatus: async (paymentId, newStatus) => {
    return paymentService.updatePayment(paymentId, { status: newStatus })
  },

  completePayment: async (paymentId) => {
    return paymentService.updatePaymentStatus(paymentId, 'completed')
  },

  cancelPayment: async (paymentId) => {
    return paymentService.updatePaymentStatus(paymentId, 'cancelled')
  }
}

export default paymentService
