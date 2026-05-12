import api from './api'

/**
 * Purchase Order Service
 * Handles all API calls related to purchase orders
 */
const purchaseOrderService = {
  /**
   * Get all purchase orders with optional filters
   * @param {Object} params - Query parameters
   * @param {string} params.status - Filter by status (pending/approved/received/cancelled)
   * @param {string} params.paymentStatus - Filter by payment status (unpaid/partial/paid)
   * @param {string} params.supplier - Filter by supplier ID
   * @param {string} params.createdBy - Filter by employee who created the order
   * @param {boolean} params.overdue - Filter overdue orders (expected delivery date passed)
   * @param {string} params.startDate - Filter orders after this date (ISO format)
   * @param {string} params.endDate - Filter orders before this date (ISO format)
   * @param {number} params.minTotal - Filter by minimum total price
   * @param {number} params.maxTotal - Filter by maximum total price
   * @param {string} params.search - Search by PO number
   * @param {boolean} params.withDetails - Include purchase order details
   * @param {number} params.page - Page number for pagination
   * @param {number} params.limit - Items per page
   * @returns {Promise<Object>} Response with purchaseOrders array and pagination
   */
  getAllPurchaseOrders: async (params = {}) => {
    try {
      const response = await api.get('/purchase-orders', { params })
      return response.data
    } catch (error) {
      console.error('Error fetching purchase orders:', error)
      throw error
    }
  },

  /**
   * Get purchase order by ID
   * @param {string} purchaseOrderId - Purchase order ID
   * @returns {Promise<Object>} Purchase order data with supplier, employee, details, and summary
   */
  getPurchaseOrderById: async (purchaseOrderId) => {
    try {
      const response = await api.get(`/purchase-orders/${purchaseOrderId}`)
      return response.data
    } catch (error) {
      console.error('Error fetching purchase order:', error)
      throw error
    }
  },

  /**
   * Create new purchase order
   * @param {Object} purchaseOrderData - Purchase order data
   * @param {string} purchaseOrderData.supplier - Supplier ID (required)
   * @param {string} purchaseOrderData.orderDate - Order date (optional, default: now)
   * @param {string} purchaseOrderData.expectedDeliveryDate - Expected delivery date (optional)
   * @param {number} purchaseOrderData.shippingFee - Shipping fee (optional, default: 0)
   * @param {number} purchaseOrderData.discountPercentage - Discount percentage (optional, default: 0, max: 100)
   * @param {number} purchaseOrderData.totalPrice - Total price (optional, default: 0)
   * @param {string} purchaseOrderData.status - Status (optional, default: pending)
   * @param {string} purchaseOrderData.paymentStatus - Payment status (optional, default: unpaid)
   * @param {string} purchaseOrderData.notes - Notes (optional, max 1000 chars)
   * @returns {Promise<Object>} Created purchase order data
   */
  createPurchaseOrder: async (purchaseOrderData) => {
    try {
      const response = await api.post('/purchase-orders', purchaseOrderData)
      return response.data
    } catch (error) {
      console.error('Error creating purchase order:', error)
      throw error
    }
  },

  /**
   * Update purchase order
   * @param {string} purchaseOrderId - Purchase order ID
   * @param {Object} purchaseOrderData - Updated purchase order data
   * @param {string} purchaseOrderData.supplier - Supplier ID (optional)
   * @param {string} purchaseOrderData.orderDate - Order date (optional)
   * @param {string} purchaseOrderData.expectedDeliveryDate - Expected delivery date (optional)
   * @param {number} purchaseOrderData.shippingFee - Shipping fee (optional)
   * @param {number} purchaseOrderData.discountPercentage - Discount percentage (optional)
   * @param {number} purchaseOrderData.totalPrice - Total price (optional)
   * @param {string} purchaseOrderData.status - Status (optional)
   * @param {string} purchaseOrderData.paymentStatus - Payment status (optional)
   * @param {string} purchaseOrderData.notes - Notes (optional)
   * @returns {Promise<Object>} Updated purchase order data
   * @note Cannot update received or cancelled orders
   */
  updatePurchaseOrder: async (purchaseOrderId, purchaseOrderData) => {
    try {
      const response = await api.put(`/purchase-orders/${purchaseOrderId}`, purchaseOrderData)
      return response.data
    } catch (error) {
      console.error('Error updating purchase order:', error)
      throw error
    }
  },

  /**
   * Delete purchase order
   * @param {string} purchaseOrderId - Purchase order ID
   * @returns {Promise<Object>} Success message
   * @note Can only delete pending purchase orders with no details
   */
  deletePurchaseOrder: async (purchaseOrderId) => {
    try {
      const response = await api.delete(`/purchase-orders/${purchaseOrderId}`)
      return response.data
    } catch (error) {
      console.error('Error deleting purchase order:', error)
      throw error
    }
  },

  /**
   * Search purchase orders by PO number
   * @param {string} searchTerm - Search term (PO number)
   * @param {number} limit - Maximum results (optional, default 20)
   * @returns {Promise<Object>} Matching purchase orders
   */
  searchPurchaseOrders: async (searchTerm, limit = 20) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { search: searchTerm, limit }
      })
      return response.data
    } catch (error) {
      console.error('Error searching purchase orders:', error)
      throw error
    }
  },

  /**
   * Get purchase orders by status
   * @param {string} status - Status (pending/approved/received/cancelled)
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Purchase orders with specified status
   */
  getPurchaseOrdersByStatus: async (status, params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { status, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching purchase orders by status:', error)
      throw error
    }
  },

  /**
   * Get pending purchase orders
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Pending purchase orders
   */
  getPendingOrders: async (params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { status: 'pending', ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching pending purchase orders:', error)
      throw error
    }
  },

  /**
   * Get approved purchase orders
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Approved purchase orders
   */
  getApprovedOrders: async (params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { status: 'approved', ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching approved purchase orders:', error)
      throw error
    }
  },

  /**
   * Get received purchase orders
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Received purchase orders
   */
  getReceivedOrders: async (params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { status: 'received', ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching received purchase orders:', error)
      throw error
    }
  },

  /**
   * Get cancelled purchase orders
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Cancelled purchase orders
   */
  getCancelledOrders: async (params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { status: 'cancelled', ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching cancelled purchase orders:', error)
      throw error
    }
  },

  /**
   * Get purchase orders by payment status
   * @param {string} paymentStatus - Payment status (unpaid/partial/paid)
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Purchase orders with specified payment status
   */
  getPurchaseOrdersByPaymentStatus: async (paymentStatus, params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { paymentStatus, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching purchase orders by payment status:', error)
      throw error
    }
  },

  /**
   * Get unpaid purchase orders
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Unpaid purchase orders
   */
  getUnpaidOrders: async (params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { paymentStatus: 'unpaid', ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching unpaid purchase orders:', error)
      throw error
    }
  },

  /**
   * Get partially paid purchase orders
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Partially paid purchase orders
   */
  getPartiallyPaidOrders: async (params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { paymentStatus: 'partial', ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching partially paid purchase orders:', error)
      throw error
    }
  },

  /**
   * Get fully paid purchase orders
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Fully paid purchase orders
   */
  getPaidOrders: async (params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { paymentStatus: 'paid', ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching paid purchase orders:', error)
      throw error
    }
  },

  /**
   * Get overdue purchase orders
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Overdue purchase orders (expected delivery date passed)
   */
  getOverdueOrders: async (params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { overdue: true, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching overdue purchase orders:', error)
      throw error
    }
  },

  /**
   * Get purchase orders by supplier
   * @param {string} supplierId - Supplier ID
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Purchase orders for specified supplier
   */
  getPurchaseOrdersBySupplier: async (supplierId, params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { supplier: supplierId, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching purchase orders by supplier:', error)
      throw error
    }
  },

  /**
   * Get purchase orders by date range
   * @param {string} startDate - Start date (ISO format)
   * @param {string} endDate - End date (ISO format)
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Purchase orders within date range
   */
  getPurchaseOrdersByDateRange: async (startDate, endDate, params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { startDate, endDate, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching purchase orders by date range:', error)
      throw error
    }
  },

  /**
   * Get purchase orders with details
   * @param {Object} params - Additional query parameters (optional)
   * @returns {Promise<Object>} Purchase orders with details populated
   */
  getPurchaseOrdersWithDetails: async (params = {}) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { withDetails: true, ...params }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching purchase orders with details:', error)
      throw error
    }
  },

  /**
   * Approve purchase order
   * @param {string} purchaseOrderId - Purchase order ID
   * @returns {Promise<Object>} Updated purchase order data
   * @note Can only approve pending orders
   */
  approvePurchaseOrder: async (purchaseOrderId) => {
    try {
      const response = await api.patch(`/purchase-orders/${purchaseOrderId}/status`, {
        status: 'approved'
      })
      return response.data
    } catch (error) {
      console.error('Error approving purchase order:', error)
      throw error
    }
  },

  /**
   * Receive purchase order (mark as received)
   * @param {string} purchaseOrderId - Purchase order ID
   * @returns {Promise<Object>} Updated purchase order data
   * @note Can only receive approved orders
   */
  receivePurchaseOrder: async (purchaseOrderId) => {
    try {
      const response = await api.patch(`/purchase-orders/${purchaseOrderId}/status`, {
        status: 'received'
      })
      return response.data
    } catch (error) {
      console.error('Error receiving purchase order:', error)
      throw error
    }
  },

  /**
   * Receive purchase order with batch creation (single backend call)
   * Backend handles: create batches → stock in → link to PO details → update status
   * @param {string} purchaseOrderId - Purchase order ID
   * @param {Array} items - Array of { poDetailId, quantity, mfgDate, expiryDate, locationId, notes }
   * @returns {Promise<Object>} Updated purchase order data
   */
  receivePurchaseOrderWithBatches: async (purchaseOrderId, items) => {
    try {
      const response = await api.post(`/purchase-orders/${purchaseOrderId}/receive`, {
        items
      })
      return response.data
    } catch (error) {
      console.error('Error receiving purchase order with batches:', error)
      throw error
    }
  },

  /**
   * Cancel purchase order
   * @param {string} purchaseOrderId - Purchase order ID
   * @returns {Promise<Object>} Updated purchase order data
   * @note Can cancel pending or approved orders
   */
  cancelPurchaseOrder: async (purchaseOrderId) => {
    try {
      const response = await api.patch(`/purchase-orders/${purchaseOrderId}/status`, {
        status: 'cancelled'
      })
      return response.data
    } catch (error) {
      console.error('Error cancelling purchase order:', error)
      throw error
    }
  },

  /**
   * Update purchase order status
   * @param {string} purchaseOrderId - Purchase order ID
   * @param {string} status - New status (pending/approved/received/cancelled)
   * @returns {Promise<Object>} Updated purchase order data
   */
  updateStatus: async (purchaseOrderId, status) => {
    try {
      const response = await api.patch(`/purchase-orders/${purchaseOrderId}/status`, { status })
      return response.data
    } catch (error) {
      console.error('Error updating purchase order status:', error)
      throw error
    }
  },

  /**
   * Update purchase order payment status
   * @param {string} purchaseOrderId - Purchase order ID
   * @param {string} paymentStatus - New payment status (unpaid/partial/paid)
   * @returns {Promise<Object>} Updated purchase order data
   */
  updatePaymentStatus: async (purchaseOrderId, paymentStatus) => {
    try {
      const response = await api.patch(`/purchase-orders/${purchaseOrderId}/status`, { paymentStatus })
      return response.data
    } catch (error) {
      console.error('Error updating payment status:', error)
      throw error
    }
  },

  /**
   * Update purchase order total price
   * @param {string} purchaseOrderId - Purchase order ID
   * @param {number} totalPrice - New total price
   * @returns {Promise<Object>} Updated purchase order data
   */
  updateTotalPrice: async (purchaseOrderId, totalPrice) => {
    try {
      const response = await api.put(`/purchase-orders/${purchaseOrderId}`, { totalPrice })
      return response.data
    } catch (error) {
      console.error('Error updating total price:', error)
      throw error
    }
  },

  /**
   * Update purchase order discount
   * @param {string} purchaseOrderId - Purchase order ID
   * @param {number} discountPercentage - Discount percentage (0-100)
   * @returns {Promise<Object>} Updated purchase order data
   */
  updateDiscount: async (purchaseOrderId, discountPercentage) => {
    try {
      const response = await api.put(`/purchase-orders/${purchaseOrderId}`, { discountPercentage })
      return response.data
    } catch (error) {
      console.error('Error updating discount:', error)
      throw error
    }
  },

  /**
   * Update purchase order shipping fee
   * @param {string} purchaseOrderId - Purchase order ID
   * @param {number} shippingFee - Shipping fee
   * @returns {Promise<Object>} Updated purchase order data
   */
  updateShippingFee: async (purchaseOrderId, shippingFee) => {
    try {
      const response = await api.put(`/purchase-orders/${purchaseOrderId}`, { shippingFee })
      return response.data
    } catch (error) {
      console.error('Error updating shipping fee:', error)
      throw error
    }
  },

  /**
   * Update expected delivery date
   * @param {string} purchaseOrderId - Purchase order ID
   * @param {string} expectedDeliveryDate - Expected delivery date (ISO format)
   * @returns {Promise<Object>} Updated purchase order data
   */
  updateExpectedDeliveryDate: async (purchaseOrderId, expectedDeliveryDate) => {
    try {
      const response = await api.put(`/purchase-orders/${purchaseOrderId}`, { expectedDeliveryDate })
      return response.data
    } catch (error) {
      console.error('Error updating expected delivery date:', error)
      throw error
    }
  },

  /**
   * Update purchase order notes
   * @param {string} purchaseOrderId - Purchase order ID
   * @param {string} notes - Notes (max 1000 characters)
   * @returns {Promise<Object>} Updated purchase order data
   */
  updateNotes: async (purchaseOrderId, notes) => {
    try {
      const response = await api.put(`/purchase-orders/${purchaseOrderId}`, { notes })
      return response.data
    } catch (error) {
      console.error('Error updating notes:', error)
      throw error
    }
  },

  /**
   * Get purchase orders with pagination
   * @param {number} page - Page number
   * @param {number} limit - Items per page
   * @returns {Promise<Object>} Paginated purchase orders
   */
  getPurchaseOrdersPaginated: async (page = 1, limit = 20) => {
    try {
      const response = await api.get('/purchase-orders', {
        params: { page, limit }
      })
      return response.data
    } catch (error) {
      console.error('Error fetching paginated purchase orders:', error)
      throw error
    }
  },

  /**
   * Get purchase orders count by status
   * @returns {Promise<Object>} Count of orders by status
   */
  getOrdersCountByStatus: async () => {
    try {
      // Fetch all statuses in parallel
      const [pending, approved, received, cancelled] = await Promise.all([
        api.get('/purchase-orders', { params: { status: 'pending', limit: 0 } }),
        api.get('/purchase-orders', { params: { status: 'approved', limit: 0 } }),
        api.get('/purchase-orders', { params: { status: 'received', limit: 0 } }),
        api.get('/purchase-orders', { params: { status: 'cancelled', limit: 0 } })
      ])

      return {
        pending: pending.data.data?.pagination?.total || 0,
        approved: approved.data.data?.pagination?.total || 0,
        received: received.data.data?.pagination?.total || 0,
        cancelled: cancelled.data.data?.pagination?.total || 0
      }
    } catch (error) {
      console.error('Error fetching orders count by status:', error)
      throw error
    }
  },

  /**
   * Get purchase orders count by payment status
   * @returns {Promise<Object>} Count of orders by payment status
   */
  getOrdersCountByPaymentStatus: async () => {
    try {
      // Fetch all payment statuses in parallel
      const [unpaid, partial, paid] = await Promise.all([
        api.get('/purchase-orders', { params: { paymentStatus: 'unpaid', limit: 0 } }),
        api.get('/purchase-orders', { params: { paymentStatus: 'partial', limit: 0 } }),
        api.get('/purchase-orders', { params: { paymentStatus: 'paid', limit: 0 } })
      ])

      return {
        unpaid: unpaid.data.data?.pagination?.total || 0,
        partial: partial.data.data?.pagination?.total || 0,
        paid: paid.data.data?.pagination?.total || 0
      }
    } catch (error) {
      console.error('Error fetching orders count by payment status:', error)
      throw error
    }
  },

}

export default purchaseOrderService
