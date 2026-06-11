import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
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

import { useEffect } from 'react';
import { useCart } from './contexts/CartContext';
import toast from 'react-hot-toast';

function CustomerChatActionHandler() {
  const { addToCart, updateQuantity, setIsCartOpen } = useCart();
  const navigate = useNavigate();

  useEffect(() => {
    const handleAction = (e) => {
      const action = e.detail;
      if (!action) return;

      switch (action.type) {
        case 'ADD_TO_CART': {
          const { productId, name, price, unitPrice, image, quantity } = action.payload || {};
          const productPrice = price || unitPrice || 0;
          if (productId) {
            addToCart({
              id: productId,
              name: name || 'Sản phẩm',
              price: productPrice,
              image: image || null
            }, quantity || 1);
          }
          break;
        }
        case 'UPDATE_CART_ITEM': {
          const { productId, quantity } = action.payload || {};
          if (productId && quantity != null) {
            updateQuantity(productId, quantity);
            toast.success('Đã cập nhật số lượng trong giỏ hàng');
          }
          break;
        }
        case 'VIEW_CART':
          setIsCartOpen(true);
          break;
        case 'NAVIGATE': {
          const path = action.payload?.path || action.payload;
          if (path) navigate(path);
          break;
        }
        case 'CREATE_ORDER': {
          toast.success('Đơn hàng của bạn đã được tạo thành công qua trợ lý ảo!');
          const orderId = action.payload?.orderId || action.payload?.id;
          if (orderId) {
            navigate(`/orders/${orderId}`);
          } else {
            navigate('/orders');
          }
          break;
        }
        case 'CANCEL_ORDER':
          toast.success(action.payload?.message || 'Đơn hàng đã được hủy thành công');
          break;
        default:
          break;
      }
    };

    window.addEventListener('posmart:customer_chat_action', handleAction);
    return () => window.removeEventListener('posmart:customer_chat_action', handleAction);
  }, [addToCart, updateQuantity, setIsCartOpen, navigate]);

  return null;
}

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
              <CustomerChatActionHandler />
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

                  {/* Order Details/Status — requires store selection */}
                  <Route path="/orders/:orderId" element={<StoreGuard><OrderStatusPage /></StoreGuard>} />

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
