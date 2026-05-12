import React, { useState, useEffect, useRef } from 'react';
import stockOutOrderService from '../../services/stockOutOrderService';
import inventoryService from '../../services/inventoryService';
import authService from '../../services/authService';
import employeeService from '../../services/employeeService';

export const CreateStockOutOrderModal = ({ isOpen, onClose, onSuccess }) => {
  const dropdownRefs = useRef({});

  const [formData, setFormData] = useState({
    reason: 'sales',
    destination: '',
  });

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [currentEmployee, setCurrentEmployee] = useState(null);

  // Product list from inventory summary
  const [products, setProducts] = useState([]);
  const [productsLoading, setProductsLoading] = useState(false);

  // Per-item batch data cache: { [productId]: batchList }
  const [batchCache, setBatchCache] = useState({});

  // Search & dropdown states
  const [productSearchTerms, setProductSearchTerms] = useState({});
  const [showProductDropdown, setShowProductDropdown] = useState({});
  const [batchSearchTerms, setBatchSearchTerms] = useState({});
  const [showBatchDropdown, setShowBatchDropdown] = useState({});

  useEffect(() => {
    if (isOpen) {
      setFormData({ reason: 'sales', destination: '' });
      setItems([]);
      setProductSearchTerms({});
      setShowProductDropdown({});
      setBatchSearchTerms({});
      setShowBatchDropdown({});
      setError(null);
      setBatchCache({});

      fetchProducts();
      fetchEmployee();
    }
  }, [isOpen]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      Object.entries(dropdownRefs.current).forEach(([key, ref]) => {
        if (ref && !ref.contains(event.target)) {
          const [type, index] = key.split('-');
          if (type === 'product') {
            setShowProductDropdown(prev => ({ ...prev, [index]: false }));
          } else if (type === 'batch') {
            setShowBatchDropdown(prev => ({ ...prev, [index]: false }));
          }
        }
      });
    };

    if (Object.values(showProductDropdown).some(v => v) || Object.values(showBatchDropdown).some(v => v)) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showProductDropdown, showBatchDropdown]);

  const fetchProducts = async () => {
    setProductsLoading(true);
    try {
      const response = await inventoryService.getInventorySummary();
      if (response.success && Array.isArray(response.data)) {
        // Only show products with on-hand stock > 0
        const inStock = response.data.filter(p => (p.quantityOnHand || 0) > 0);
        setProducts(inStock);
      }
    } catch (err) {
      console.error('Error loading products:', err);
    } finally {
      setProductsLoading(false);
    }
  };

  const fetchEmployee = async () => {
    try {
      const user = authService.getUser();
      setCurrentUser(user);
      if (user?.employeeId) {
        const res = await employeeService.getEmployeeById(user.employeeId);
        if (res.success && res.data) setCurrentEmployee(res.data.employee);
      }
    } catch (err) {
      console.error('Error fetching employee:', err);
    }
  };

  // Fetch batches for a product (with cache)
  const fetchBatchesForProduct = async (productId) => {
    if (batchCache[productId]) return batchCache[productId];
    try {
      const response = await inventoryService.getBatchesByProduct(productId);
      if (response.success && Array.isArray(response.data)) {
        const withStock = response.data.filter(b => (b.totalOnHand || 0) > 0);
        setBatchCache(prev => ({ ...prev, [productId]: withStock }));
        return withStock;
      }
    } catch (err) {
      console.error('Error fetching batches:', err);
    }
    return [];
  };

  // --- Item Management ---
  const addItem = () => {
    const idx = items.length;
    setItems([...items, { productId: '', batchId: '', quantity: 1, unitPrice: 0, onHandQty: 0, batchCode: '', expiryDate: null, productName: '' }]);
    setProductSearchTerms(prev => ({ ...prev, [idx]: '' }));
    setBatchSearchTerms(prev => ({ ...prev, [idx]: '' }));
  };

  const removeItem = (index) => {
    setItems(items.filter((_, i) => i !== index));
  };

  // --- Product Selection ---
  const selectProduct = async (index, product) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], productId: product.productId, productName: product.product?.name || '', batchId: '', onHandQty: 0, batchCode: '', unitPrice: 0, expiryDate: null };
    setItems(newItems);
    setProductSearchTerms(prev => ({ ...prev, [index]: product.product?.name || '' }));
    setShowProductDropdown(prev => ({ ...prev, [index]: false }));
    setBatchSearchTerms(prev => ({ ...prev, [index]: '' }));

    // Pre-fetch batches
    await fetchBatchesForProduct(product.productId);
  };

  const getFilteredProducts = (index) => {
    const term = (productSearchTerms[index] || '').toLowerCase();
    const selectedIds = items.map((it, idx) => idx !== index ? it.productId : null).filter(Boolean);
    let filtered = products.filter(p => !selectedIds.includes(p.productId));
    if (term) {
      filtered = filtered.filter(p =>
        p.product?.name?.toLowerCase().includes(term) ||
        String(p.productId).includes(term)
      );
    }
    return term ? filtered : filtered.slice(0, 20);
  };

  // --- Batch Selection ---
  const selectBatch = (index, batch) => {
    const newItems = [...items];
    newItems[index] = {
      ...newItems[index],
      batchId: batch.id,
      onHandQty: batch.totalOnHand || 0,
      batchCode: `B-${batch.id}`,
      unitPrice: batch.unitPrice || 0,
      expiryDate: batch.expiryDate
    };
    setItems(newItems);
    setBatchSearchTerms(prev => ({ ...prev, [index]: `B-${batch.id}` }));
    setShowBatchDropdown(prev => ({ ...prev, [index]: false }));
  };

  const selectAllBatches = async (index) => {
    const item = items[index];
    if (!item?.productId) return;

    const batches = await fetchBatchesForProduct(item.productId);
    if (batches.length === 0) { setError('No batches available'); return; }

    const batchItems = batches.map(b => ({
      productId: item.productId,
      productName: item.productName,
      batchId: b.id,
      quantity: 1,
      unitPrice: b.unitPrice || 0,
      onHandQty: b.totalOnHand || 0,
      batchCode: `B-${b.id}`,
      expiryDate: b.expiryDate
    }));

    const before = items.slice(0, index);
    const after = items.slice(index + 1);
    const updated = [...before, ...batchItems, ...after];
    setItems(updated);

    // Update search terms
    const newPST = {};
    const newBST = {};
    updated.forEach((it, idx) => {
      newPST[idx] = it.productName || '';
      newBST[idx] = it.batchCode || '';
    });
    setProductSearchTerms(newPST);
    setBatchSearchTerms(newBST);
    setError(null);
  };

  const getFilteredBatches = (index) => {
    const item = items[index];
    if (!item?.productId) return [];
    const batches = batchCache[item.productId] || [];
    const term = (batchSearchTerms[index] || '').toLowerCase();
    if (!term) return batches.slice(0, 20);
    return batches.filter(b => `B-${b.id}`.toLowerCase().includes(term));
  };

  const calculateTotal = () => items.reduce((sum, it) => sum + (it.quantity * it.unitPrice), 0);

  // --- Submit ---
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (items.length === 0) { setError('Please add at least one item'); return; }

    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      if (!it.productId) { setError(`Item ${i + 1}: Please select a product`); return; }
      if (!it.batchId) { setError(`Item ${i + 1}: Please select a batch`); return; }
      if (it.quantity <= 0) { setError(`Item ${i + 1}: Quantity must be > 0`); return; }
      if (it.quantity > it.onHandQty) { setError(`Item ${i + 1}: Quantity exceeds stock (${it.onHandQty})`); return; }
    }

    setLoading(true);
    setError(null);

    try {
      await stockOutOrderService.createStockOutOrder({
        reason: formData.reason,
        destination: formData.destination || null,
        items: items.map(it => ({
          batch_id: it.batchId,
          quantity: it.quantity,
          unit_price: it.unitPrice
        }))
      });

      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      console.error('Error creating stock out order:', err);
      setError(err.response?.data?.error?.message || err.response?.data?.error || err.message || 'Failed to create stock out order');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const totals = calculateTotal();

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Create Stock Out Order
            </h2>
            <p className="text-[12px] text-gray-500 font-['Poppins',sans-serif] mt-1">
              Release inventory from warehouse • Status: <span className="font-semibold text-gray-600">Draft</span>
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px] font-['Poppins',sans-serif]">
              {error}
            </div>
          )}

          {/* Order Information */}
          <div className="space-y-4">
            <h3 className="text-[16px] font-semibold font-['Poppins',sans-serif] text-[#212529]">Order Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529] mb-2">
                  Reason <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  required
                  className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                >
                  <option value="sales">Sales</option>
                  <option value="transfer">Transfer</option>
                  <option value="damage">Damage</option>
                  <option value="expired">Expired</option>
                  <option value="return_to_supplier">Return to Supplier</option>
                  <option value="internal_use">Internal Use</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529] mb-2">
                  Destination <span className="text-gray-400 font-normal">(Optional)</span>
                </label>
                <input
                  type="text"
                  value={formData.destination}
                  onChange={(e) => setFormData({ ...formData, destination: e.target.value })}
                  placeholder="e.g., Customer name, warehouse location, etc."
                  className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                />
              </div>
            </div>
          </div>

          {/* Items */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-[16px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
                Items <span className="text-red-500">*</span>
              </h3>
              <button type="button" onClick={addItem}
                className="px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 text-[12px] font-['Poppins',sans-serif] font-medium flex items-center gap-1.5 transition-colors">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Add Item
              </button>
            </div>

            {items.length === 0 && (
              <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
                <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                  {productsLoading ? 'Loading products...' : 'No items added yet. Click "Add Item" to start.'}
                </p>
              </div>
            )}

            <div className="space-y-3">
              {items.map((item, index) => {
                const filteredProducts = getFilteredProducts(index);
                const filteredBatches = getFilteredBatches(index);
                const selectedProduct = products.find(p => p.productId === item.productId);

                return (
                  <div key={index} className="bg-gray-50 p-4 rounded-lg border-2 border-gray-200">
                    <div className="flex items-start gap-3">
                      <div className="flex-1 space-y-3">
                        {/* Product & Batch Selection */}
                        <div className="grid grid-cols-2 gap-3">
                          {/* Product */}
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <label className="block text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                                Product <span className="text-red-500">*</span>
                              </label>
                              {item.productId && !item.batchId && (
                                <button type="button" onClick={() => selectAllBatches(index)}
                                  className="px-2 py-0.5 bg-blue-600 text-white rounded text-[10px] font-['Poppins',sans-serif] font-medium hover:bg-blue-700 transition-colors flex items-center gap-1"
                                  title="Select all available batches">
                                  <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
                                    <path d="M2 8h12M8 2v12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                                  </svg>
                                  All Batches
                                </button>
                              )}
                            </div>
                            <div ref={el => dropdownRefs.current[`product-${index}`] = el} className="relative">
                              <input
                                type="text"
                                value={productSearchTerms[index] || ''}
                                onChange={(e) => {
                                  setProductSearchTerms(prev => ({ ...prev, [index]: e.target.value }));
                                  setShowProductDropdown(prev => ({ ...prev, [index]: true }));
                                }}
                                onFocus={() => setShowProductDropdown(prev => ({ ...prev, [index]: true }))}
                                placeholder="Search product..."
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-red-500"
                              />

                              {selectedProduct && !showProductDropdown[index] && (
                                <div className="absolute inset-0 px-3 py-2 bg-white border border-red-500 rounded-lg text-[12px] font-['Poppins',sans-serif] flex items-center justify-between pointer-events-none">
                                  <span className="text-red-700 font-semibold">{selectedProduct.product?.name}</span>
                                  <span className="text-blue-600 text-[10px] font-semibold">#{selectedProduct.productId}</span>
                                </div>
                              )}

                              {showProductDropdown[index] && (
                                <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                                  {filteredProducts.length === 0 ? (
                                    <div className="px-3 py-2 text-[12px] text-gray-500 font-['Poppins',sans-serif]">No products found</div>
                                  ) : (
                                    filteredProducts.map(p => (
                                      <button key={p.productId} type="button" onClick={() => selectProduct(index, p)}
                                        className="w-full px-3 py-2 text-left text-[12px] font-['Poppins',sans-serif] hover:bg-red-50 border-b border-gray-100 last:border-b-0">
                                        <div className="flex items-center justify-between">
                                          <span className="font-semibold text-gray-900">{p.product?.name}</span>
                                          <span className="text-emerald-600 text-[10px] font-semibold">On Hand: {p.quantityOnHand}</span>
                                        </div>
                                      </button>
                                    ))
                                  )}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Batch */}
                          <div>
                            <label className="block text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-1">
                              Batch <span className="text-red-500">*</span>
                            </label>
                            <div ref={el => dropdownRefs.current[`batch-${index}`] = el} className="relative">
                              <input
                                type="text"
                                value={batchSearchTerms[index] || ''}
                                onChange={(e) => {
                                  setBatchSearchTerms(prev => ({ ...prev, [index]: e.target.value }));
                                  setShowBatchDropdown(prev => ({ ...prev, [index]: true }));
                                }}
                                onFocus={() => item.productId && setShowBatchDropdown(prev => ({ ...prev, [index]: true }))}
                                placeholder={item.productId ? "Search batch..." : "Select product first"}
                                disabled={!item.productId}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-red-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                              />

                              {item.batchId && !showBatchDropdown[index] && (
                                <div className="absolute inset-0 px-3 py-2 bg-white border border-red-500 rounded-lg text-[12px] font-['Poppins',sans-serif] flex items-center justify-between pointer-events-none">
                                  <span className="text-red-700 font-semibold font-mono">{item.batchCode}</span>
                                  <span className="text-gray-500 text-[10px]">OnHand: {item.onHandQty}</span>
                                </div>
                              )}

                              {showBatchDropdown[index] && item.productId && (
                                <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                                  {filteredBatches.length === 0 ? (
                                    <div className="px-3 py-2 text-[12px] text-gray-500 font-['Poppins',sans-serif]">No batches available</div>
                                  ) : (
                                    filteredBatches.map(b => (
                                      <button key={b.id} type="button" onClick={() => selectBatch(index, b)}
                                        className="w-full px-3 py-2 text-left text-[12px] font-['Poppins',sans-serif] hover:bg-red-50 border-b border-gray-100 last:border-b-0">
                                        <div className="flex items-center justify-between">
                                          <span className="font-semibold text-gray-900 font-mono">B-{b.id}</span>
                                          <span className="text-gray-600 text-[10px]">OnHand: {b.totalOnHand || 0}</span>
                                        </div>
                                        {b.expiryDate && (
                                          <div className="text-gray-500 text-[10px] mt-0.5">
                                            Exp: {new Date(b.expiryDate).toLocaleDateString()}
                                          </div>
                                        )}
                                      </button>
                                    ))
                                  )}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Quantity & Price */}
                        <div className="grid grid-cols-3 gap-3">
                          <div>
                            <label className="block text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-1">Available</label>
                            <div className="px-3 py-2 bg-gray-100 border border-gray-300 rounded-lg text-[12px] font-['Poppins',sans-serif] text-gray-700">
                              {item.onHandQty || 0}
                            </div>
                          </div>
                          <div>
                            <label className="block text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-1">
                              Quantity <span className="text-red-500">*</span>
                            </label>
                            <input type="number" value={item.quantity}
                              onChange={(e) => {
                                const newItems = [...items];
                                newItems[index] = { ...newItems[index], quantity: parseInt(e.target.value) || 0 };
                                setItems(newItems);
                              }}
                              min="1" max={item.onHandQty || 999999}
                              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-red-500"
                            />
                          </div>
                          <div>
                            <label className="block text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-1">Unit Price (₫)</label>
                            <input type="number" value={item.unitPrice} readOnly
                              className="w-full px-3 py-2 bg-gray-100 border border-gray-300 rounded-lg text-[12px] font-['Poppins',sans-serif] text-gray-700 cursor-not-allowed"
                            />
                          </div>
                        </div>

                        {/* Line Total */}
                        <div className="flex justify-end">
                          <div className="text-[12px] font-['Poppins',sans-serif]">
                            <span className="text-gray-600">Total: </span>
                            <span className="font-semibold text-red-600">{(item.quantity * item.unitPrice).toLocaleString('vi-VN')}₫</span>
                          </div>
                        </div>
                      </div>

                      {/* Remove */}
                      <button type="button" onClick={() => removeItem(index)}
                        className="mt-6 p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Remove item">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                          <path d="M12 4L4 12M4 4L12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Summary */}
          {items.length > 0 && (
            <div className="bg-red-50 border-2 border-red-200 rounded-lg p-5">
              <h4 className="text-[14px] font-semibold font-['Poppins',sans-serif] text-[#212529] mb-3">Order Summary</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-[13px] font-['Poppins',sans-serif]">
                  <span className="text-gray-600">Total Items:</span>
                  <span className="font-semibold">{items.length} item(s)</span>
                </div>
                <div className="flex justify-between text-[13px] font-['Poppins',sans-serif]">
                  <span className="text-gray-600">Total Quantity:</span>
                  <span className="font-semibold">{items.reduce((s, it) => s + it.quantity, 0)} units</span>
                </div>
                <div className="flex justify-between border-t-2 border-red-300 pt-2 mt-2">
                  <span className="font-bold text-[15px] font-['Poppins',sans-serif] text-gray-900">Estimated Value:</span>
                  <span className="font-bold text-red-600 text-[18px] font-['Poppins',sans-serif]">
                    {totals.toLocaleString('vi-VN')}₫
                  </span>
                </div>
              </div>
            </div>
          )}
        </form>

        {/* Footer */}
        <div className="border-t-2 border-gray-200 p-6 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="text-[12px] text-gray-600 font-['Poppins',sans-serif]">
              <p>
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className="inline mr-1 align-text-bottom text-emerald-600">
                  <path d="M13.5 4L6 11.5L2.5 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Order will be created as: <span className="font-semibold text-gray-600">Draft</span>
              </p>
              <p className="mt-1">Reason: {formData.reason}</p>
            </div>
            <div className="flex items-center gap-3">
              <button type="button" onClick={onClose} disabled={loading}
                className="px-5 py-2.5 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-white transition-colors text-[13px] font-['Poppins',sans-serif] font-semibold disabled:opacity-50">
                Cancel
              </button>
              <button type="submit" onClick={handleSubmit} disabled={loading || items.length === 0}
                className="px-6 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-[13px] font-['Poppins',sans-serif] font-semibold disabled:opacity-50 flex items-center gap-2 shadow-lg hover:shadow-xl">
                {loading ? (
                  <>
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Creating...
                  </>
                ) : (
                  <>
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <path d="M13.5 4L6 11.5L2.5 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    Create Stock Out Order
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
