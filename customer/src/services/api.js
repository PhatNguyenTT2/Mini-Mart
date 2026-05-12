import axios from 'axios'

// Use relative URL — works with Vite proxy in dev, same origin in production
const baseURL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add token to requests if available (for authenticated customer actions)
api.interceptors.request.use(
  (config) => {
    if (config.headers.Authorization) {
      return config;
    }

    const token = localStorage.getItem('customerToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
)

// Handle response: normalize format + errors
api.interceptors.response.use(
  (response) => {
    // Normalize: backend may return { status: 'success' } or { success: true }
    if (response.data && response.data.status === 'success' && response.data.success === undefined) {
      response.data.success = true;
    }
    return response;
  },
  async (error) => {
    const config = error.config;

    // Auto-retry on 429 Too Many Requests (rate limit)
    if (error.response?.status === 429) {
      config.__retryCount = config.__retryCount || 0;
      if (config.__retryCount < 3) {
        config.__retryCount += 1;
        const backoff = Math.pow(2, config.__retryCount - 1) * 1000;
        await new Promise(r => setTimeout(r, backoff));
        return api(config);
      }
    }

    return Promise.reject(error)
  }
)

export default api
