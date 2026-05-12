import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import authService from '../services/authService';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => authService.getSavedUser());
  const [loading, setLoading] = useState(true);

  // Verify token on mount
  useEffect(() => {
    const verify = async () => {
      if (!authService.isLoggedIn()) {
        setLoading(false);
        return;
      }
      try {
        const me = await authService.getMe();
        setUser(me);
        // Sync full profile to localStorage
        localStorage.setItem('customerUser', JSON.stringify(me));
      } catch {
        // Token expired or invalid
        await authService.logout();
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    verify();
  }, []);

  const login = useCallback(async (credentials) => {
    const { user: userData } = await authService.login(credentials);
    setUser(userData);
    return userData;
  }, []);

  const register = useCallback(async (data) => {
    const { user: userData } = await authService.register(data);
    setUser(userData);
    return userData;
  }, []);

  const logout = useCallback(async () => {
    await authService.logout();
    setUser(null);
  }, []);

  const value = {
    user,
    loading,
    isLoggedIn: !!user,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
