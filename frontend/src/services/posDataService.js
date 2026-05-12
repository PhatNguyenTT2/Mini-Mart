import posApi from './posApi'

/**
 * POS Data Service
 * Wrapper for shared endpoints accessed from POS context.
 * Uses posApi (posToken) instead of api (adminToken).
 *
 * Rule: POS hooks/components MUST use this service for data operations.
 * posLoginService handles auth-only (login/logout/verify).
 */
const posDataService = {
  // ========== Categories ==========
  getActiveCategories: async () => {
    const response = await posApi.get('/categories', { params: { isActive: true } })
    return response.data
  },

  getCategoryTree: async () => {
    const response = await posApi.get('/categories/tree')
    return response.data
  },

  // ========== Products ==========
  getAllProducts: async (filters = {}) => {
    const response = await posApi.get('/products', { params: filters })
    return response.data
  },

  getProductByBarcode: async (barcode) => {
    const response = await posApi.get(`/products/barcode/${barcode}`)
    return response.data
  },

  getProductById: async (productId) => {
    const response = await posApi.get(`/products/${productId}`)
    return response.data
  },

  // ========== Inventory ==========
  getInventorySummary: async () => {
    const response = await posApi.get('/inventory/summary')
    return response.data
  },

  getProductBatches: async (productId) => {
    const response = await posApi.get(`/inventory/batches/${productId}`)
    return response.data
  },

  // ========== Warehouse / Store Map ==========
  getStoreShelfBlocks: async () => {
    const response = await posApi.get('/warehouse/blocks', { params: { type: 'store_shelf' } })
    return response.data
  },

  getStoreMapData: async () => {
    const response = await posApi.get('/warehouse/store-map-data')
    return response.data
  },

  getLocationById: async (locationId) => {
    const response = await posApi.get(`/warehouse/locations/${locationId}`)
    return response.data
  },

  // ========== Order Details ==========
  getOrderDetails: async (orderId) => {
    const response = await posApi.get(`/orders/${orderId}/details`)
    return response.data
  },

  // ========== Orders ==========
  createOrder: async (orderData) => {
    const rawCustId = orderData.customerId || orderData.customer_id;
    const payload = {
      customer_id: (rawCustId && rawCustId !== 'virtual-guest') ? rawCustId : null,
      delivery_type: orderData.deliveryType || 'pickup',
      shipping_fee: orderData.shippingFee || 0,
      items: (orderData.items || []).map(item => ({
        product_id: item.productId || item.product_id,
        product_name: item.productName || item.product_name || 'Product',
        batch_id: item.batchId || item.batch_id || null,
        quantity: item.quantity,
        unit_price: item.unitPrice || item.unit_price || item.price || 0
      }))
    }
    const response = await posApi.post('/orders', payload)
    return response.data
  },

  getOrderById: async (orderId) => {
    const response = await posApi.get(`/orders/${orderId}`)
    return response.data
  },

  updateOrder: async (orderId, data) => {
    const response = await posApi.put(`/orders/${orderId}`, data)
    return response.data
  },

  updateDraftItems: async (orderId, items) => {
    const payload = {
      items: items.map(item => ({
        product_id: item.productId || item.product_id,
        product_name: item.productName || item.product_name || 'Product',
        batch_id: item.batchId || item.batch_id || null,
        quantity: item.quantity,
        unit_price: item.unitPrice || item.unit_price || item.price || 0
      }))
    }
    const response = await posApi.put(`/orders/${orderId}/items`, payload)
    return response.data
  },

  deleteOrder: async (orderId) => {
    const response = await posApi.delete(`/orders/${orderId}`)
    return response.data
  },

  getOrdersByStatus: async (status) => {
    const response = await posApi.get('/orders', { params: { status } })
    return response.data
  },

  // ========== Payments ==========
  createDirectPayment: async ({ orderId, amount, method, items, deliveryType, notes }) => {
    const response = await posApi.post('/payments/direct', {
      reference_id: orderId,
      reference_type: 'SaleOrder',
      amount,
      method,
      items: items || [],
      deliveryType: deliveryType || 'pickup',
      notes: notes || ''
    })
    return response.data
  },

  // ========== VNPay ==========
  createVNPayUrl: async (orderId, amount, orderInfo) => {
    const response = await posApi.post('/payments/vnpay/create-url', {
      amount,
      reference_type: 'SaleOrder',
      reference_id: orderId,
      notes: orderInfo || `Thanh toán đơn hàng ${orderId}`
    })
    return response.data.data
  },

  checkVNPayStatus: async (vnpTxnRef) => {
    const response = await posApi.get(`/payments/vnpay/check-status/${vnpTxnRef}`)
    return response.data
  },

  // ========== Customers ==========
  searchCustomers: async (query, limit = 10) => {
    const response = await posApi.get('/customers', {
      params: { search: query, isActive: true, limit }
    })
    return response.data
  },

  getCustomerById: async (customerId) => {
    const response = await posApi.get(`/customers/${customerId}`)
    return response.data
  },

  getEmployeeById: async (employeeId) => {
    const response = await posApi.get(`/employees/${employeeId}`)
    return response.data
  },

  getDefaultGuest: async () => {
    const response = await posApi.get('/customers/default-guest')
    return response.data
  },

  createCustomer: async (customerData) => {
    const response = await posApi.post('/customers', customerData)
    return response.data
  },

  // ========== Discount Config ==========
  getActiveDiscounts: async () => {
    const response = await posApi.get('/customer-discount-settings/active')
    return response.data
  }
}

export default posDataService
