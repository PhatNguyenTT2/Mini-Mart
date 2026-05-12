import api from './api'

const orderService = {
  // Create delivery order
  createOrder: async ({ items, customerId, deliveryType, shippingAddress, shippingFee, notes, storeId }) => {
    const response = await api.post('/orders', {
      customer_id: customerId,
      delivery_type: deliveryType || 'delivery',
      shipping_fee: shippingFee || 0,
      address: shippingAddress || '',
      notes,
      items: items.map(item => ({
        product_id: item.id || item.productId,
        product_name: item.name,
        quantity: item.quantity,
        unit_price: item.price || item.unitPrice
      }))
    }, {
      headers: { 'x-store-id': storeId }
    })
    return response.data
  },

  // Get order by ID
  getOrderById: async (orderId, storeId) => {
    const response = await api.get(`/orders/${orderId}`, {
      headers: { 'x-store-id': storeId }
    })
    return response.data
  },

  // Get order list for current customer
  getMyOrders: async (filters = {}, storeId) => {
    const response = await api.get('/orders', { 
      params: filters,
      headers: { 'x-store-id': storeId }
    })
    return response.data
  },

  // Get order details (items)
  getOrderDetails: async (orderId, storeId) => {
    const response = await api.get(`/orders/${orderId}/details`, {
      headers: { 'x-store-id': storeId }
    })
    return response.data
  }
}
export default orderService
