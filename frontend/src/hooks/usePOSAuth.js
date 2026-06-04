import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import posLoginService from '../services/posLoginService';

/**
 * POS Authentication & Session Management Hook.
 * Handles login verification, session checks, logout, and clock.
 */
export function usePOSAuth() {
  const navigate = useNavigate();
  const [currentEmployee, setCurrentEmployee] = useState(null);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [loading, setLoading] = useState(true);
  const [networkError, setNetworkError] = useState(false);

  const checkAuth = async () => {
    setLoading(true);
    setNetworkError(false);

    if (!posLoginService.isLoggedIn()) {
      navigate('/pos-login');
      return;
    }

    try {
      const result = await posLoginService.verifySession();

      if (!result.success) {
        console.error('Session verification failed:', result.error);
        const code = result.error?.code;
        const isAuthError = code === 'NO_SESSION' || result.httpStatus === 401 || result.httpStatus === 403;

        if (isAuthError) {
          posLoginService.clearSession();
          navigate('/pos-login');
        } else {
          // Infrastructure/network error (502, 429, etc) -> show error UI, don't clear token
          setNetworkError(true);
        }
        return;
      }

      const employee = posLoginService.getCurrentEmployee();
      setCurrentEmployee(employee);
      setNetworkError(false);
    } catch (error) {
      console.error('Session verification error:', error);
      setNetworkError(true);
    } finally {
      setLoading(false);
    }
  };

  // Check auth on mount
  useEffect(() => {
    checkAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate]);

  // Clock tick
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Periodic session verify (5 min)
  useEffect(() => {
    const verifyInterval = setInterval(async () => {
      if (posLoginService.isLoggedIn()) {
        const result = await posLoginService.verifySession();
        if (!result.success) {
          const code = result.error?.code;
          const isAuthError = code === 'NO_SESSION' || result.httpStatus === 401 || result.httpStatus === 403;

          if (isAuthError) {
            console.error('Session expired or revoked');
            alert('Your session has expired. Please login again.');
            posLoginService.clearSession();
            navigate('/pos-login');
          } else {
            console.warn('Periodic session verification failed due to network/server issue. Keeping session active.');
          }
        }
      }
    }, 5 * 60 * 1000);
    return () => clearInterval(verifyInterval);
  }, [navigate]);

  const handleLogout = async (cartLength = 0) => {
    if (cartLength > 0) {
      if (!window.confirm('You have items in cart. Are you sure you want to logout?')) {
        return;
      }
    }

    try {
      await posLoginService.logout();
      navigate('/pos-login');
    } catch (error) {
      console.error('Logout error:', error);
      navigate('/pos-login');
    }
  };

  const retryAuth = async () => {
    await checkAuth();
  };

  return {
    currentEmployee,
    currentTime,
    loading,
    setLoading,
    networkError,
    retryAuth,
    handleLogout
  };
}