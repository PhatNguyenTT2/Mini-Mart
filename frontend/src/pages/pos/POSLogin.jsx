import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import posLoginService from '../../services/posLoginService';

export const POSLogin = () => {
  const navigate = useNavigate();
  const [employeeId, setEmployeeId] = useState('');
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [attemptsRemaining, setAttemptsRemaining] = useState(null);
  const [minutesLocked, setMinutesLocked] = useState(null);

  // Check if already logged in
  useEffect(() => {
    if (posLoginService.isLoggedIn()) {
      navigate('/pos');
    }
  }, [navigate]);

  // Clear error when employeeId changes
  useEffect(() => {
    if (error) {
      setError('');
      setAttemptsRemaining(null);
      setMinutesLocked(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employeeId]);

  // Handle employee ID input — digits only
  const handleEmployeeIdChange = (value) => {
    const digits = value.replace(/\D/g, '');
    setEmployeeId(digits);
  };

  // Handle number pad click
  const handleNumberClick = (num) => {
    if (pin.length < 6) {
      setPin(pin + num);
    }
  };

  // Handle backspace
  const handleBackspace = () => {
    setPin(pin.slice(0, -1));
  };

  // Handle clear
  const handleClear = () => {
    setPin('');
  };

  // Handle login
  const handleLogin = async (e) => {
    e.preventDefault();

    if (!employeeId.trim()) {
      setError('Please enter your Employee ID');
      return;
    }

    if (pin.length < 4) {
      setError('PIN must be at least 4 digits');
      return;
    }

    if (pin.length > 6) {
      setError('PIN must be at most 6 digits');
      return;
    }

    setLoading(true);
    setError('');
    setAttemptsRemaining(null);
    setMinutesLocked(null);

    try {
      const response = await posLoginService.login(employeeId, pin);

      if (response.success) {
        navigate('/pos');
      } else {
        const errorData = response.error;

        if (typeof errorData === 'object') {
          if (errorData.code === 'INVALID_PIN') {
            const remaining = errorData.attemptsRemaining !== undefined ? errorData.attemptsRemaining : null;
            setAttemptsRemaining(remaining);

            if (remaining !== null && remaining > 0) {
              setError(`Incorrect PIN. You have ${remaining} attempt${remaining !== 1 ? 's' : ''} remaining.`);
            } else if (remaining === 0) {
              setError('Incorrect PIN. Your account will be locked on next failed attempt.');
            } else {
              setError(errorData.message || 'Invalid PIN');
            }
          } else if (errorData.code === 'PIN_LOCKED' && errorData.minutesLeft) {
            setMinutesLocked(errorData.minutesLeft);
            setError(errorData.message || `Account locked for ${errorData.minutesLeft} minutes`);
          } else if (errorData.code === 'UNAUTHORIZED') {
            setError(errorData.message || 'Invalid Employee ID or PIN. Please check and try again.');
          } else {
            setError(errorData.message || 'Login failed');
          }
        } else {
          setError(errorData || 'Login failed');
        }

        setPin('');
      }
    } catch (err) {
      console.error('Login error:', err);
      if (err.response?.status === 404) {
        setError('Service unavailable. Please contact system administrator.');
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
      setPin('');
    } finally {
      setLoading(false);
    }
  };

  // Number pad buttons
  const numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'];

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-emerald-100 flex items-center justify-center p-4 animate-fade-in-smooth">
      {/* Back to Admin Login Button */}
      <button
        onClick={() => navigate('/')}
        className="fixed top-6 left-6 flex items-center gap-2 px-4 py-2 bg-white text-emerald-600 rounded-lg shadow-lg hover:shadow-xl hover:bg-emerald-50 transition-all group"
        title="Back to Admin Login"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="group-hover:-translate-x-1 transition-transform"
        >
          <path
            d="M19 12H5M5 12L12 19M5 12L12 5"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span className="text-[14px] font-semibold font-['Poppins',sans-serif]">
          Admin Login
        </span>
      </button>

      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
        {/* Header */}
        <div className="bg-emerald-600 text-white p-6 text-center">
          <div className="flex items-center justify-center mb-2">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="2" />
              <path d="M3 10h18" stroke="currentColor" strokeWidth="2" />
              <circle cx="7" cy="15" r="1" fill="currentColor" />
            </svg>
          </div>
          <h1 className="text-[24px] font-bold font-['Poppins',sans-serif]">
            POS System
          </h1>
          <p className="text-[14px] font-['Poppins',sans-serif] text-emerald-100 mt-1">
            Enter your credentials to continue
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleLogin} className="p-6">
          {/* Error Message */}
          {error && (
            <div className={`mb-4 p-4 rounded-lg border-2 ${attemptsRemaining !== null && attemptsRemaining <= 1
              ? 'bg-orange-50 border-orange-300'
              : minutesLocked !== null
                ? 'bg-red-50 border-red-300'
                : 'bg-red-50 border-red-200'
              }`}>
              <div className="flex items-start gap-3">
                <svg
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                  className="flex-shrink-0 mt-0.5"
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="10"
                    stroke={attemptsRemaining !== null && attemptsRemaining <= 1 ? "#F97316" : "#EF4444"}
                    strokeWidth="2"
                  />
                  <path
                    d="M12 8v4M12 16h.01"
                    stroke={attemptsRemaining !== null && attemptsRemaining <= 1 ? "#F97316" : "#EF4444"}
                    strokeWidth="2"
                    strokeLinecap="round"
                  />
                </svg>
                <div className="flex-1">
                  <span className={`text-[14px] font-semibold font-['Poppins',sans-serif] block ${attemptsRemaining !== null && attemptsRemaining <= 1
                    ? 'text-orange-800'
                    : 'text-red-800'
                    }`}>
                    {error}
                  </span>

                  {/* Warning for low attempts */}
                  {attemptsRemaining !== null && attemptsRemaining > 0 && attemptsRemaining <= 2 && (
                    <div className="mt-2 p-2 bg-orange-100 rounded border border-orange-200">
                      <span className="text-[12px] font-medium font-['Poppins',sans-serif] text-orange-900 flex items-center gap-1">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                          <path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                        Warning: Only {attemptsRemaining} attempt{attemptsRemaining !== 1 ? 's' : ''} left before account lock!
                      </span>
                    </div>
                  )}

                  {/* Lock notification */}
                  {minutesLocked !== null && (
                    <div className="mt-2 p-2 bg-red-100 rounded border border-red-200">
                      <span className="text-[12px] font-medium font-['Poppins',sans-serif] text-red-900 flex items-center gap-1">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                          <rect x="5" y="11" width="14" height="10" rx="2" stroke="currentColor" strokeWidth="2" />
                          <path d="M8 11V7a4 4 0 018 0v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                        </svg>
                        Account locked. Try again in {minutesLocked} minute{minutesLocked !== 1 ? 's' : ''}.
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Employee ID Input */}
          <div className="mb-4">
            <label className="block text-[14px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-2">
              Employee ID
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="text-gray-400">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <circle cx="12" cy="7" r="4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <input
                type="text"
                inputMode="numeric"
                value={employeeId}
                onChange={(e) => handleEmployeeIdChange(e.target.value)}
                placeholder="Enter your ID number"
                disabled={loading}
                className="w-full pl-11 pr-4 py-3 border-2 border-gray-300 rounded-lg text-[16px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                autoFocus
              />
            </div>
            <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
              Enter your numeric employee ID
            </p>
          </div>

          {/* PIN Input */}
          <div className="mb-4">
            <label className="block text-[14px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-2">
              PIN (4-6 digits)
            </label>
            <div className="relative">
              <input
                type="password"
                value={pin}
                readOnly
                placeholder="Enter PIN"
                disabled={loading}
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg text-[24px] font-['Poppins',sans-serif] tracking-[0.5em] text-center focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <div className="absolute inset-y-0 right-3 flex items-center gap-2">
                {pin.length > 0 && !loading && (
                  <button
                    type="button"
                    onClick={handleClear}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                    title="Clear"
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
            <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif] text-right">
              {pin.length}/6
            </p>
          </div>

          {/* Number Pad */}
          <div className="grid grid-cols-3 gap-2 mb-4">
            {numbers.map((num) => (
              <button
                key={num}
                type="button"
                onClick={() => handleNumberClick(num)}
                disabled={loading || minutesLocked !== null}
                className="h-16 bg-gray-100 hover:bg-gray-200 active:bg-gray-300 disabled:bg-gray-50 disabled:cursor-not-allowed disabled:text-gray-400 rounded-lg text-[24px] font-semibold font-['Poppins',sans-serif] text-gray-800 transition-colors"
              >
                {num}
              </button>
            ))}
            <button
              type="button"
              onClick={handleBackspace}
              disabled={loading || minutesLocked !== null}
              className="h-16 bg-gray-100 hover:bg-gray-200 active:bg-gray-300 disabled:bg-gray-50 disabled:cursor-not-allowed rounded-lg flex items-center justify-center transition-colors col-start-3"
              title="Backspace"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className={minutesLocked !== null ? 'text-gray-400' : 'text-gray-800'}>
                <path d="M9 9l6 6M15 9l-6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          </div>

          {/* Login Button */}
          <button
            type="submit"
            disabled={loading || !employeeId || pin.length < 4 || minutesLocked !== null}
            className="w-full py-4 bg-emerald-600 hover:bg-emerald-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg text-[16px] font-bold font-['Poppins',sans-serif] transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Logging in...
              </>
            ) : minutesLocked !== null ? (
              `Locked for ${minutesLocked} minute${minutesLocked !== 1 ? 's' : ''}`
            ) : (
              'Login to POS'
            )}
          </button>

          {/* Help Text */}
          <p className="text-center text-[12px] font-['Poppins',sans-serif] text-gray-500 mt-4">
            Contact your manager if you forgot your PIN
          </p>
        </form>
      </div>
    </div>
  );
};
