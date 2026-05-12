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
import { POSInlineScanner } from '../../components/POSMain/POSInlineScanner';
import { VNPayReturnHandler } from '../../components/VNPayReturnHandler';

import { usePOSAuth } from '../../hooks/usePOSAuth';
import { usePOSCart } from '../../hooks/usePOSCart';
import { usePOSScanner } from '../../hooks/usePOSScanner';
import { usePOSOrder } from '../../hooks/usePOSOrder';
import { usePOSPayment } from '../../hooks/usePOSPayment';

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

  const showToast = useCallback((type, message) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3000);
  }, []);

  // ========== HOOKS ==========
  const {
    currentEmployee, currentTime, loading, setLoading, handleLogout
  } = usePOSAuth();

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
    existingOrder, setExistingOrder,
    showHeldOrdersModal, setShowHeldOrdersModal,
    handleHoldOrder, handleCheckout, handleLoadHeldOrder
  } = usePOSOrder({
    cart, setCart, selectedCustomer, setSelectedCustomer,
    showToast, setLoading, parsePrice
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
  }, []);

  // Debounce search input (350ms)
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 350);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  useEffect(() => {
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
  }, [selectedCategory, debouncedSearch, categories]);

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
      if (e.key === 'F4') { e.preventDefault(); setShowHeldOrdersModal(true); }
      if (e.key === 'F8') { e.preventDefault(); document.getElementById('pos-hold-order-btn')?.click(); }
      if (e.key === 'F9') { e.preventDefault(); document.getElementById('pos-checkout-btn')?.click(); }
      if (e.key === 'Escape') {
        e.preventDefault();
        if (showPaymentModal) setShowPaymentModal(false);
        if (showQRScanner) setShowQRScanner(false);
        if (showHeldOrdersModal) setShowHeldOrdersModal(false);
        if (showBatchModal) setShowBatchModal(false);
        if (showInvoiceModal) setShowInvoiceModal(false);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [cart.length, handleLogout, showPaymentModal, showQRScanner, showHeldOrdersModal, showBatchModal, showInvoiceModal, setShowQRScanner, setShowHeldOrdersModal, setShowPaymentModal, setShowBatchModal, setShowInvoiceModal]);

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