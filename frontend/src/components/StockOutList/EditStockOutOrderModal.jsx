import React, { useState, useEffect, useRef } from 'react';
import stockOutOrderService from '../../services/stockOutOrderService';
import inventoryService from '../../services/inventoryService';

export const EditStockOutOrderModal = ({ isOpen, onClose, onSuccess, stockOutOrder }) => {
  const dropdownRefs = useRef({});

  const [formData, setFormData] = useState({ reason: 'sales', destination: '' });
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [error, setError] = useState(null);

  // Inventory data
  const [products, setProducts] = useState([]);
  const [batchCache, setBatchCache] = useState({});

  // Search & dropdown states
  const [productSearchTerms, setProductSearchTerms] = useState({});
  const [showProductDropdown, setShowProductDropdown] = useState({});
  const [batchSearchTerms, setBatchSearchTerms] = useState({});
  const [showBatchDropdown, setShowBatchDropdown] = useState({});

  const isFullEditAllowed = stockOutOrder?.status === 'draft';

  const getStatusStyles = (status) => ({
    draft: 'bg-gray-500', pending: 'bg-amber-500', completed: 'bg-emerald-500', cancelled: 'bg-red-500'
  }[(status || '').toLowerCase()] || 'bg-gray-500');

  const getStatusLabel = (status) => ({
    draft: 'Draft', pending: 'Pending', completed: 'Completed', cancelled: 'Cancelled'
  }[(status || '').toLowerCase()] || status);

  useEffect(() => {
    if (isOpen && stockOutOrder) {
      loadOrder();
      if (isFullEditAllowed) fetchProducts();
    }
  }, [isOpen, stockOutOrder]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      Object.entries(dropdownRefs.current).forEach(([key, ref]) => {
        if (ref && !ref.contains(e.target)) {
          const [type, index] = key.split('-');
          if (type === 'product') setShowProductDropdown(prev => ({ ...prev, [index]: false }));
          else if (type === 'batch') setShowBatchDropdown(prev => ({ ...prev, [index]: false }));
        }
      });
    };
    if (Object.values(showProductDropdown).some(v => v) || Object.values(showBatchDropdown).some(v => v)) {
      document.addEventListener('mousedown', handler);
    }
    return () => document.removeEventListener('mousedown', handler);
  }, [showProductDropdown, showBatchDropdown]);

  const fetchProducts = async () => {
    try {
      const response = await inventoryService.getInventorySummary();
      if (response.success && Array.isArray(response.data)) {
        setProducts(response.data.filter(p => (p.quantityOnHand || 0) > 0));
      }
    } catch (err) {
      console.error('Error loading products:', err);
    }
  };

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

  const loadOrder = async () => {
    try {
      setLoadingDetails(true);
      setError(null);

      // Set header from stockOutOrder (already camelCase from list)
      setFormData({
        reason: stockOutOrder.reason || 'sales',
        destination: stockOutOrder.destination || ''
      });

      // Fetch full order with details from backend
      const response = await stockOutOrderService.getStockOutOrderById(stockOutOrder.id);
      const order = response.success ? response.data?.order : null;
      const details = order?.details || [];

      const loadedItems = details.map(d => ({
        detailId: d.id,
        productId: d.productId,
        batchId: d.batchId,
        quantity: d.quantity || 0,
        unitPrice: d.unitPrice || 0,
        onHandQty: d.quantity || 0,
        batchCode: `B-${d.batchId}`,
        expiryDate: d.expiryDate
      }));

      setItems(loadedItems);

      // Set search terms
      const pst = {};
      const bst = {};
      loadedItems.forEach((it, i) => {
        pst[i] = `Product #${it.productId}`;
        bst[i] = it.batchCode;
      });
      setProductSearchTerms(pst);
      setBatchSearchTerms(bst);

      // Pre-fetch batches for loaded products if draft
      if (isFullEditAllowed) {
        const uniqueProductIds = [...new Set(loadedItems.map(it => it.productId).filter(Boolean))];
        for (const pid of uniqueProductIds) {
          const batches = await fetchBatchesForProduct(pid);
          // Update onHandQty from batch data
          const updatedItems = [...loadedItems];
          updatedItems.forEach(it => {
            if (it.productId === pid) {
              const batch = batches.find(b => b.id === it.batchId);
              if (batch) it.onHandQty = batch.totalOnHand || it.quantity;
            }
          });
          setItems(updatedItems);
        }
      }
    } catch (err) {
      console.error('Error loading order:', err);
      setError('Failed to load stock out order details');
    } finally {
      setLoadingDetails(false);
    }
  };

  // --- Item management (draft only) ---
  const addItem = () => {
    if (!isFullEditAllowed) return;
    const idx = items.length;
    setItems([...items, { productId: '', batchId: '', quantity: 1, unitPrice: 0, onHandQty: 0, batchCode: '', expiryDate: null }]);
    setProductSearchTerms(prev => ({ ...prev, [idx]: '' }));
    setBatchSearchTerms(prev => ({ ...prev, [idx]: '' }));
  };

  const removeItem = (index) => {
    if (!isFullEditAllowed) return;
    setItems(items.filter((_, i) => i !== index));
  };

  const selectProduct = async (index, product) => {
    if (!isFullEditAllowed) return;
    const newItems = [...items];
    newItems[index] = { ...newItems[index], productId: product.productId, batchId: '', onHandQty: 0, batchCode: '', unitPrice: 0, expiryDate: null };
    setItems(newItems);
    setProductSearchTerms(prev => ({ ...prev, [index]: product.product?.name || '' }));
    setShowProductDropdown(prev => ({ ...prev, [index]: false }));
    setBatchSearchTerms(prev => ({ ...prev, [index]: '' }));
    await fetchBatchesForProduct(product.productId);
  };

  const selectBatch = (index, batch) => {
    if (!isFullEditAllowed) return;
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

  const getFilteredProducts = (index) => {
    const term = (productSearchTerms[index] || '').toLowerCase();
    const selectedIds = items.map((it, idx) => idx !== index ? it.productId : null).filter(Boolean);
    let filtered = products.filter(p => !selectedIds.includes(p.productId));
    if (term) filtered = filtered.filter(p => p.product?.name?.toLowerCase().includes(term) || String(p.productId).includes(term));
    return term ? filtered : filtered.slice(0, 20);
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
    setLoading(true);
    setError(null);

    try {
      const updateData = {
        reason: formData.reason,
        destination: formData.destination || null
      };

      // For draft: include items for full update
      if (isFullEditAllowed) {
        if (items.length === 0) { setError('Please add at least one item'); setLoading(false); return; }
        for (let i = 0; i < items.length; i++) {
          const it = items[i];
          if (!it.productId) { setError(`Item ${i + 1}: Select a product`); setLoading(false); return; }
          if (!it.batchId) { setError(`Item ${i + 1}: Select a batch`); setLoading(false); return; }
          if (it.quantity <= 0) { setError(`Item ${i + 1}: Quantity must be > 0`); setLoading(false); return; }
          if (it.quantity > it.onHandQty) { setError(`Item ${i + 1}: Exceeds stock (${it.onHandQty})`); setLoading(false); return; }
        }
        updateData.items = items.map(it => ({
          batch_id: it.batchId,
          quantity: it.quantity,
          unit_price: it.unitPrice
        }));
      }

      await stockOutOrderService.updateStockOutOrder(stockOutOrder.id, updateData);
      if (onSuccess) onSuccess();
      onClose();
    } catch (err) {
      console.error('Error updating:', err);
      setError(err.response?.data?.error?.message || err.message || 'Failed to update');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Edit Stock Out Order - SO-{stockOutOrder?.id}
            </h2>
            <span className={`${getStatusStyles(stockOutOrder?.status)} px-2.5 py-1 rounded text-[11px] font-bold font-['Poppins',sans-serif] text-white uppercase`}>
              {getStatusLabel(stockOutOrder?.status)}
            </span>
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
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px] font-['Poppins',sans-serif]">{error}</div>
          )}

          {loadingDetails ? (
            <div className="text-center py-8">
              <div className="animate-spin h-8 w-8 border-4 border-red-500 border-t-transparent rounded-full mx-auto"></div>
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif] mt-2">Loading details...</p>
            </div>
          ) : (
            <>
              {!isFullEditAllowed && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <p className="text-[12px] text-amber-700 font-['Poppins',sans-serif]">
                    This order is <strong>{stockOutOrder?.status}</strong>. Only reason and destination can be modified.
                  </p>
                </div>
              )}

              {/* Order Info */}
              <div className="space-y-4">
                <h3 className="text-[16px] font-semibold font-['Poppins',sans-serif] text-[#212529]">Order Information</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529] mb-2">Reason <span className="text-red-500">*</span></label>
                    <select value={formData.reason} onChange={(e) => setFormData({ ...formData, reason: e.target.value })} required
                      className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-red-500">
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
                    <input type="text" value={formData.destination}
                      onChange={(e) => setFormData({ ...formData, destination: e.target.value })}
                      placeholder="e.g., Customer name, warehouse, etc."
                      className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-red-500"
                    />
                  </div>
                </div>
              </div>

              {/* Items */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <h3 className="text-[16px] font-semibold font-['Poppins',sans-serif] text-[#212529]">Items <span className="text-red-500">*</span></h3>
                    {!isFullEditAllowed && (
                      <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-[10px] font-semibold">Read-only</span>
                    )}
                  </div>
                  {isFullEditAllowed && (
                    <button type="button" onClick={addItem}
                      className="px-3 py-1.5 bg-red-600 text-white rounded-lg hover:bg-red-700 text-[12px] font-['Poppins',sans-serif] font-medium flex items-center gap-1.5 transition-colors">
                      <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                        <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                      Add Item
                    </button>
                  )}
                </div>

                {items.length === 0 && (
                  <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
                    <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">No items in this order.</p>
                  </div>
                )}

                <div className="space-y-3">
                  {items.map((item, index) => {
                    const selectedProduct = products.find(p => p.productId === item.productId);
                    const filteredProducts = isFullEditAllowed ? getFilteredProducts(index) : [];
                    const filteredBatches = isFullEditAllowed ? getFilteredBatches(index) : [];

                    return (
                      <div key={index} className="bg-gray-50 p-4 rounded-lg border-2 border-gray-200">
                        <div className="flex items-start gap-3">
                          <div className="flex-1 space-y-3">
                            <div className="grid grid-cols-2 gap-3">
                              {/* Product */}
                              <div>
                                <label className="block text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-1">
                                  Product <span className="text-red-500">*</span>
                                </label>
                                <div ref={el => dropdownRefs.current[`product-${index}`] = el} className="relative">
                                  <input type="text" value={productSearchTerms[index] || ''}
                                    onChange={(e) => { if (!isFullEditAllowed) return; setProductSearchTerms(prev => ({ ...prev, [index]: e.target.value })); setShowProductDropdown(prev => ({ ...prev, [index]: true })); }}
                                    onFocus={() => isFullEditAllowed && setShowProductDropdown(prev => ({ ...prev, [index]: true }))}
                                    placeholder="Search product..." disabled={!isFullEditAllowed}
                                    className={`w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-red-500 ${!isFullEditAllowed ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                                  />
                                  {(selectedProduct || item.productId) && !showProductDropdown[index] && (
                                    <div className="absolute inset-0 px-3 py-2 bg-white border border-red-500 rounded-lg text-[12px] font-['Poppins',sans-serif] flex items-center justify-between pointer-events-none">
                                      <span className="text-red-700 font-semibold">{selectedProduct?.product?.name || `Product #${item.productId}`}</span>
                                      <span className="text-blue-600 text-[10px] font-semibold">#{item.productId}</span>
                                    </div>
                                  )}
                                  {showProductDropdown[index] && isFullEditAllowed && (
                                    <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                                      {filteredProducts.length === 0 ? (
                                        <div className="px-3 py-2 text-[12px] text-gray-500">No products found</div>
                                      ) : filteredProducts.map(p => (
                                        <button key={p.productId} type="button" onClick={() => selectProduct(index, p)}
                                          className="w-full px-3 py-2 text-left text-[12px] font-['Poppins',sans-serif] hover:bg-red-50 border-b border-gray-100 last:border-b-0">
                                          <div className="flex items-center justify-between">
                                            <span className="font-semibold text-gray-900">{p.product?.name}</span>
                                            <span className="text-emerald-600 text-[10px] font-semibold">OnHand: {p.quantityOnHand}</span>
                                          </div>
                                        </button>
                                      ))}
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
                                  <input type="text" value={batchSearchTerms[index] || ''}
                                    onChange={(e) => { if (!isFullEditAllowed) return; setBatchSearchTerms(prev => ({ ...prev, [index]: e.target.value })); setShowBatchDropdown(prev => ({ ...prev, [index]: true })); }}
                                    onFocus={() => isFullEditAllowed && item.productId && setShowBatchDropdown(prev => ({ ...prev, [index]: true }))}
                                    placeholder={item.productId ? "Search batch..." : "Select product first"}
                                    disabled={!isFullEditAllowed || !item.productId}
                                    className={`w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-red-500 ${!isFullEditAllowed ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                                  />
                                  {item.batchId && !showBatchDropdown[index] && (
                                    <div className="absolute inset-0 px-3 py-2 bg-white border border-red-500 rounded-lg text-[12px] font-['Poppins',sans-serif] flex items-center justify-between pointer-events-none">
                                      <span className="text-red-700 font-semibold font-mono">{item.batchCode}</span>
                                      <span className="text-gray-500 text-[10px]">OnHand: {item.onHandQty}</span>
                                    </div>
                                  )}
                                  {showBatchDropdown[index] && item.productId && isFullEditAllowed && (
                                    <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                                      {filteredBatches.length === 0 ? (
                                        <div className="px-3 py-2 text-[12px] text-gray-500">No batches available</div>
                                      ) : filteredBatches.map(b => (
                                        <button key={b.id} type="button" onClick={() => selectBatch(index, b)}
                                          className="w-full px-3 py-2 text-left text-[12px] font-['Poppins',sans-serif] hover:bg-red-50 border-b border-gray-100 last:border-b-0">
                                          <div className="flex items-center justify-between">
                                            <span className="font-semibold text-gray-900 font-mono">B-{b.id}</span>
                                            <span className="text-gray-600 text-[10px]">OnHand: {b.totalOnHand || 0}</span>
                                          </div>
                                          {b.expiryDate && <div className="text-gray-500 text-[10px] mt-0.5">Exp: {new Date(b.expiryDate).toLocaleDateString()}</div>}
                                        </button>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Qty & Price */}
                            <div className="grid grid-cols-3 gap-3">
                              <div>
                                <label className="block text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-1">Available</label>
                                <div className="px-3 py-2 bg-gray-100 border border-gray-300 rounded-lg text-[12px] font-['Poppins',sans-serif] text-gray-700">{item.onHandQty || 0}</div>
                              </div>
                              <div>
                                <label className="block text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-1">Quantity <span className="text-red-500">*</span></label>
                                <input type="number" value={item.quantity}
                                  onChange={(e) => { if (!isFullEditAllowed) return; const ni = [...items]; ni[index] = { ...ni[index], quantity: parseInt(e.target.value) || 0 }; setItems(ni); }}
                                  min="1" max={item.onHandQty || 999999} disabled={!isFullEditAllowed}
                                  className={`w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-red-500 ${!isFullEditAllowed ? 'bg-gray-100 cursor-not-allowed' : ''}`}
                                />
                              </div>
                              <div>
                                <label className="block text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-1">Unit Price (₫)</label>
                                <input type="number" value={item.unitPrice} readOnly
                                  className="w-full px-3 py-2 bg-gray-100 border border-gray-300 rounded-lg text-[12px] font-['Poppins',sans-serif] text-gray-700 cursor-not-allowed" />
                              </div>
                            </div>

                            <div className="flex justify-end">
                              <div className="text-[12px] font-['Poppins',sans-serif]">
                                <span className="text-gray-600">Total: </span>
                                <span className="font-semibold text-red-600">{(item.quantity * item.unitPrice).toLocaleString('vi-VN')}₫</span>
                              </div>
                            </div>
                          </div>

                          {isFullEditAllowed && (
                            <button type="button" onClick={() => removeItem(index)}
                              className="mt-6 p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Remove item">
                              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                                <path d="M12 4L4 12M4 4L12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                            </button>
                          )}
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
                      <span className="font-bold text-red-600 text-[18px] font-['Poppins',sans-serif]">{calculateTotal().toLocaleString('vi-VN')}₫</span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </form>

        {/* Footer */}
        <div className="border-t-2 border-gray-200 p-6 bg-gray-50">
          <div className="flex items-center justify-end gap-3">
            <button type="button" onClick={onClose} disabled={loading}
              className="px-5 py-2.5 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-white transition-colors text-[13px] font-['Poppins',sans-serif] font-semibold disabled:opacity-50">
              Cancel
            </button>
            <button type="submit" onClick={handleSubmit} disabled={loading}
              className="px-6 py-2.5 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-[13px] font-['Poppins',sans-serif] font-semibold disabled:opacity-50 flex items-center gap-2 shadow-lg">
              {loading ? (
                <><svg className="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg> Saving...</>
              ) : (
                <><svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M13.5 4L6 11.5L2.5 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg> Save Changes</>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
