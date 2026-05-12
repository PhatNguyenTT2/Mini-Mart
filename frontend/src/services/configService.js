/**
 * Configuration Service
 * 
 * Fetches and caches runtime configuration from backend API.
 * This eliminates hardcoded environment variables and enables
 * dynamic configuration for production deployments.
 */

import axios from 'axios'

class ConfigService {
  constructor() {
    this.config = null
    this.loading = false
    this.error = null
    this.listeners = new Set()
  }

  /**
   * Get the base API URL for config endpoint
   */
  getBaseUrl() {
    // Try Vite env var first (for development)
    if (import.meta.env.VITE_API_BASE_URL) {
      return import.meta.env.VITE_API_BASE_URL
    }

    // Production or dev with proxy: use relative URL (empty string = same origin)
    // This works because:
    // - Dev: Vite proxy forwards /api to backend
    // - Prod: Frontend and backend are on same origin
    return ''
  }

  /**
   * Fetch configuration from backend
   * Note: Config endpoint is PUBLIC - no auth required
   * @returns {Promise<Object>} Configuration object
   */
  async fetchConfig() {
    if (this.loading) {
      // Wait for existing fetch to complete
      return new Promise((resolve, reject) => {
        const checkInterval = setInterval(() => {
          if (!this.loading) {
            clearInterval(checkInterval)
            if (this.config) {
              resolve(this.config)
            } else {
              reject(this.error || new Error('Config fetch failed'))
            }
          }
        }, 100)
      })
    }

    this.loading = true
    this.error = null

    try {
      const baseUrl = this.getBaseUrl()

      // Use axios directly without auth interceptor for public endpoint
      const response = await axios.get(`${baseUrl}/api/config`, {
        headers: {
          'Content-Type': 'application/json'
        },
        timeout: 5000 // 5 second timeout
      })

      // Config controller returns config object directly
      this.config = response.data
      this.loading = false

      console.log('[ConfigService] Configuration loaded:', {
        apiUrl: this.config.apiUrl,
        socketUrl: this.config.socketUrl,
        environment: this.config.environment,
        timestamp: this.config.timestamp
      })

      // Notify listeners
      this.notifyListeners(this.config)

      return this.config
    } catch (error) {
      this.error = error
      this.loading = false

      console.error('[ConfigService] Failed to fetch config:', error.message)

      // Return fallback config
      const fallbackConfig = this.getFallbackConfig()
      this.config = fallbackConfig

      console.warn('[ConfigService] Using fallback configuration')

      return fallbackConfig
    }
  }

  /**
   * Get fallback configuration when API is unavailable
   */
  getFallbackConfig() {
    const baseUrl = this.getBaseUrl()

    return {
      apiUrl: baseUrl,
      socketUrl: baseUrl,
      environment: import.meta.env.MODE || 'development',
      features: {
        vnpayEnabled: true,
        realTimeNotifications: true
      },
      settings: {
        notificationRefreshInterval: 300000,
        sessionTimeout: 3600000,
        toastDuration: 10000
      },
      timestamp: new Date().toISOString(),
      version: '1.0.0',
      _fallback: true
    }
  }

  /**
   * Get cached configuration
   * Fetches from API if not cached
   */
  async getConfig() {
    if (this.config) {
      return this.config
    }

    return await this.fetchConfig()
  }

  /**
   * Force refresh configuration from API
   */
  async refresh() {
    this.config = null
    return await this.fetchConfig()
  }

  /**
   * Subscribe to config changes
   */
  subscribe(callback) {
    this.listeners.add(callback)

    // Call immediately if config already loaded
    if (this.config) {
      callback(this.config)
    }

    // Return unsubscribe function
    return () => {
      this.listeners.delete(callback)
    }
  }

  /**
   * Notify all listeners of config changes
   */
  notifyListeners(config) {
    this.listeners.forEach(callback => {
      try {
        callback(config)
      } catch (error) {
        console.error('[ConfigService] Listener error:', error)
      }
    })
  }

  /**
   * Check if config is loaded
   */
  isLoaded() {
    return this.config !== null
  }

  /**
   * Get specific config value
   */
  get(path, defaultValue = undefined) {
    if (!this.config) {
      return defaultValue
    }

    const keys = path.split('.')
    let value = this.config

    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key]
      } else {
        return defaultValue
      }
    }

    return value
  }

  /**
   * Clear cached configuration
   */
  clear() {
    this.config = null
    this.error = null
    this.loading = false
  }
}

// Export singleton instance
const configService = new ConfigService()

export default configService
