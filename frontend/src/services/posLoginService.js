import posApi from './posApi';

const POS_TOKEN_KEY = 'posToken';
const POS_EMPLOYEE_KEY = 'posEmployee';

/**
 * POS Login Service
 * Auth-only: login, logout, session management.
 * Data operations (orders, payments, etc.) are in posDataService.js
 */
const posLoginService = {
  async login(employeeId, pin) {
    try {
      const response = await posApi.post('/auth/pos/login', {
        employeeId: parseInt(employeeId),
        pin: pin
      });

      if (response.data.success) {
        const { token, user } = response.data.data;
        this.setToken(token);
        this.setEmployee({
          id: user.id,
          username: user.username,
          fullName: user.fullName,
          phone: user.phone,
          role: user.role,
          storeId: user.storeId,
          permissions: user.permissions
        });

        return {
          success: true,
          data: { token, employee: user }
        };
      }

      return {
        success: false,
        error: response.data.error || 'Login failed'
      };
    } catch (error) {
      console.error('POS Login error:', error);

      if (error.response?.data?.error) {
        return {
          success: false,
          error: error.response.data.error
        };
      }

      if (error.response?.status === 404) {
        return {
          success: false,
          error: {
            message: 'POS login service is unavailable. Please contact administrator.',
            code: 'SERVICE_UNAVAILABLE'
          }
        };
      }

      return {
        success: false,
        error: {
          message: 'Network error. Please check your connection.',
          code: 'NETWORK_ERROR'
        }
      };
    }
  },

  async logout() {
    try {
      if (this.getToken()) {
        await posApi.post('/auth/pos/logout');
      }
      this.clearSession();
      return true;
    } catch (error) {
      console.error('POS Logout error:', error);
      this.clearSession();
      return true;
    }
  },

  async verifySession() {
    try {
      const token = this.getToken();

      if (!token) {
        return {
          success: false,
          error: { message: 'No active session', code: 'NO_SESSION' }
        };
      }

      const response = await posApi.get('/auth/pos/verify');

      if (response.data.success) {
        this.setEmployee(response.data.data.employee);
        return {
          success: true,
          data: response.data.data
        };
      }

      this.clearSession();
      return {
        success: false,
        error: response.data.error || 'Session verification failed'
      };
    } catch (error) {
      console.error('POS Verify error:', error);

      if (error.response?.status === 401 || error.response?.status === 403) {
        this.clearSession();
      }

      if (error.response?.data?.error) {
        return {
          success: false,
          error: error.response.data.error
        };
      }

      return {
        success: false,
        error: { message: 'Failed to verify session', code: 'VERIFICATION_ERROR' }
      };
    }
  },

  // ========== Storage Helpers ==========

  setToken(token) {
    localStorage.setItem(POS_TOKEN_KEY, token);
  },

  getToken() {
    return localStorage.getItem(POS_TOKEN_KEY);
  },

  setEmployee(employee) {
    localStorage.setItem(POS_EMPLOYEE_KEY, JSON.stringify(employee));
  },

  getEmployee() {
    const employee = localStorage.getItem(POS_EMPLOYEE_KEY);
    return employee ? JSON.parse(employee) : null;
  },

  clearSession() {
    localStorage.removeItem(POS_TOKEN_KEY);
    localStorage.removeItem(POS_EMPLOYEE_KEY);
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  getCurrentEmployee() {
    return this.getEmployee();
  },

  getAuthHeader() {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
};

export default posLoginService;
