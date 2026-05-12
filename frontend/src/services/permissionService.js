import api from './api';

const permissionService = {
  // Get all available permissions from auth microservice
  getPermissions: async () => {
    try {
      const response = await api.get('/permissions');
      // Auth service returns { success: true, data: { permissions: ["code1", ...] } }
      return response.data;
    } catch (error) {
      console.error('Error fetching permissions:', error);
      throw error;
    }
  }
};

export default permissionService;

