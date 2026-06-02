const axios = require('axios');
const logger = require('../../../../shared/common/logger');

/**
 * Internal HTTP client for Inventory Service (:3006)
 * Fetches inventory summaries for statistics aggregation
 */
class InventoryClient {
  constructor(baseURL) {
    this.api = axios.create({
      baseURL,
      timeout: 8000,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  async getSummary(token) {
    try {
      const response = await this.api.get('/api/inventory/summary', {
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data?.data || [];
    } catch (err) {
      logger.warn({ err: err.message }, 'InventoryClient.getSummary failed');
      return [];
    }
  }

  async getProductStockOutAggregated(token, filters = {}) {
    try {
      const response = await this.api.get('/api/stock-outs/stats/product-aggregates', {
        params: filters,
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data?.data?.productAggregates || [];
    } catch (err) {
      logger.warn({ err: err.message }, 'InventoryClient.getProductStockOutAggregated failed');
      return [];
    }
  }
}

module.exports = InventoryClient;
