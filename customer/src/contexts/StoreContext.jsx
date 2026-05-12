import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import storeService from '../services/storeService';

const StoreContext = createContext(null);

const STORAGE_KEY = 'selectedStore';

export function StoreProvider({ children }) {
  const [stores, setStores] = useState([]);
  const [selectedStore, setSelectedStore] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);

  // Fetch stores on mount
  useEffect(() => {
    const fetchStores = async () => {
      try {
        const result = await storeService.getStores();
        const storeList = result?.data?.stores || [];
        setStores(storeList.filter(s => s.is_active !== false));
      } catch (error) {
        console.error('Failed to fetch stores:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStores();
  }, []);

  const selectStore = useCallback((store) => {
    setSelectedStore(store);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  }, []);

  const clearStore = useCallback(() => {
    setSelectedStore(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const value = {
    stores,
    selectedStore,
    loading,
    selectStore,
    clearStore,
  };

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useStore() {
  const context = useContext(StoreContext);
  if (!context) {
    throw new Error('useStore must be used within a StoreProvider');
  }
  return context;
}
