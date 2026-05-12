import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import authService from '../../services/authService'

export default function LoginSignup() {
  const navigate = useNavigate()
  const [isLogin, setIsLogin] = useState(true)

  // Login form state
  const [loginData, setLoginData] = useState({
    username: '',
    password: ''
  })

  // Register form state
  const [registerData, setRegisterData] = useState({
    fullName: '',
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    storeName: '',
    storeAddress: '',
    storePhone: ''
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [rememberMe, setRememberMe] = useState(false)

  // Check if already logged in
  useEffect(() => {
    if (authService.isAuthenticated()) {
      navigate('/dashboard')
    }
  }, [navigate])

  // Handle login form change
  const handleLoginChange = (e) => {
    const { name, value } = e.target
    setLoginData(prev => ({
      ...prev,
      [name]: value
    }))
    setError('')
  }

  // Handle register form change
  const handleRegisterChange = (e) => {
    const { name, value } = e.target
    setRegisterData(prev => ({
      ...prev,
      [name]: value
    }))
    setError('')
  }

  // Switch between login and register
  const toggleMode = () => {
    setIsLogin(!isLogin)
    setError('')
    setSuccessMessage('')
    setLoginData({ username: '', password: '' })
    setRegisterData({
      fullName: '',
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      storeName: '',
      storeAddress: '',
      storePhone: ''
    })
  }

  // Handle login submit
  const handleLoginSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const result = await authService.login(loginData.username, loginData.password)

      if (result.success) {
        navigate('/dashboard')
      } else {
        setError(result.error || 'Login failed. Please try again.')
      }
    } catch (err) {
      console.error('Login error:', err)
      // Handle error from authService or axios
      if (err.response?.data?.error) {
        // Error is a string
        if (typeof err.response.data.error === 'string') {
          setError(err.response.data.error)
        } else {
          // Error is an object with message
          setError(err.response.data.error.message || err.response.data.error)
        }
      } else if (err.response?.status === 401) {
        setError('Invalid username or password')
      } else if (err.response?.status === 403) {
        setError('Account is inactive. Please contact administrator.')
      } else {
        setError('Unable to connect to server. Please try again later.')
      }
    } finally {
      setLoading(false)
    }
  }

  // Handle register submit
  const handleRegisterSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccessMessage('')
    setLoading(true)

    // Validation
    if (registerData.password.length < 6) {
      setError('Password must be at least 6 characters long')
      setLoading(false)
      return
    }

    if (registerData.password !== registerData.confirmPassword) {
      setError('Passwords do not match')
      setLoading(false)
      return
    }

    try {
      if (!registerData.storeName.trim()) {
        setError('Store name is required')
        setLoading(false)
        return
      }

      const result = await authService.register({
        fullName: registerData.fullName,
        username: registerData.username,
        email: registerData.email,
        password: registerData.password,
        storeName: registerData.storeName,
        storeAddress: registerData.storeAddress || undefined,
        storePhone: registerData.storePhone || undefined
      })

      if (result.success) {
        setSuccessMessage('Registration successful! Please login with your credentials.')
        setRegisterData({
          fullName: '',
          username: '',
          email: '',
          password: '',
          confirmPassword: '',
          storeName: '',
          storeAddress: '',
          storePhone: ''
        })
        // Switch to login after 3 seconds
        setTimeout(() => {
          setIsLogin(true)
          setSuccessMessage('')
        }, 2000)
      } else {
        setError(result.error || 'Registration failed. Please try again.')
      }
    } catch (err) {
      console.error('Registration error:', err)
      // Handle error from authService or axios
      if (err.response?.data?.error) {
        // Error is a string
        if (typeof err.response.data.error === 'string') {
          setError(err.response.data.error)
        } else {
          // Error is an object with message
          setError(err.response.data.error.message || err.response.data.error)
        }
      } else if (err.response?.status === 400) {
        setError('Invalid input. Please check your information.')
      } else if (err.response?.status === 409) {
        setError('Username or email already exists.')
      } else {
        setError('Unable to connect to server. Please try again later.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-[1440px] mx-auto px-8 py-16">
      <div className="max-w-[500px] mx-auto bg-white rounded-[15px] border border-[#ececec] shadow-sm p-8">
        {/* Tab Headers */}
        <div className="flex justify-center gap-8 mb-6 border-b border-[#ececec]">
          <button
            onClick={() => !loading && toggleMode()}
            className={`font-['Quicksand',sans-serif] font-bold text-[28px] pb-3 transition-colors ${isLogin
              ? 'text-[#3bb77e] border-b-2 border-[#3bb77e]'
              : 'text-[#7e7e7e]'
              }`}
            disabled={loading}
          >
            Login
          </button>
          <button
            onClick={() => !loading && toggleMode()}
            className={`font-['Quicksand',sans-serif] font-bold text-[28px] pb-3 transition-colors ${!isLogin
              ? 'text-[#3bb77e] border-b-2 border-[#3bb77e]'
              : 'text-[#7e7e7e]'
              }`}
            disabled={loading}
          >
            Register
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-[8px]">
            <p className="font-['Lato',sans-serif] text-red-600 text-[14px]">
              {error}
            </p>
          </div>
        )}

        {/* Success Message */}
        {successMessage && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-[8px]">
            <p className="font-['Lato',sans-serif] text-green-600 text-[14px]">
              {successMessage}
            </p>
          </div>
        )}

        {/* Login Form */}
        {isLogin ? (
          <div key="login" className="animate-fade-in-smooth">
            <p className="font-['Lato',sans-serif] text-[#7e7e7e] text-[14px] leading-[22px] mb-6 text-center">
              Sign in to access the admin dashboard and manage your store.
            </p>

            <form className="space-y-5" onSubmit={handleLoginSubmit}>
              {/* Username Field */}
              <div>
                <label className="font-['Lato',sans-serif] text-[#253d4e] text-[13px] leading-[20px] block mb-2">
                  Username <span className="text-[#3bb77e]">*</span>
                </label>
                <input
                  type="text"
                  name="username"
                  value={loginData.username}
                  onChange={handleLoginChange}
                  className="w-full h-[50px] px-4 border border-[#ececec] rounded-[8px] font-['Lato',sans-serif] text-[14px] text-[#253d4e] focus:border-[#3bb77e] focus:outline-none transition-colors"
                  placeholder="Enter your username"
                  required
                  disabled={loading}
                />
              </div>

              {/* Password Field */}
              <div>
                <label className="font-['Lato',sans-serif] text-[#253d4e] text-[13px] leading-[20px] block mb-2">
                  Password <span className="text-[#3bb77e]">*</span>
                </label>
                <input
                  type="password"
                  name="password"
                  value={loginData.password}
                  onChange={handleLoginChange}
                  className="w-full h-[50px] px-4 border border-[#ececec] rounded-[8px] font-['Lato',sans-serif] text-[14px] text-[#253d4e] focus:border-[#3bb77e] focus:outline-none transition-colors"
                  placeholder="Enter your password"
                  required
                  disabled={loading}
                />
              </div>

              {/* Remember Me & POS Login */}
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-[18px] h-[18px] border border-[#ececec] rounded-[4px] accent-[#3bb77e] cursor-pointer"
                    disabled={loading}
                  />
                  <span className="font-['Lato',sans-serif] text-[#253d4e] text-[13px]">
                    Remember me
                  </span>
                </label>
                <button
                  type="button"
                  onClick={() => navigate('/pos-login')}
                  className="font-['Lato',sans-serif] text-[#3bb77e] text-[13px] hover:underline flex items-center gap-1"
                  disabled={loading}
                  title="Login to POS Terminal"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="2" />
                    <path d="M3 10h18" stroke="currentColor" strokeWidth="2" />
                    <circle cx="7" cy="15" r="1" fill="currentColor" />
                  </svg>
                  POS Login
                </button>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full h-[50px] bg-[#3bb77e] text-white font-['Quicksand',sans-serif] font-bold text-[16px] rounded-[8px] hover:bg-[#2fa56a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Logging in...' : 'Log in'}
              </button>
            </form>
          </div>
        ) : (
          /* Register Form */
          <div key="register" className="animate-fade-in-smooth">
            <p className="font-['Lato',sans-serif] text-[#7e7e7e] text-[14px] leading-[22px] mb-6 text-center">
              Create your store and admin account to start managing your business.
            </p>

            <form className="space-y-5" onSubmit={handleRegisterSubmit}>
              {/* Store Name Field */}
              <div>
                <label className="font-['Lato',sans-serif] text-[#253d4e] text-[13px] leading-[20px] block mb-2">
                  Store Name <span className="text-[#3bb77e]">*</span>
                </label>
                <input
                  type="text"
                  name="storeName"
                  value={registerData.storeName}
                  onChange={handleRegisterChange}
                  className="w-full h-[50px] px-4 border border-[#ececec] rounded-[8px] font-['Lato',sans-serif] text-[14px] text-[#253d4e] focus:border-[#3bb77e] focus:outline-none transition-colors"
                  placeholder="Enter your store name"
                  required
                  disabled={loading}
                />
              </div>

              {/* Store Address (Optional) */}
              <div>
                <label className="font-['Lato',sans-serif] text-[#253d4e] text-[13px] leading-[20px] block mb-2">
                  Store Address
                </label>
                <input
                  type="text"
                  name="storeAddress"
                  value={registerData.storeAddress}
                  onChange={handleRegisterChange}
                  className="w-full h-[50px] px-4 border border-[#ececec] rounded-[8px] font-['Lato',sans-serif] text-[14px] text-[#253d4e] focus:border-[#3bb77e] focus:outline-none transition-colors"
                  placeholder="Store address (optional)"
                  disabled={loading}
                />
              </div>

              {/* Store Phone (Optional) */}
              <div>
                <label className="font-['Lato',sans-serif] text-[#253d4e] text-[13px] leading-[20px] block mb-2">
                  Store Phone
                </label>
                <input
                  type="tel"
                  name="storePhone"
                  value={registerData.storePhone}
                  onChange={handleRegisterChange}
                  className="w-full h-[50px] px-4 border border-[#ececec] rounded-[8px] font-['Lato',sans-serif] text-[14px] text-[#253d4e] focus:border-[#3bb77e] focus:outline-none transition-colors"
                  placeholder="Store phone (optional)"
                  disabled={loading}
                />
              </div>

              {/* Full Name Field */}
              <div>
                <label className="font-['Lato',sans-serif] text-[#253d4e] text-[13px] leading-[20px] block mb-2">
                  Full Name <span className="text-[#3bb77e]">*</span>
                </label>
                <input
                  type="text"
                  name="fullName"
                  value={registerData.fullName}
                  onChange={handleRegisterChange}
                  className="w-full h-[50px] px-4 border border-[#ececec] rounded-[8px] font-['Lato',sans-serif] text-[14px] text-[#253d4e] focus:border-[#3bb77e] focus:outline-none transition-colors"
                  placeholder="Enter your full name"
                  required
                  disabled={loading}
                />
              </div>

              {/* Username Field */}
              <div>
                <label className="font-['Lato',sans-serif] text-[#253d4e] text-[13px] leading-[20px] block mb-2">
                  Username <span className="text-[#3bb77e]">*</span>
                </label>
                <input
                  type="text"
                  name="username"
                  value={registerData.username}
                  onChange={handleRegisterChange}
                  className="w-full h-[50px] px-4 border border-[#ececec] rounded-[8px] font-['Lato',sans-serif] text-[14px] text-[#253d4e] focus:border-[#3bb77e] focus:outline-none transition-colors"
                  placeholder="Enter your username"
                  required
                  disabled={loading}
                  minLength={3}
                  maxLength={20}
                />
              </div>

              {/* Email Field */}
              <div>
                <label className="font-['Lato',sans-serif] text-[#253d4e] text-[13px] leading-[20px] block mb-2">
                  Email address <span className="text-[#3bb77e]">*</span>
                </label>
                <input
                  type="email"
                  name="email"
                  value={registerData.email}
                  onChange={handleRegisterChange}
                  className="w-full h-[50px] px-4 border border-[#ececec] rounded-[8px] font-['Lato',sans-serif] text-[14px] text-[#253d4e] focus:border-[#3bb77e] focus:outline-none transition-colors"
                  placeholder="Enter your email address"
                  required
                  disabled={loading}
                />
              </div>

              {/* Password Field */}
              <div>
                <label className="font-['Lato',sans-serif] text-[#253d4e] text-[13px] leading-[20px] block mb-2">
                  Password <span className="text-[#3bb77e]">*</span>
                </label>
                <input
                  type="password"
                  name="password"
                  value={registerData.password}
                  onChange={handleRegisterChange}
                  className="w-full h-[50px] px-4 border border-[#ececec] rounded-[8px] font-['Lato',sans-serif] text-[14px] text-[#253d4e] focus:border-[#3bb77e] focus:outline-none transition-colors"
                  placeholder="Create a password (min 6 characters)"
                  required
                  disabled={loading}
                  minLength={6}
                />
              </div>

              {/* Confirm Password Field */}
              <div>
                <label className="font-['Lato',sans-serif] text-[#253d4e] text-[13px] leading-[20px] block mb-2">
                  Confirm Password <span className="text-[#3bb77e]">*</span>
                </label>
                <input
                  type="password"
                  name="confirmPassword"
                  value={registerData.confirmPassword}
                  onChange={handleRegisterChange}
                  className="w-full h-[50px] px-4 border border-[#ececec] rounded-[8px] font-['Lato',sans-serif] text-[14px] text-[#253d4e] focus:border-[#3bb77e] focus:outline-none transition-colors"
                  placeholder="Confirm your password"
                  required
                  disabled={loading}
                  minLength={6}
                />
              </div>

              {/* Admin Role Note */}
              <div className="bg-[#def9ec] p-4 rounded-[8px] border border-[#3bb77e]/20">
                <p className="font-['Lato',sans-serif] text-[#253d4e] text-[12px] leading-[20px]">
                  <span className="font-bold text-[#3bb77e]">Owner Account:</span> This creates a Super Admin account with full access to manage your store, products, orders, employees, and all settings.
                </p>
              </div>

              {/* Privacy Policy Text */}
              <div className="bg-[#f4f6fa] p-4 rounded-[8px]">
                <p className="font-['Lato',sans-serif] text-[#7e7e7e] text-[12px] leading-[20px]">
                  Your personal data will be used to support your experience throughout this admin dashboard, to manage access to your account, and for other purposes described in our{' '}
                  <button
                    type="button"
                    className="text-[#3bb77e] hover:underline"
                    disabled={loading}
                  >
                    privacy policy
                  </button>
                  .
                </p>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full h-[50px] bg-[#3bb77e] text-white font-['Quicksand',sans-serif] font-bold text-[16px] rounded-[8px] hover:bg-[#2fa56a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Creating Account...' : 'Create Admin Account'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}