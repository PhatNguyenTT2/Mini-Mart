import React, { useState, useEffect, useCallback } from 'react';
import posDataService from '../../services/posDataService';
import {
  POSHeader,
  POSSearchBar,
  POSCategoryFilter,
  POSProductGrid,
  POSCart,
  POSPaymentModal,
  POSLoadingScreen,
  POSCustomerSelector,
  POSInvoiceModal,
  POSStoreMapModal
} from '../../components/POSMain';
import { POSBatchSelectModal } from '../../components/POSMain/POSBatchSelectModal';
import { POSHeldOrdersModal } from '../../components/POSMain/POSHeldOrdersModal';
import { POSEmployeeOrdersModal } from '../../components/POSMain/POSEmployeeOrdersModal';
import { POSInlineScanner } from '../../components/POSMain/POSInlineScanner';
import { VNPayReturnHandler } from '../../components/VNPayReturnHandler';

import { usePOSAuth } from '../../hooks/usePOSAuth';
import { usePOSCart } from '../../hooks/usePOSCart';
import { usePOSScanner } from '../../hooks/usePOSScanner';
import { usePOSOrder } from '../../hooks/usePOSOrder';
import { usePOSPayment } from '../../hooks/usePOSPayment';
import { ChatWidget } from '../../components/ChatWidget/ChatWidget';
import { useChat } from '../../contexts/ChatContext';

export const POSMain = () => {
  // ========== SHARED STATE ==========
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [products, setProducts] = useState([]);
  const [loadingProducts, setLoadingProducts] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [customerDiscounts, setCustomerDiscounts] = useState({
    guest: 0, retail: 10, wholesale: 15, vip: 20
  });
  const [toast, setToast] = useState(null);
  const [showStoreMap, setShowStoreMap] = useState(false);
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [orderModalKey, setOrderModalKey] = useState(0);

  const showToast = useCallback((type, message) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // ========== HOOKS ==========
  const {
    currentEmployee, currentTime, loading, setLoading, networkError, retryAuth, handleLogout
  } = usePOSAuth();

  const { toggleChat, setPosContext } = useChat();

  const [showEmployeeOrdersModal, setShowEmployeeOrdersModal] = useState(false);
  const [orderHistorySearch, setOrderHistorySearch] = useState('');
  const [showHelpModal, setShowHelpModal] = useState(false);

  // Sync selected customer to chat context
  useEffect(() => {
    setPosContext(prev => ({
      ...prev,
      selectedCustomer: selectedCustomer
    }));
  }, [selectedCustomer, setPosContext]);

  const {
    cart, setCart, lastAddedId, addToCart, addProductWithBatch,
    updateQuantity, removeFromCart, clearCart, calculateTotals, parsePrice
  } = usePOSCart({ customerDiscounts, selectedCustomer, showToast });

  const {
    scanning, showBatchModal, setShowBatchModal,
    selectedProductData, setSelectedProductData,
    showQRScanner, setShowQRScanner,
    scanHistory, clearScanHistory,
    handleProductClick, handleProductScanned,
    handleQRScanSuccess, handleQRScanError,
    handleBatchSelected, handleMapBatchSelect
  } = usePOSScanner({ addToCart, addProductWithBatch, showToast });

  const {
    holdLoading,
    existingOrder, setExistingOrder,
    showHeldOrdersModal, setShowHeldOrdersModal,
    handleHoldOrder, handleCheckout, handleLoadHeldOrder
  } = usePOSOrder({
    cart, setCart, selectedCustomer, setSelectedCustomer,
    showToast, parsePrice
  });

  const {
    showPaymentModal, setShowPaymentModal,
    vnpayProcessing,
    showInvoiceModal, setShowInvoiceModal,
    invoiceOrder, setInvoiceOrder,
    handlePaymentMethodSelect,
    handleVNPayComplete, handleVNPayFailed,
    handlePaymentModalClose
  } = usePOSPayment({
    existingOrder, setExistingOrder,
    setCart, setSelectedCustomer, showToast
  });

  // ========== DATA LOADING ==========

  useEffect(() => {
    if (loading || !currentEmployee) return;

    const fetchCategories = async () => {
      try {
        const response = await posDataService.getCategoryTree();
        const treeData = response.data?.categories || [];

        // Flatten tree into POS-friendly list:
        // Parent categories expand to include their subcategory IDs
        const posCats = [{ id: 'all', name: 'All Products' }];
        treeData.forEach(parent => {
          const childIds = (parent.children || []).map(c => c.id);
          posCats.push({
            ...parent,
            // Store child IDs for filter expansion
            childIds,
            // Show children inline
            children: parent.children || []
          });
        });

        setCategories(posCats);
      } catch (error) {
        console.error('Error fetching categories:', error);
        setCategories([{ id: 'all', name: 'All Products' }]);
      }
    };

    const fetchDiscountConfig = async () => {
      try {
        const response = await posDataService.getActiveDiscounts();
        if (response.success && response.data) {
          setCustomerDiscounts({
            guest: 0,
            retail: response.data.retail || 10,
            wholesale: response.data.wholesale || 15,
            vip: response.data.vip || 20
          });
        }
      } catch (error) {
        console.error('Error fetching discount configuration:', error);
      }
    };

    fetchCategories();
    fetchDiscountConfig();
  }, [loading, currentEmployee]);

  // Debounce search input (350ms)
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 350);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  useEffect(() => {
    if (loading || !currentEmployee) return;

    const fetchProducts = async () => {
      setLoadingProducts(true);
      try {
        const filters = { isActive: true };
        if (selectedCategory !== 'all') {
          // Find the selected category to check for children
          const selectedCat = categories.find(c => c.id === selectedCategory);
          if (selectedCat?.childIds?.length > 0) {
            // Parent category: include parent + all subcategory IDs
            filters.categoryId = [selectedCategory, ...selectedCat.childIds].join(',');
          } else {
            filters.categoryId = selectedCategory;
          }
        }
        if (debouncedSearch.trim()) filters.search = debouncedSearch.trim();

        // Fetch products + inventory in parallel
        const [productResponse, inventoryResponse] = await Promise.all([
          posDataService.getAllProducts(filters),
          posDataService.getInventorySummary()
        ]);

        const productsData = productResponse.data?.products || [];

        // Build inventory map: productId → { quantityOnShelf, quantityOnHand, quantityAvailable }
        const inventoryMap = {};
        const inventoryData = inventoryResponse.data || [];
        (Array.isArray(inventoryData) ? inventoryData : []).forEach(item => {
          inventoryMap[item.productId] = {
            quantityOnHand: item.quantityOnHand || 0,
            quantityOnShelf: item.quantityOnShelf || 0,
            quantityReserved: item.quantityReserved || 0,
            quantityAvailable: item.quantityAvailable || 0
          };
        });

        // Merge product + inventory data
        setProducts(productsData.map(product => {
          const productId = product._id || product.id;
          const inv = inventoryMap[productId] || {
            quantityOnHand: 0, quantityOnShelf: 0, quantityReserved: 0, quantityAvailable: 0
          };
          return {
            ...product,
            id: productId,
            price: product.unitPrice || 0,
            stock: inv.quantityAvailable,
            categoryName: product.category?.name || 'Uncategorized',
            inventory: inv
          };
        }));
      } catch (error) {
        console.error('Error fetching products:', error);
        setProducts([]);
      } finally {
        setLoadingProducts(false);
      }
    };

    fetchProducts();
  }, [selectedCategory, debouncedSearch, categories, loading, currentEmployee]);

  // ========== KEYBOARD SHORTCUTS ==========

  useEffect(() => {
    const handleKeyPress = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('product-search')?.focus();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault();
        handleLogout(cart.length);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'Delete') {
        e.preventDefault();
        document.getElementById('pos-clear-cart-btn')?.click();
      }
      if (e.key === 'F2') { e.preventDefault(); setShowQRScanner(prev => !prev); }
      if (e.key === 'F3') { e.preventDefault(); toggleChat(); }
      if (e.key === 'F4') { e.preventDefault(); setShowHeldOrdersModal(true); }
      if (e.key === 'F5') { e.preventDefault(); setShowEmployeeOrdersModal(true); }
      if (e.key === 'F8') { e.preventDefault(); document.getElementById('pos-hold-order-btn')?.click(); }
      if (e.key === 'F9') { e.preventDefault(); document.getElementById('pos-checkout-btn')?.click(); }
      if (e.key === 'Escape') {
        e.preventDefault();
        if (showPaymentModal) setShowPaymentModal(false);
        if (showQRScanner) setShowQRScanner(false);
        if (showHeldOrdersModal) setShowHeldOrdersModal(false);
        if (showEmployeeOrdersModal) setShowEmployeeOrdersModal(false);
        if (showHelpModal) setShowHelpModal(false);
        if (showBatchModal) setShowBatchModal(false);
        if (showInvoiceModal) setShowInvoiceModal(false);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [cart.length, handleLogout, showPaymentModal, showQRScanner, showHeldOrdersModal, showEmployeeOrdersModal, showHelpModal, showBatchModal, showInvoiceModal, setShowQRScanner, setShowHeldOrdersModal, setShowEmployeeOrdersModal, setShowHelpModal, setShowPaymentModal, setShowBatchModal, setShowInvoiceModal, toggleChat]);

  // ========== CHATBOT ACTION DISPATCHER ==========

  useEffect(() => {
    const handleChatAction = async (e) => {
      const action = e.detail;
      if (!action) return;

      if (action.type === 'OPEN_MODAL') {
        const { modal, searchQuery } = action.payload || {};
        if (modal === 'POSEmployeeOrdersModal') {
          setOrderHistorySearch(searchQuery || '');
          setShowEmployeeOrdersModal(true);
          showToast('info', searchQuery ? `Đang mở lịch sử đơn hàng: ${searchQuery}...` : 'Đang mở lịch sử đơn hàng...');
        }
        return;
      }

      if (action.type === 'POS_HOLD_ORDER') {
        showToast('info', 'Đang lưu hóa đơn tạm...');
        await handleHoldOrder();
        return;
      }

      if (action.type === 'POS_CHECKOUT') {
        showToast('info', 'Đang mở giao diện thanh toán...');
        const success = await handleCheckout();
        if (success) setShowPaymentModal(true);
        return;
      }

      if (action.type === 'UPDATE_CART_ITEM') {
        const { productId, quantity, name } = action.payload || {};
        if (productId && quantity != null) {
          updateQuantity(productId, quantity);
          showToast('success', `Đã cập nhật ${name || 'sản phẩm'} → số lượng: ${quantity}`);
        }
        return;
      }

      if (action.type === 'CANCEL_ORDER') {
        showToast('info', action.payload?.message || 'Đơn hàng đã được hủy thành công');
        setOrderModalKey(prev => prev + 1);
        return;
      }

      if (action.type !== 'POS_ADD_ITEM') return;

      const { productId, quantity, name, isPerishable } = action.payload;

      if (isPerishable) {
        // 🧊 FRESH PRODUCT: Match scanner behavior and open POSBatchSelectModal
        showToast('success', `${name} là hàng tươi — Mở danh sách lô hàng...`);

        try {
          const [productResponse, batchResponse] = await Promise.all([
            posDataService.getProductById(productId),
            posDataService.getProductBatches(productId)
          ]);

          if (!productResponse.success) {
            showToast('error', `Không thể tải chi tiết sản phẩm ${name}`);
            return;
          }

          const product = productResponse.data?.product;
          const batches = batchResponse.data?.batches || batchResponse.data || [];

          // Only batches available on shelf (qty > 0)
          const availableBatches = batches.filter(batch => {
            const qty = batch.totalOnShelf || batch.detailInventory?.quantityOnShelf || batch.quantityOnShelf || batch.quantity || 0;
            return qty > 0;
          });

          if (availableBatches.length === 0) {
            showToast('error', `${name} không có lô hàng nào khả dụng trên kệ!`);
            return;
          }

          setSelectedProductData({ product, inventory: null, batches: availableBatches });
          setShowBatchModal(true);
        } catch (err) {
          console.error('Error fetching fresh product batches:', err);
          showToast('error', `Lỗi tải lô hàng: ${err.message}`);
        }
      } else {
        // ✅ REGULAR PRODUCT: Add directly (Implicit FEFO)
        showToast('success', `Đang thêm ${quantity}x ${name} vào giỏ...`);

        try {
          const [productResponse, batchResponse] = await Promise.all([
            posDataService.getProductById(productId),
            posDataService.getProductBatches(productId)
          ]);

          if (!productResponse.success) {
            showToast('error', `Không thể tải chi tiết sản phẩm ${name}`);
            return;
          }

          const product = productResponse.data?.product;
          const batches = batchResponse.data?.batches || batchResponse.data || [];

          // Aggregate total quantities across shelf
          const inventory = batches.reduce((acc, b) => {
            acc.quantityOnShelf += b.totalOnShelf || b.detailInventory?.quantityOnShelf || b.quantityOnShelf || 0;
            acc.quantityAvailable += b.quantity || b.totalOnHand || 0;
            return acc;
          }, { quantityOnShelf: 0, quantityAvailable: 0 });

          if (inventory.quantityOnShelf <= 0) {
            showToast('error', `${name} hiện không còn hàng trên kệ!`);
            return;
          }

          // CRITICAL: Override catalog product's isPerishable with chatbot payload value
          // The chatbot already determined perishability; catalog category flag
          // can falsely trigger batch selection modal for non-perishable products
          const cartProduct = {
            ...product,
            id: productId,
            price: product.unitPrice || 0,
            stock: inventory.quantityAvailable,
            inventory,
            isPerishable: false // Non-perishable path — force direct add
          };
          // Also neutralize category perishable flags to prevent addToCart bail-out
          if (cartProduct.category) {
            cartProduct.category = { ...cartProduct.category, isPerishable: false, is_perishable: false };
          }

          // Add to cart directly, passing quantity directly to avoid React state batching race conditions
          const result = await addToCart(cartProduct, quantity);

          if (result && result.success === false) {
            // Toast error already shown inside usePOSCart
            return;
          }

          if (result && result.needsBatchSelection) {
            // Should not happen since we forced isPerishable=false
            console.warn('[POS Chatbot] Unexpected needsBatchSelection for non-perishable product:', name);
            showToast('error', `Sản phẩm ${name} yêu cầu chọn lô hàng. Vui lòng thêm từ giao diện sản phẩm.`);
          }
        } catch (err) {
          console.error('Error adding regular product via chatbot:', err);
          showToast('error', `Lỗi thêm sản phẩm: ${err.message}`);
        }
      }
    };

    window.addEventListener('posmart:chat_action', handleChatAction);
    return () => window.removeEventListener('posmart:chat_action', handleChatAction);
  }, [addToCart, showToast, setSelectedProductData, setShowBatchModal, handleHoldOrder, handleCheckout, setShowPaymentModal]);

  // ========== CHECKOUT WRAPPER ==========

  const onCheckout = async () => {
    const success = await handleCheckout();
    if (success) setShowPaymentModal(true);
  };

  const onClearCart = () => {
    const cleared = clearCart();
    if (cleared) setExistingOrder(null);
  };

  // ========== RENDER ==========

  const totals = calculateTotals();

  if (networkError) {
    return (
      <div className="min-h-screen bg-emerald-950 flex flex-col items-center justify-center font-['Poppins',sans-serif] p-4 text-center">
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20 max-w-md w-full shadow-2xl animate-fade-in-smooth">
          <div className="text-emerald-400 text-6xl mb-4 flex justify-center">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <h2 className="text-white text-2xl font-bold mb-2 font-['Poppins',sans-serif]">Connection Failed</h2>
          <p className="text-emerald-100/75 mb-6 text-[14px]">
            The server is offline or your network is disconnected. Please check your connection and try again.
          </p>
          <div className="flex flex-col gap-3">
            <button
              onClick={retryAuth}
              className="py-3 px-6 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[15px] font-semibold transition-all hover:scale-[1.02] shadow-lg flex items-center justify-center gap-2"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Retry Connection
            </button>
            <button
              onClick={() => handleLogout(0)}
              className="py-3 px-6 bg-white/10 hover:bg-white/20 text-emerald-200 border border-emerald-500/30 rounded-lg text-[15px] font-semibold transition-all"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return <POSLoadingScreen />;
  }

  return (
    <div className="h-screen flex flex-col bg-gray-100 animate-fade-in-smooth">
      <POSHeader
        currentEmployee={currentEmployee}
        currentTime={currentTime}
        onLogout={() => handleLogout(cart.length)}
      />

      <div className="flex-1 flex overflow-hidden">
        {/* Products Section */}
        <div className="flex-1 flex flex-col p-4 overflow-hidden">
          <div className="mb-4">
            <POSSearchBar
              searchTerm={searchTerm}
              onSearchChange={setSearchTerm}
              onProductScanned={handleProductScanned}
              onOpenQRScanner={() => setShowQRScanner(!showQRScanner)}
              onMapClick={() => setShowStoreMap(true)}
              onHistoryClick={() => setShowEmployeeOrdersModal(true)}
              onHelpClick={() => setShowHelpModal(true)}
              scanning={scanning}
              scannerActive={showQRScanner}
            />

            {!showQRScanner && (
              <POSCategoryFilter
                categories={categories}
                selectedCategory={selectedCategory}
                onCategoryChange={setSelectedCategory}
              />
            )}
          </div>

          <div className="flex-1 overflow-y-auto">
            {showQRScanner ? (
              <POSInlineScanner
                onScanSuccess={handleQRScanSuccess}
                onClose={() => setShowQRScanner(false)}
                scanHistory={scanHistory}
                scanning={scanning}
              />
            ) : (
              <POSProductGrid
                products={products}
                loading={loadingProducts}
                searchTerm={searchTerm}
                onProductClick={handleProductClick}
              />
            )}
          </div>
        </div>

        <POSCart
          holdLoading={holdLoading}
          cart={cart}
          onUpdateQuantity={updateQuantity}
          onRemoveItem={removeFromCart}
          onClearCart={onClearCart}
          onCheckout={onCheckout}
          onHoldOrder={handleHoldOrder}
          onOpenHeldOrders={() => setShowHeldOrdersModal(true)}
          totals={totals}
          selectedCustomer={selectedCustomer}
          onCustomerChange={setSelectedCustomer}
          customerDiscounts={customerDiscounts}
          lastAddedId={lastAddedId}
        />
      </div>

      <POSPaymentModal
        isOpen={showPaymentModal}
        totals={totals}
        onClose={handlePaymentModalClose}
        onPaymentMethodSelect={handlePaymentMethodSelect}
        existingOrder={existingOrder}
      />

      <POSBatchSelectModal
        isOpen={showBatchModal}
        productData={selectedProductData}
        onClose={() => {
          setShowBatchModal(false);
          setSelectedProductData(null);
        }}
        onBatchSelected={handleBatchSelected}
      />

      <POSHeldOrdersModal
        isOpen={showHeldOrdersModal}
        onClose={() => setShowHeldOrdersModal(false)}
        onLoadOrder={handleLoadHeldOrder}
        currentEmployee={currentEmployee}
      />

      <POSEmployeeOrdersModal
        key={orderModalKey}
        isOpen={showEmployeeOrdersModal}
        onClose={() => {
          setShowEmployeeOrdersModal(false);
          setOrderHistorySearch('');
        }}
        currentEmployee={currentEmployee}
        onLoadDraftOrder={handleLoadHeldOrder}
        initialSearch={orderHistorySearch}
      />

      <POSHelpModal
        isOpen={showHelpModal}
        onClose={() => setShowHelpModal(false)}
      />


      <POSStoreMapModal
        isOpen={showStoreMap}
        onClose={() => setShowStoreMap(false)}
        onLocationSelect={handleMapBatchSelect}
      />

      <POSInvoiceModal
        isOpen={showInvoiceModal}
        order={invoiceOrder}
        onClose={() => {
          setShowInvoiceModal(false);
          setInvoiceOrder(null);
          setCart([]);
          setSelectedCustomer(null);
          setExistingOrder(null);
          setSearchTerm('');
        }}
        onComplete={() => {
          setShowInvoiceModal(false);
          setInvoiceOrder(null);
          setCart([]);
          setSelectedCustomer(null);
          setExistingOrder(null);
          setSearchTerm('');
        }}
      />

      <VNPayReturnHandler
        onPaymentComplete={handleVNPayComplete}
        onPaymentFailed={handleVNPayFailed}
      />

      {/* Action-based Chatbot Assistant */}
      <ChatWidget />

      {/* Toast Notification */}
      {toast && (
        <div className={`fixed top-4 right-4 z-[10000] px-6 py-4 rounded-lg shadow-2xl flex items-center gap-3 animate-slide-in-right ${toast.type === 'success'
          ? 'bg-green-500 text-white'
          : 'bg-red-500 text-white'
          }`}>
          {toast.type === 'success' ? (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M20 6L9 17L4 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          ) : (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
              <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
          )}
          <span className="font-semibold text-[14px]">{toast.message}</span>
        </div>
      )}
    </div>
  );
};

const POSHelpModal = ({ isOpen, onClose }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]">
      <div className="bg-white rounded-xl shadow-2xl max-w-md w-full mx-4 overflow-hidden flex flex-col border border-gray-100 animate-fade-in">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-emerald-50 flex justify-between items-center font-['Poppins',sans-serif]">
          <h3 className="text-[17px] font-bold text-gray-950 flex items-center gap-2">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-emerald-600">
              <circle cx="12" cy="12" r="10" />
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <span>Keyboard Shortcuts Guide</span>
          </h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-200 rounded-full transition-colors text-gray-500 font-bold">&times;</button>
        </div>

        {/* Body */}
        <div className="p-6 font-['Poppins',sans-serif] space-y-4 max-h-[70vh] overflow-y-auto">
          {/* Global Section */}
          <div>
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Global System Keys</h4>
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 font-medium">Focus product search input</span>
                <span className="px-2 py-1 bg-gray-100 border border-gray-300 rounded font-semibold text-gray-800 shadow-sm">Ctrl + K / Ctrl + M</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 font-medium">Log out securely</span>
                <span className="px-2 py-1 bg-gray-100 border border-gray-300 rounded font-semibold text-gray-800 shadow-sm">Ctrl + L</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 font-medium">Clear items in cart</span>
                <span className="px-2 py-1 bg-gray-100 border border-gray-300 rounded font-semibold text-gray-800 shadow-sm">Ctrl + Delete</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 font-medium">Close any active modal dialog</span>
                <span className="px-2 py-1 bg-gray-100 border border-gray-300 rounded font-semibold text-gray-800 shadow-sm">Esc</span>
              </div>
            </div>
          </div>

          <hr className="border-gray-150" />

          {/* Menu Controls */}
          <div>
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Interface Controls</h4>
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 font-medium">Toggle barcode/QR scanner view</span>
                <span className="px-2 py-1 bg-gray-100 border border-gray-300 rounded font-semibold text-gray-800 shadow-sm">F2</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 font-medium">Open POSMART AI Chatbot panel</span>
                <span className="px-2 py-1 bg-gray-100 border border-gray-300 rounded font-semibold text-gray-800 shadow-sm">F3</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 font-medium">Open Held Orders (Draft List)</span>
                <span className="px-2 py-1 bg-gray-100 border border-gray-300 rounded font-semibold text-gray-800 shadow-sm">F4</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 font-medium">Open employee logs order history</span>
                <span className="px-2 py-1 bg-gray-100 border border-gray-300 rounded font-semibold text-gray-800 shadow-sm">F5</span>
              </div>
            </div>
          </div>

          <hr className="border-gray-150" />

          {/* In-Cart Operations */}
          <div>
            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Order Cart Actions</h4>
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 font-medium">Temporarily save/hold current order</span>
                <span className="px-2 py-1 bg-gray-100 border border-gray-300 rounded font-semibold text-gray-800 shadow-sm">F8</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-600 font-medium">Trigger checkout / direct payment modal</span>
                <span className="px-2 py-1 bg-gray-100 border border-gray-300 rounded font-semibold text-gray-800 shadow-sm">F9</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-1.5 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 text-xs transition-colors"
          >
            Got It
          </button>
        </div>
      </div>
    </div>
  );
};