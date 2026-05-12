import api from './api';

const posAuthService = {
  getAllPOSAccess: async (params = {}) => {
    try {
      const response = await api.get('/pos-auth', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching POS access:', error);
      return {
        success: false,
        error: error.response?.data?.error?.message || error.message
      };
    }
  },

  getAvailableEmployees: async (params = {}) => {
    try {
      const response = await api.get('/pos-auth/available-employees', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching available employees:', error);
      return {
        success: false,
        error: error.response?.data?.error?.message || error.message
      };
    }
  },

  getPOSAuthStatus: async (employeeId) => {
    try {
      const response = await api.get(`/pos-auth/${employeeId}`);
      return response.data;
    } catch (error) {
      console.error('Error fetching POS auth status:', error);
      return {
        success: false,
        error: error.response?.data?.error?.message || error.message
      };
    }
  },

  grantPOSAccess: async (employeeId, pin) => {
    try {
      const response = await api.post('/pos-auth', { employeeId, pin });
      return response.data;
    } catch (error) {
      console.error('Error granting POS access:', error);
      return {
        success: false,
        error: error.response?.data?.error?.message || error.message
      };
    }
  },

  updatePIN: async (employeeId, pin) => {
    try {
      const response = await api.put(`/pos-auth/${employeeId}/pin`, { pin });
      return response.data;
    } catch (error) {
      console.error('Error updating PIN:', error);
      return {
        success: false,
        error: error.response?.data?.error?.message || error.message
      };
    }
  },

  enablePOSAccess: async (employeeId) => {
    try {
      const response = await api.put(`/pos-auth/${employeeId}/enable`);
      return response.data;
    } catch (error) {
      console.error('Error enabling POS access:', error);
      return {
        success: false,
        error: error.response?.data?.error?.message || error.message
      };
    }
  },

  disablePOSAccess: async (employeeId) => {
    try {
      const response = await api.put(`/pos-auth/${employeeId}/disable`);
      return response.data;
    } catch (error) {
      console.error('Error disabling POS access:', error);
      return {
        success: false,
        error: error.response?.data?.error?.message || error.message
      };
    }
  },

  resetFailedAttempts: async (employeeId) => {
    try {
      const response = await api.post(`/pos-auth/${employeeId}/reset-attempts`);
      return response.data;
    } catch (error) {
      console.error('Error resetting failed attempts:', error);
      return {
        success: false,
        error: error.response?.data?.error?.message || error.message
      };
    }
  },

  revokePOSAccess: async (employeeId) => {
    try {
      const response = await api.delete(`/pos-auth/${employeeId}`);
      return response.data;
    } catch (error) {
      console.error('Error revoking POS access:', error);
      return {
        success: false,
        error: error.response?.data?.error?.message || error.message
      };
    }
  },

  getLockedAccounts: async () => {
    try {
      const response = await api.get('/pos-auth/status/locked');
      return response.data;
    } catch (error) {
      console.error('Error fetching locked accounts:', error);
      return {
        success: false,
        error: error.response?.data?.error?.message || error.message
      };
    }
  },

  verifyPIN: async (employeeId, pin) => {
    try {
      const response = await api.post('/pos-auth/verify-pin', { employeeId, pin });
      return response.data;
    } catch (error) {
      console.error('Error verifying PIN:', error);
      return {
        success: false,
        error: error.response?.data?.error?.message || error.message
      };
    }
  }
};

export default posAuthService;
