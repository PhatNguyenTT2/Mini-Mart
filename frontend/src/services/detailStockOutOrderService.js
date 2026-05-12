import api from './api';

/**
 * Detail Stock Out Order Service
 * Uses shared api instance (baseURL = '/api')
 * Handles all API calls for detail stock out order management
 */

const API_PATH = '/detail-stock-out-orders';

/**
 * Get all detail stock out orders with optional filtering
 * @param {Object} filters - Filter parameters
 * @returns {Promise<Array>} List of detail stock out orders
 */
export const getAllDetailStockOutOrders = async (filters = {}) => {
  try {
    const params = new URLSearchParams();

    if (filters.stockOutOrder) params.append('stockOutOrder', filters.stockOutOrder);
    if (filters.product) params.append('product', filters.product);
    if (filters.batchId) params.append('batchId', filters.batchId);
    if (filters.minQuantity) params.append('minQuantity', filters.minQuantity);
    if (filters.maxQuantity) params.append('maxQuantity', filters.maxQuantity);
    if (filters.minPrice) params.append('minPrice', filters.minPrice);
    if (filters.maxPrice) params.append('maxPrice', filters.maxPrice);
    if (filters.withStockOutOrder) params.append('withStockOutOrder', filters.withStockOutOrder);
    if (filters.withProduct) params.append('withProduct', filters.withProduct);
    if (filters.withBatch) params.append('withBatch', filters.withBatch);

    const queryString = params.toString();
    const url = queryString ? `${API_PATH}?${queryString}` : API_PATH;

    const response = await api.get(url);
    return response.data;
  } catch (error) {
    console.error('Error fetching detail stock out orders:', error);
    throw error;
  }
};

/**
 * Get single detail stock out order by ID
 * @param {string} id - Detail stock out order ID
 * @returns {Promise<Object>} Detail stock out order details
 */
export const getDetailStockOutOrderById = async (id) => {
  try {
    const response = await api.get(`${API_PATH}/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching detail stock out order ${id}:`, error);
    throw error;
  }
};

/**
 * Create new detail stock out order
 * @param {Object} detailData - Detail stock out order data
 * @returns {Promise<Object>} Created detail stock out order
 */
export const createDetailStockOutOrder = async (detailData) => {
  try {
    const response = await api.post(API_PATH, detailData);
    return response.data;
  } catch (error) {
    console.error('Error creating detail stock out order:', error);
    throw error;
  }
};

/**
 * Update detail stock out order
 * @param {string} id - Detail stock out order ID
 * @param {Object} updates - Fields to update
 * @returns {Promise<Object>} Updated detail stock out order
 */
export const updateDetailStockOutOrder = async (id, updates) => {
  try {
    const response = await api.put(`${API_PATH}/${id}`, updates);
    return response.data;
  } catch (error) {
    console.error(`Error updating detail stock out order ${id}:`, error);
    throw error;
  }
};

/**
 * Delete detail stock out order
 * @param {string} id - Detail stock out order ID
 * @returns {Promise<Object>} Deletion confirmation
 */
export const deleteDetailStockOutOrder = async (id) => {
  try {
    const response = await api.delete(`${API_PATH}/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Error deleting detail stock out order ${id}:`, error);
    throw error;
  }
};

/**
 * Get detail stock out orders by stock out order ID
 * @param {string} stockOutOrderId - Stock out order ID
 * @param {Object} options - Additional options (withProduct, withBatch)
 * @returns {Promise<Array>} List of details
 */
export const getDetailsByStockOutOrder = async (stockOutOrderId, options = {}) => {
  try {
    const filters = {
      stockOutOrder: stockOutOrderId,
      withProduct: options.withProduct !== false ? 'true' : 'false',
      withBatch: options.withBatch !== false ? 'true' : 'false'
    };
    return await getAllDetailStockOutOrders(filters);
  } catch (error) {
    console.error(`Error fetching details for stock out order ${stockOutOrderId}:`, error);
    throw error;
  }
};

/**
 * Get detail stock out orders by product ID
 * @param {string} productId - Product ID
 * @param {Object} options - Additional options
 * @returns {Promise<Array>} List of details
 */
export const getDetailsByProduct = async (productId, options = {}) => {
  try {
    const filters = {
      product: productId,
      withStockOutOrder: options.withStockOutOrder === true ? 'true' : 'false',
      withBatch: options.withBatch === true ? 'true' : 'false'
    };
    return await getAllDetailStockOutOrders(filters);
  } catch (error) {
    console.error(`Error fetching details for product ${productId}:`, error);
    throw error;
  }
};

/**
 * Get detail stock out orders by batch ID
 * @param {string} batchId - Batch ID
 * @param {Object} options - Additional options
 * @returns {Promise<Array>} List of details
 */
export const getDetailsByBatch = async (batchId, options = {}) => {
  try {
    const filters = {
      batchId,
      withStockOutOrder: options.withStockOutOrder === true ? 'true' : 'false',
      withProduct: options.withProduct === true ? 'true' : 'false'
    };
    return await getAllDetailStockOutOrders(filters);
  } catch (error) {
    console.error(`Error fetching details for batch ${batchId}:`, error);
    throw error;
  }
};

/**
 * Update quantity for detail stock out order
 * @param {string} id - Detail stock out order ID
 * @param {number} quantity - New quantity
 * @returns {Promise<Object>} Updated detail
 */
export const updateQuantity = async (id, quantity) => {
  try {
    return await updateDetailStockOutOrder(id, { quantity });
  } catch (error) {
    console.error(`Error updating quantity for detail ${id}:`, error);
    throw error;
  }
};

/**
 * Update unit price for detail stock out order
 * @param {string} id - Detail stock out order ID
 * @param {number} unitPrice - New unit price
 * @returns {Promise<Object>} Updated detail
 */
export const updateUnitPrice = async (id, unitPrice) => {
  try {
    return await updateDetailStockOutOrder(id, { unitPrice });
  } catch (error) {
    console.error(`Error updating unit price for detail ${id}:`, error);
    throw error;
  }
};

/**
 * Bulk create detail stock out orders
 * @param {Array} detailsArray - Array of detail data objects
 * @returns {Promise<Array>} Array of created details
 */
export const bulkCreateDetails = async (detailsArray) => {
  try {
    const promises = detailsArray.map(detail => createDetailStockOutOrder(detail));
    return await Promise.all(promises);
  } catch (error) {
    console.error('Error bulk creating detail stock out orders:', error);
    throw error;
  }
};

/**
 * Bulk delete detail stock out orders
 * @param {Array} ids - Array of detail IDs
 * @returns {Promise<Array>} Array of deletion results
 */
export const bulkDeleteDetails = async (ids) => {
  try {
    const promises = ids.map(id => deleteDetailStockOutOrder(id));
    return await Promise.all(promises);
  } catch (error) {
    console.error('Error bulk deleting detail stock out orders:', error);
    throw error;
  }
};

/**
 * Calculate total for a detail (quantity × unitPrice)
 * @param {number} quantity - Quantity
 * @param {number} unitPrice - Unit price
 * @returns {number} Total
 */
export const calculateTotal = (quantity, unitPrice) => {
  return parseFloat((quantity * unitPrice).toFixed(2));
};

export default {
  getAllDetailStockOutOrders,
  getDetailStockOutOrderById,
  createDetailStockOutOrder,
  updateDetailStockOutOrder,
  deleteDetailStockOutOrder,
  getDetailsByStockOutOrder,
  getDetailsByProduct,
  getDetailsByBatch,
  updateQuantity,
  updateUnitPrice,
  bulkCreateDetails,
  bulkDeleteDetails,
  calculateTotal
};
