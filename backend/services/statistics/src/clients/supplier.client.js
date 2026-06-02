const axios = require('axios');
const logger = require('../../../../shared/common/logger');

/**
 * Internal HTTP client for Supplier Service (:3005)
 * Fetches purchase orders and purchase details for statistics aggregation
 */
class SupplierClient {
  constructor(baseURL) {
    this.api = axios.create({
      baseURL,
      timeout: 8000,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  async getPurchaseOrders(token, filters = {}) {
    try {
      const params = {};
      if (filters.status) params.status = filters.status;
      if (filters.paymentStatus) params.paymentStatus = filters.paymentStatus;
      if (filters.startDate) params.startDate = filters.startDate;
      if (filters.endDate) params.endDate = filters.endDate;

      const response = await this.api.get('/api/purchase-orders', {
        params,
        headers: { Authorization: `Bearer ${token}` }
      });

      return response.data.data || [];
    } catch (err) {
      logger.warn({ err: err.message }, 'SupplierClient.getPurchaseOrders failed');
      return [];
    }
  }

  async getPurchaseOrderById(token, poId) {
    try {
      const response = await this.api.get(`/api/purchase-orders/${poId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data.data || null;
    } catch (err) {
      logger.warn({ err: err.message, poId }, 'SupplierClient.getPurchaseOrderById failed');
      return null;
    }
  }

  // Bounded Parallelism: fetch POs WITH details in chunks
  async getPurchaseOrdersWithDetails(token, filters = {}) {
    const pos = await this.getPurchaseOrders(token, filters);
    const CHUNK_SIZE = 20;
    for (let i = 0; i < pos.length; i += CHUNK_SIZE) {
      const chunk = pos.slice(i, i + CHUNK_SIZE);
      const details = await Promise.all(
        chunk.map(po => this.getPurchaseOrderById(token, po.id))
      );
      chunk.forEach((po, idx) => {
        po.details = details[idx]?.details || [];
      });
    }
    return pos;
  }

  // SQL-level aggregation (OOM mitigation helper)
  async getProductCostsAggregated(token, { startDate, endDate }) {
    try {
      const response = await this.api.get('/api/purchase-orders/stats/product-costs', {
        params: { startDate, endDate },
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data.data?.productCosts || [];
    } catch (err) {
      logger.warn({ err: err.message }, 'SupplierClient.getProductCostsAggregated failed');
      return [];
    }
  }
}

module.exports = SupplierClient;
