import api from './api';

/**
 * Location Service (Warehouse & Store Shelf)
 * Calls inventory microservice: /api/warehouse/*
 * Replaces old /api/location-masters and /api/store-locations endpoints
 */
const locationService = {
  // ==========================================
  // BLOCK OPERATIONS
  // ==========================================

  /**
   * Get all blocks (optional type filter: 'warehouse' | 'store_shelf')
   */
  getAllBlocks: async (filters = {}) => {
    try {
      const params = {};
      if (filters.type) params.type = filters.type;
      const response = await api.get('/warehouse/blocks', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching blocks:', error);
      throw error;
    }
  },

  /**
   * Get single block with locations
   */
  getBlockById: async (id) => {
    try {
      const response = await api.get(`/warehouse/blocks/${id}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching block:', error);
      throw error;
    }
  },

  /**
   * Create block with auto-generated locations
   * @param {Object} data - { name, type, rows, cols, columnGaps }
   */
  createBlock: async (data) => {
    try {
      const response = await api.post('/warehouse/blocks', data);
      return response.data;
    } catch (error) {
      console.error('Error creating block:', error);
      throw error;
    }
  },

  /**
   * Update block metadata (name, columnGaps, type)
   */
  updateBlock: async (id, data) => {
    try {
      const response = await api.put(`/warehouse/blocks/${id}`, data);
      return response.data;
    } catch (error) {
      console.error('Error updating block:', error);
      throw error;
    }
  },

  /**
   * Delete block (only if no inventory items)
   */
  deleteBlock: async (id) => {
    try {
      const response = await api.delete(`/warehouse/blocks/${id}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting block:', error);
      throw error;
    }
  },

  // ==========================================
  // LOCATION OPERATIONS
  // ==========================================

  /**
   * Get all locations (optional filters: type, blockId, isActive)
   */
  getAllLocations: async (filters = {}) => {
    try {
      const params = {};
      if (filters.type) params.type = filters.type;
      if (filters.blockId) params.blockId = filters.blockId;
      if (filters.isActive !== undefined) params.isActive = filters.isActive;
      const response = await api.get('/warehouse/locations', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching locations:', error);
      throw error;
    }
  },

  /**
   * Get location detail with inventory items
   */
  getLocationById: async (id) => {
    try {
      const response = await api.get(`/warehouse/locations/${id}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching location:', error);
      throw error;
    }
  },

  /**
   * Update location (maxCapacity, isActive)
   */
  updateLocation: async (id, data) => {
    try {
      const response = await api.put(`/warehouse/locations/${id}`, data);
      return response.data;
    } catch (error) {
      console.error('Error updating location:', error);
      throw error;
    }
  },

  /**
   * Delete location (only if empty)
   */
  deleteLocation: async (id) => {
    try {
      const response = await api.delete(`/warehouse/locations/${id}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting location:', error);
      throw error;
    }
  },

  // ==========================================
  // ASSIGN / MOVE
  // ==========================================

  /**
   * Assign inventory item to a location
   */
  assignItemToLocation: async (locationId, itemId) => {
    try {
      const response = await api.post(`/warehouse/locations/${locationId}/assign`, { itemId });
      return response.data;
    } catch (error) {
      console.error('Error assigning item to location:', error);
      throw error;
    }
  },

  /**
   * Move inventory item to another location
   */
  moveItemToLocation: async (toLocationId, itemId, reason) => {
    try {
      const response = await api.post(`/warehouse/locations/${toLocationId}/move`, { itemId, reason });
      return response.data;
    } catch (error) {
      console.error('Error moving item:', error);
      throw error;
    }
  },

  /**
   * Get unassigned inventory items (no location, with stock) grouped by product
   */
  getUnassignedItems: async () => {
    try {
      const response = await api.get('/warehouse/locations/unassigned-items');
      return response.data;
    } catch (error) {
      console.error('Error fetching unassigned items:', error);
      throw error;
    }
  },

  /**
   * Get blocks with product details inside their locations
   */
  getStoreMapData: async (filters = {}) => {
    try {
      const params = {};
      if (filters.type) params.type = filters.type;
      const response = await api.get('/warehouse/store-map-data', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching store map data:', error);
      throw error;
    }
  }
};

export default locationService;
