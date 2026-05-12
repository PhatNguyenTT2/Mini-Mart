import api from './api';

const TOKEN_KEY = 'customerToken';
const USER_KEY = 'customerUser';

const authService = {
  /**
   * Login — POST /api/auth/login
   * Backend accepts username OR email in the `username` field
   */
  async login({ username, password }) {
    const res = await api.post('/auth/login', { username, password });
    const { token, user } = res.data.data || res.data;
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
    return { token, user };
  },

  /**
   * Register Customer — POST /api/auth/register-customer
   * Creates user_account (role=Customer) + customer profile, returns JWT
   */
  async register({ fullName, username, email, password, phone, address, gender, dob }) {
    const res = await api.post('/auth/register-customer', {
      fullName, username, email, password, phone, address, gender, dob
    });
    const { token, user } = res.data.data || res.data;
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
    return { token, user };
  },

  /**
   * Get current user profile — GET /api/auth/me
   */
  async getMe() {
    const res = await api.get('/auth/me');
    return res.data.data || res.data;
  },

  /**
   * Logout — POST /api/auth/logout
   */
  async logout() {
    try {
      await api.post('/auth/logout');
    } catch {
      // Ignore errors — clear local state regardless
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },

  getSavedUser() {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  isLoggedIn() {
    return !!localStorage.getItem(TOKEN_KEY);
  }
};

export default authService;
