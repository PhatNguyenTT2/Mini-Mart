import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { CartProvider } from './contexts/CartContext';
import { StoreProvider, useStore } from './contexts/StoreContext';
import { Home, LoginSignup, CartPage } from './pages';
import ProductDetail from './pages/ProductDetail';
import StoreSelection from './pages/StoreSelection';
import CheckoutPage from './pages/CheckoutPage';
import OrderStatusPage from './pages/OrderStatusPage';
import OrderHistoryPage from './pages/OrderHistoryPage';
import { ChatProvider } from './contexts/ChatContext';
import { ChatWidget } from './components/ChatWidget';
import { CartDrawer } from './components/Cart/CartDrawer';
import { Toaster } from 'react-hot-toast';
import ErrorBoundary from './components/ErrorBoundary';
import './App.css';

/**
 * StoreGuard — Redirect to /select-store if no store selected.
 * Only guards "/" and product browsing routes.
 * Does NOT block /login, /register, /cart (per decision.md edge case).
 */
const StoreGuard = ({ children }) => {
  const { selectedStore, loading } = useStore();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-500" />
      </div>
    );
  }

  if (!selectedStore) {
    return <Navigate to="/select-store" replace />;
  }

  return children;
};

function App() {
  return (
    <StoreProvider>
      <AuthProvider>
        <CartProvider>
          <ChatProvider>
            <Router>
              <Toaster 
                position="top-right"
                toastOptions={{
                  duration: 3000,
                  style: {
                    background: '#fff',
                    color: '#374151',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                    borderRadius: '0.75rem',
                    padding: '16px',
                  },
                  success: {
                    iconTheme: {
                      primary: '#10b981',
                      secondary: '#fff',
                    },
                  },
                  error: {
                    iconTheme: {
                      primary: '#ef4444',
                      secondary: '#fff',
                    },
                  },
                }}
              />
              <ErrorBoundary>
                <Routes>
                  {/* Store Selection — no guard */}
                  <Route path="/select-store" element={<StoreSelection />} />

                  {/* Home — requires store selection */}
                  <Route path="/" element={<StoreGuard><Home /></StoreGuard>} />

                  {/* Product Detail — requires store selection (for batch/FEFO data) */}
                  <Route path="/product/:productId" element={<StoreGuard><ProductDetail /></StoreGuard>} />

                  {/* Auth — no guard */}
                  <Route path="/login" element={<LoginSignup />} />
                  <Route path="/register" element={<LoginSignup />} />

                  {/* Cart — no guard */}
                  <Route path="/cart" element={<CartPage />} />
                  
                  {/* Checkout — requires store selection */}
                  <Route path="/checkout" element={<StoreGuard><CheckoutPage /></StoreGuard>} />
                  
                  {/* Order Status — requires store selection */}
                  <Route path="/order-status/:orderId" element={<StoreGuard><OrderStatusPage /></StoreGuard>} />

                  {/* Order History — requires store selection */}
                  <Route path="/orders" element={<StoreGuard><OrderHistoryPage /></StoreGuard>} />
                </Routes>
              </ErrorBoundary>

              {/* Global Chat Widget — floating FAB */}
              <ChatWidget />
              
              {/* Global Cart Drawer */}
              <CartDrawer />
            </Router>
          </ChatProvider>
        </CartProvider>
      </AuthProvider>
    </StoreProvider>
  );
}

export default App;
