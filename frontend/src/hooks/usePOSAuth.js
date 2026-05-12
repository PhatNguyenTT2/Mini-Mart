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

  // Check auth on mount
  useEffect(() => {
    const checkAuth = async () => {
      setLoading(true);

      if (!posLoginService.isLoggedIn()) {
        navigate('/pos-login');
        return;
      }

      try {
        const result = await posLoginService.verifySession();

        if (!result.success) {
          console.error('Session verification failed:', result.error);
          navigate('/pos-login');
          return;
        }

        const employee = posLoginService.getCurrentEmployee();
        setCurrentEmployee(employee);
      } catch (error) {
        console.error('Session verification error:', error);
        navigate('/pos-login');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
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
          console.error('Session expired or revoked');
          alert('Your session has expired. Please login again.');
          navigate('/pos-login');
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

  return {
    currentEmployee,
    currentTime,
    loading,
    setLoading,
    handleLogout
  };
}