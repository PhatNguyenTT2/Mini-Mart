const axios = require('axios');
const logger = require('../../../../shared/common/logger');

/**
 * Internal HTTP client for Order Service (:3003)
 * Fetches orders and order details for statistics aggregation
 */
class OrderClient {
  constructor(baseURL) {
    this.api = axios.create({
      baseURL,
      timeout: 8000,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  async getOrders(token, filters = {}) {
    try {
      const params = {};
      if (filters.status) params.status = filters.status;
      if (filters.paymentStatus) params.paymentStatus = filters.paymentStatus;
      if (filters.startDate) params.startDate = filters.startDate;
      if (filters.endDate) params.endDate = filters.endDate;
      if (filters.createdBy) params.createdBy = filters.createdBy;

      const response = await this.api.get('/api/orders', {
        params,
        headers: { Authorization: `Bearer ${token}` }
      });

      return response.data.data?.orders || [];
    } catch (err) {
      logger.warn({ err: err.message }, 'OrderClient.getOrders failed');
      return [];
    }
  }

  async getOrderById(token, orderId) {
    try {
      const response = await this.api.get(`/api/orders/${orderId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data.data?.order || null;
    } catch (err) {
      logger.warn({ err: err.message, orderId }, 'OrderClient.getOrderById failed');
      return null;
    }
  }

  // Bounded Parallelism: fetch orders WITH details in chunks
  async getOrdersWithDetails(token, filters = {}) {
    const orders = await this.getOrders(token, filters);
    const CHUNK_SIZE = 20;
    for (let i = 0; i < orders.length; i += CHUNK_SIZE) {
      const chunk = orders.slice(i, i + CHUNK_SIZE);
      const details = await Promise.all(
        chunk.map(o => this.getOrderById(token, o.id))
      );
      chunk.forEach((order, idx) => {
        order.details = details[idx]?.details || [];
      });
    }
    return orders;
  }

  // SQL-level aggregation (OOM mitigation helper)
  async getProductSalesAggregated(token, { startDate, endDate }) {
    try {
      const response = await this.api.get('/api/orders/stats/product-sales', {
        params: { startDate, endDate },
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data.data?.productSales || [];
    } catch (err) {
      logger.warn({ err: err.message }, 'OrderClient.getProductSalesAggregated failed');
      return [];
    }
  }
}

module.exports = OrderClient;
