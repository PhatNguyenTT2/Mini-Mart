import api from './api'

const paymentService = {
  // Create VNPay payment URL
  createVNPayUrl: async ({ orderId, amount, orderInfo, storeId }) => {
    const response = await api.post('/payments/vnpay/create-url', {
      amount,
      reference_type: 'SaleOrder',
      reference_id: orderId,
      notes: orderInfo || `Payment for order #${orderId}`,
      origin: 'customer'  // Signal backend to redirect back to customer web
    }, {
      headers: { 'x-store-id': storeId }
    })
    return response.data
  },

  // Create direct payment for COD
  createDirectPayment: async ({ orderId, amount, items, storeId }) => {
    const response = await api.post('/payments/direct', {
      amount,
      method: 'cash',
      reference_type: 'SaleOrder',
      reference_id: orderId,
      items: items.map(item => ({
        batchId: item.batchId || null,
        locationId: null,
        quantity: item.quantity
      })),
      deliveryType: 'delivery',
      notes: `COD payment for order #${orderId}`
    }, {
      headers: { 'x-store-id': storeId }
    })
    return response.data
  },

  // Check VNPay transaction status
  checkVNPayStatus: async (txnRef, storeId) => {
    const response = await api.get(`/payments/vnpay/check-status/${txnRef}`, {
      headers: { 'x-store-id': storeId }
    })
    return response.data
  },

  // Get payments by order
  getPaymentsByOrder: async (orderId, storeId) => {
    const response = await api.get('/payments', {
      params: { referenceType: 'Order', referenceId: orderId },
      headers: { 'x-store-id': storeId }
    })
    return response.data
  }
}
export default paymentService
