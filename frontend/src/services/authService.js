import api from './api'
import chatSocketService from './chatSocketService'

const authService = {
  // Login
  login: async (username, password) => {
    try {
      const response = await api.post('/auth/login', { username, password })

      if (response.data.success) {
        const { token, user } = response.data.data
        localStorage.setItem('adminToken', token)
        localStorage.setItem('adminUser', JSON.stringify(user))
        return { success: true, user, token }
      }

      return { success: false, error: 'Login failed' }
    } catch (error) {
      throw error
    }
  },

  // Register (Trial — creates Super Admin + Store)
  register: async (userData) => {
    try {
      const { fullName, username, email, password, storeName, storeAddress, storePhone } = userData
      const response = await api.post('/auth/register-trial', {
        username,
        email,
        fullName,
        password,
        storeName,
        storeAddress: storeAddress || undefined,
        storePhone: storePhone || undefined
      })

      if (response.data.success) {
        return { success: true, message: 'Registration successful', data: response.data.data }
      }

      return { success: false, error: 'Registration failed' }
    } catch (error) {
      throw error
    }
  },

  // Logout
  logout: async () => {
    try {
      await api.post('/auth/logout')
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // Disconnect socket and clean up chat session from localStorage
      chatSocketService.disconnect()

      const token = localStorage.getItem('adminToken')
      if (token) {
        try {
          const payload = JSON.parse(atob(token.split('.')[1]))
          const uid = payload.id || payload.userId
          if (uid) {
            localStorage.removeItem(`posmart_chat_session_${uid}`)
          }
        } catch (e) {
          console.warn('Failed to parse token on logout cleanup', e)
        }
      }
      localStorage.removeItem('posmart_chat_session')

      localStorage.removeItem('adminToken')
      localStorage.removeItem('adminUser')
    }
  },

  // Get current user
  getCurrentUser: async () => {
    const response = await api.get('/auth/me')
    return response.data.data
  },

  // Check if user is logged in
  isAuthenticated: () => {
    return !!localStorage.getItem('adminToken')
  },

  // Get stored token
  getToken: () => {
    return localStorage.getItem('adminToken')
  },

  // Get stored user data
  getUser: () => {
    const user = localStorage.getItem('adminUser')
    return user ? JSON.parse(user) : null
  },

  // Check if user has specific permission
  hasPermission: (permission) => {
    const user = authService.getUser()
    if (!user) return false

    // Super Admin bypass — full access
    if (user.role === 'Super Admin') return true

    const permissions = user.permissions || []
    return permissions.includes(permission)
  }
}

export default authService