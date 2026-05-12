import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || '/api'

const posApi = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' }
})

// Auto-attach POS token
posApi.interceptors.request.use(
  (config) => {
    if (config.headers.Authorization) return config
    const token = localStorage.getItem('posToken')
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error)
)

// Response: normalize + POS-specific error handling
posApi.interceptors.response.use(
  (response) => {
    if (response.data?.status === 'success' && response.data.success === undefined) {
      response.data.success = true
    }
    return response
  },
  async (error) => {
    const config = error.config

    // Auto-retry on 429 (rate limit)
    if (error.response?.status === 429) {
      config.__retryCount = config.__retryCount || 0
      if (config.__retryCount < 3) {
        config.__retryCount += 1
        const backoff = Math.pow(2, config.__retryCount - 1) * 1000
        console.warn(`POS rate limited, retrying in ${backoff}ms (${config.__retryCount}/3)`)
        await new Promise(r => setTimeout(r, backoff))
        return posApi(config)
      }
    }

    // POS-specific 401 handling
    if (error.response?.status === 401) {
      const url = error.config?.url || ''
      const isLoginRequest = url.includes('/auth/pos') || url.includes('/pos-login')

      if (!isLoginRequest) {
        localStorage.removeItem('posToken')
        localStorage.removeItem('posEmployee')
        window.location.href = '/pos-login'
      }
    }

    return Promise.reject(error)
  }
)

export default posApi
