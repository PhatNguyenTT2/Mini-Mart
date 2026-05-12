import api from './api';

/**
 * Stock Out Order Service
 * Backend: /api/stock-out → inventory_service:3006 (PostgreSQL)
 */
const API_PATH = '/stock-out';

const stockOutOrderService = {
  getAllStockOutOrders: async (filters = {}) => {
    try {
      const params = new URLSearchParams();
      if (filters.status) params.append('status', filters.status);
      if (filters.reason) params.append('reason', filters.reason);
      const queryString = params.toString();
      const url = queryString ? `${API_PATH}?${queryString}` : API_PATH;
      const response = await api.get(url);
      return response.data;
    } catch (error) {
      console.error('Error fetching stock out orders:', error);
      throw error;
    }
  },

  getStockOutOrderById: async (id) => {
    try {
      const response = await api.get(`${API_PATH}/${id}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching stock out order ${id}:`, error);
      throw error;
    }
  },

  /**
   * Create stock out order with items in a single request
   * @param {{ reason, destination, items: [{ batch_id, quantity, unit_price }] }} orderData
   */
  createStockOutOrder: async (orderData) => {
    try {
      const response = await api.post(API_PATH, orderData);
      return response.data;
    } catch (error) {
      console.error('Error creating stock out order:', error);
      throw error;
    }
  },

  /**
   * Update stock out order
   * Draft: full edit (header + items)
   * Pending: header only (reason, destination)
   */
  updateStockOutOrder: async (id, updates) => {
    try {
      const response = await api.put(`${API_PATH}/${id}`, updates);
      return response.data;
    } catch (error) {
      console.error(`Error updating stock out order ${id}:`, error);
      throw error;
    }
  },

  deleteStockOutOrder: async (id) => {
    try {
      const response = await api.delete(`${API_PATH}/${id}`);
      return response.data;
    } catch (error) {
      console.error(`Error deleting stock out order ${id}:`, error);
      throw error;
    }
  },

  /**
   * Update status: draft→pending→completed, or →cancelled
   */
  updateStockOutOrderStatus: async (id, status) => {
    try {
      const response = await api.put(`${API_PATH}/${id}/status`, { status });
      return response.data;
    } catch (error) {
      console.error(`Error updating stock out order status ${id}:`, error);
      throw error;
    }
  }
};

export default stockOutOrderService;
