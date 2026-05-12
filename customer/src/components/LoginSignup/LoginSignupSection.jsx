import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export default function LoginSection() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, register, isLoggedIn } = useAuth();

  const [activeTab, setActiveTab] = useState('login');
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [gender, setGender] = useState('');
  const [dob, setDob] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isForgotModalOpen, setIsForgotModalOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotStatus, setForgotStatus] = useState('');

  const searchParams = new URLSearchParams(location.search);
  const redirectParam = searchParams.get('redirect');
  const finalRedirect = (redirectParam && redirectParam.startsWith('/') && !redirectParam.startsWith('//')) 
    ? redirectParam 
    : '/';

  // Redirect if already logged in
  useEffect(() => {
    if (isLoggedIn) {
      navigate(finalRedirect, { replace: true });
    }
  }, [isLoggedIn, navigate, finalRedirect]);

  useEffect(() => {
    if (location.pathname === '/register') {
      setActiveTab('register');
    } else {
      setActiveTab('login');
    }
  }, [location.pathname]);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setError('');
    navigate(tab === 'login' ? '/login' : '/register');
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login({ username: email, password });
      navigate(finalRedirect, { replace: true });
    } catch (err) {
      const msg = err.response?.data?.error?.message
        || err.response?.data?.message
        || 'Login failed. Please check again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password.length < 6) {
      setError('Password must be at least 6 characters long.');
      return;
    }

    setLoading(true);
    try {
      await register({ fullName, username, email, password, phone, address, gender, dob });
      navigate(finalRedirect, { replace: true });
    } catch (err) {
      const msg = err.response?.data?.error?.message
        || err.response?.data?.message
        || 'Registration failed. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = (e) => {
    e.preventDefault();
    if (!forgotEmail) return;
    setForgotStatus('sending');
    setTimeout(() => {
      setForgotStatus('sent');
    }, 1500);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 lg:px-8 py-16">
      <div className="max-w-md mx-auto bg-white rounded-xl border border-gray-200 shadow-sm p-8">
        {/* Tab Headers */}
        <div className="flex justify-center gap-8 mb-6 border-b border-gray-200">
          <button
            onClick={() => handleTabChange('login')}
            className={`font-bold text-2xl pb-3 transition-colors ${
              activeTab === 'login'
                ? 'text-emerald-600 border-b-2 border-emerald-600'
                : 'text-gray-400'
            }`}
          >
            Login
          </button>
          <button
            onClick={() => handleTabChange('register')}
            className={`font-bold text-2xl pb-3 transition-colors ${
              activeTab === 'register'
                ? 'text-emerald-600 border-b-2 border-emerald-600'
                : 'text-gray-400'
            }`}
          >
            Register
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
            {error}
          </div>
        )}

        {/* Login Form */}
        {activeTab === 'login' && (
          <div>
            <p className="text-gray-500 text-sm text-center mb-6">
              Login with your email or username.
            </p>

            <form className="space-y-5" onSubmit={handleLoginSubmit}>
              <div>
                <label className="text-gray-700 text-sm block mb-2">
                  Email or Username <span className="text-emerald-500">*</span>
                </label>
                <input
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-12 px-4 border border-gray-200 rounded-lg text-sm text-gray-700 focus:border-emerald-500 focus:outline-none transition-colors"
                  placeholder="Enter email or username"
                  required
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-gray-700 text-sm block">
                    Password <span className="text-emerald-500">*</span>
                  </label>
                  <button 
                    type="button"
                    onClick={() => setIsForgotModalOpen(true)}
                    className="text-emerald-600 text-xs font-semibold hover:text-emerald-700 hover:underline"
                  >
                    Forgot Password?
                  </button>
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-12 px-4 border border-gray-200 rounded-lg text-sm text-gray-700 focus:border-emerald-500 focus:outline-none transition-colors"
                  placeholder="Enter password"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full h-12 bg-emerald-500 text-white font-bold rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Logging in...' : 'Login'}
              </button>
            </form>

            <p className="text-gray-500 text-sm text-center mt-6">
              Don't have an account?{' '}
              <button onClick={() => handleTabChange('register')} className="text-emerald-600 hover:underline font-medium">
                Register now
              </button>
            </p>
          </div>
        )}

        {/* Register Form */}
        {activeTab === 'register' && (
          <div>
            <p className="text-gray-500 text-sm text-center mb-6">
              Create an account to track your orders and receive offers.
            </p>

            <form className="space-y-5" onSubmit={handleRegisterSubmit}>
              <div>
                <label className="text-gray-700 text-sm block mb-2">
                  Full Name <span className="text-emerald-500">*</span>
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full h-12 px-4 border border-gray-200 rounded-lg text-sm text-gray-700 focus:border-emerald-500 focus:outline-none transition-colors"
                  placeholder="Enter full name"
                  required
                />
              </div>

              <div>
                <label className="text-gray-700 text-sm block mb-2">
                  Username <span className="text-emerald-500">*</span>
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full h-12 px-4 border border-gray-200 rounded-lg text-sm text-gray-700 focus:border-emerald-500 focus:outline-none transition-colors"
                  placeholder="Choose a username"
                  required
                />
              </div>

              <div>
                <label className="text-gray-700 text-sm block mb-2">
                  Email <span className="text-emerald-500">*</span>
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-12 px-4 border border-gray-200 rounded-lg text-sm text-gray-700 focus:border-emerald-500 focus:outline-none transition-colors"
                  placeholder="Enter email address"
                  required
                />
              </div>

              <div>
                <label className="text-gray-700 text-sm block mb-2">
                  Phone Number
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full h-12 px-4 border border-gray-200 rounded-lg text-sm text-gray-700 focus:border-emerald-500 focus:outline-none transition-colors"
                  placeholder="Enter phone number (optional)"
                />
              </div>

              <div>
                <label className="text-gray-700 text-sm block mb-2">
                  Address
                </label>
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="w-full h-12 px-4 border border-gray-200 rounded-lg text-sm text-gray-700 focus:border-emerald-500 focus:outline-none transition-colors"
                  placeholder="Enter shipping address (optional)"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-gray-700 text-sm block mb-2">
                    Gender
                  </label>
                  <select
                    value={gender}
                    onChange={(e) => setGender(e.target.value)}
                    className="w-full h-12 px-4 border border-gray-200 rounded-lg text-sm text-gray-700 focus:border-emerald-500 focus:outline-none transition-colors bg-white"
                  >
                    <option value="">-- Select --</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </div>

                <div>
                  <label className="text-gray-700 text-sm block mb-2">
                    Date of Birth
                  </label>
                  <input
                    type="date"
                    value={dob}
                    onChange={(e) => setDob(e.target.value)}
                    className="w-full h-12 px-4 border border-gray-200 rounded-lg text-sm text-gray-700 focus:border-emerald-500 focus:outline-none transition-colors"
                  />
                </div>
              </div>

              <div>
                <label className="text-gray-700 text-sm block mb-2">
                  Password <span className="text-emerald-500">*</span>
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-12 px-4 border border-gray-200 rounded-lg text-sm text-gray-700 focus:border-emerald-500 focus:outline-none transition-colors"
                  placeholder="Create a password (min 6 characters)"
                  required
                  minLength={6}
                />
              </div>

              <div className="bg-gray-50 p-4 rounded-lg">
                <p className="text-gray-500 text-xs leading-5">
                  Your personal data will be used to support your experience throughout this website, to manage access to your account, and for other purposes described in our privacy policy.
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full h-12 bg-emerald-500 text-white font-bold rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Creating account...' : 'Register'}
              </button>
            </form>

            <p className="text-gray-500 text-sm text-center mt-6">
              Already have an account?{' '}
              <button onClick={() => handleTabChange('login')} className="text-emerald-600 hover:underline font-medium">
                Login
              </button>
            </p>
          </div>
        )}
      </div>

      {/* Forgot Password Modal */}
      {isForgotModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm">
          <div className="bg-white rounded-2xl w-full max-w-md p-6 shadow-xl">
            <h3 className="text-xl font-bold text-gray-800 mb-2">Reset Password</h3>
            
            {forgotStatus === 'sent' ? (
              <div className="text-center py-6">
                <div className="w-16 h-16 bg-emerald-100 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
                </div>
                <h4 className="text-lg font-bold text-gray-800 mb-2">Check your email</h4>
                <p className="text-gray-500 text-sm mb-6">We've sent password reset instructions to your email address.</p>
                <button
                  onClick={() => {
                    setIsForgotModalOpen(false);
                    setForgotStatus('');
                    setForgotEmail('');
                  }}
                  className="w-full bg-emerald-500 text-white font-bold h-12 rounded-xl hover:bg-emerald-600 transition-colors"
                >
                  Back to Login
                </button>
              </div>
            ) : (
              <form onSubmit={handleForgotPassword}>
                <p className="text-gray-500 text-sm mb-6">
                  Enter your email address and we'll send you a link to reset your password.
                </p>
                <div className="mb-6">
                  <label className="text-gray-700 text-sm block mb-2 font-medium">Email Address</label>
                  <input
                    type="email"
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    className="w-full h-12 px-4 border border-gray-200 rounded-lg text-sm text-gray-700 focus:border-emerald-500 focus:outline-none transition-colors"
                    placeholder="Enter your registered email"
                    required
                  />
                </div>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setIsForgotModalOpen(false)}
                    className="flex-1 bg-gray-100 text-gray-700 font-bold h-12 rounded-xl hover:bg-gray-200 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={forgotStatus === 'sending' || !forgotEmail}
                    className="flex-1 bg-emerald-500 text-white font-bold h-12 rounded-xl hover:bg-emerald-600 transition-colors disabled:opacity-50"
                  >
                    {forgotStatus === 'sending' ? 'Sending...' : 'Send Link'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
