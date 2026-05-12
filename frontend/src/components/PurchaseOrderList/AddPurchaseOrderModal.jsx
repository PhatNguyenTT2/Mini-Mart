import React, { useState, useEffect, useRef } from 'react';
import productService from '../../services/productService';
import supplierService from '../../services/supplierService';
import purchaseOrderService from '../../services/purchaseOrderService';

/**
 * AddPurchaseOrderModal
 * Modal để tạo Purchase Order MỚI
 * 
 * Workflow:
 * 1. Chọn supplier (required)
 * 2. Thêm products + quantities + estimated cost prices (giá nhập dự kiến)
 * 3. Set expected delivery date (optional)
 * 4. Add shipping fee if applicable
 * 5. Add notes
 * 6. Create PO với status = 'pending' (KHÔNG stock in)
 * 
 * Note: 
 * - Giá nhập thực tế và giá bán sẽ được nhập khi "Receive Goods"
 * - Stock in chỉ được thực hiện khi "Receive Goods" sau khi approve
 */
export const AddPurchaseOrderModal = ({ isOpen, onClose, onSuccess }) => {
  const dropdownRefs = useRef({});

  const [formData, setFormData] = useState({
    supplier: '',
    orderDate: new Date().toISOString().split('T')[0],
    shippingFee: 0,
    notes: ''
  });

  const [items, setItems] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Product search states
  const [productSearchTerms, setProductSearchTerms] = useState({});
  const [showProductDropdown, setShowProductDropdown] = useState({});

  // Supplier search states
  const [supplierSearchTerm, setSupplierSearchTerm] = useState('');
  const [showSupplierDropdown, setShowSupplierDropdown] = useState(false);
  const supplierDropdownRef = useRef(null);

  // Fetch suppliers and products on mount
  useEffect(() => {
    if (isOpen) {
      fetchSuppliers();
      fetchProducts();
      resetForm();
    }
  }, [isOpen]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      // Product dropdowns
      Object.keys(showProductDropdown).forEach(index => {
        if (showProductDropdown[index] &&
          dropdownRefs.current[index] &&
          !dropdownRefs.current[index].contains(event.target)) {
          setShowProductDropdown(prev => ({ ...prev, [index]: false }));
        }
      });

      // Supplier dropdown
      if (showSupplierDropdown &&
        supplierDropdownRef.current &&
        !supplierDropdownRef.current.contains(event.target)) {
        setShowSupplierDropdown(false);
      }
    };

    if (Object.values(showProductDropdown).some(v => v) || showSupplierDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showProductDropdown, showSupplierDropdown]);

  const fetchSuppliers = async () => {
    try {
      const response = await supplierService.getActiveSuppliers();
      // Updated API returns { success: true, data: [...] }
      if (response.success && Array.isArray(response.data)) {
        setSuppliers(response.data);
      } else if (Array.isArray(response)) {
        setSuppliers(response);
      } else {
        setSuppliers([]);
      }
    } catch (err) {
      console.error('Error fetching suppliers:', err);
    }
  };

  const fetchProducts = async () => {
    try {
      const response = await productService.getAllProducts({
        isActive: true,
        limit: 1000
      });
      if (response.success && response.data?.products) {
        setProducts(response.data.products);
      }
    } catch (err) {
      console.error('Error fetching products:', err);
    }
  };

  const resetForm = () => {
    setFormData({
      supplier: '',
      orderDate: new Date().toISOString().split('T')[0],
      shippingFee: 0,
      notes: ''
    });
    setItems([]);
    setProductSearchTerms({});
    setShowProductDropdown({});
    setSupplierSearchTerm('');
    setShowSupplierDropdown(false);
    setError(null);
  };

  // Supplier selection
  const getFilteredSuppliers = () => {
    if (!supplierSearchTerm.trim()) {
      return suppliers.slice(0, 20);
    }
    const term = supplierSearchTerm.toLowerCase();
    return suppliers.filter(supplier =>
      supplier.companyName?.toLowerCase().includes(term) ||
      String(supplier.id)?.includes(term)
    );
  };

  const selectSupplier = (supplierId) => {
    const supplier = suppliers.find(s => (s.id || s._id) === supplierId);
    if (supplier) {
      setFormData({ ...formData, supplier: supplierId });
      setSupplierSearchTerm(supplier.companyName);
      setShowSupplierDropdown(false);
    }
  };

  const handleSupplierSearch = (searchTerm) => {
    setSupplierSearchTerm(searchTerm);
    setShowSupplierDropdown(true);
    if (!searchTerm) {
      setFormData({ ...formData, supplier: '' });
    }
  };

  // Product selection
  const addItem = () => {
    const newIndex = items.length;
    setItems([...items, { product: '', quantity: 1, costPrice: 0 }]);
    setProductSearchTerms({ ...productSearchTerms, [newIndex]: '' });
    setShowProductDropdown({ ...showProductDropdown, [newIndex]: false });
  };

  const removeItem = (index) => {
    const newItems = items.filter((_, i) => i !== index);
    setItems(newItems);

    // Re-index search terms and dropdowns
    const newSearchTerms = {};
    const newShowDropdown = {};
    newItems.forEach((item, newIndex) => {
      const oldIndex = newIndex >= index ? newIndex + 1 : newIndex;
      if (productSearchTerms[oldIndex]) {
        newSearchTerms[newIndex] = productSearchTerms[oldIndex];
      }
      if (showProductDropdown[oldIndex] !== undefined) {
        newShowDropdown[newIndex] = showProductDropdown[oldIndex];
      }
    });
    setProductSearchTerms(newSearchTerms);
    setShowProductDropdown(newShowDropdown);
  };

  const updateItem = (index, field, value) => {
    const newItems = [...items];
    newItems[index] = { ...newItems[index], [field]: value };
    setItems(newItems);
  };

  const handleProductSearch = (index, searchTerm) => {
    setProductSearchTerms({ ...productSearchTerms, [index]: searchTerm });
    setShowProductDropdown({ ...showProductDropdown, [index]: true });
  };

  const selectProduct = (index, productId) => {
    const product = products.find(p => (p.id || p._id) === productId);
    if (product) {
      const newItems = [...items];
      newItems[index] = {
        ...newItems[index],
        product: productId,
        costPrice: product.costPrice || product.unitPrice || 0
      };
      setItems(newItems);

      const displayText = product.productCode
        ? `${product.productCode} - ${product.name}`
        : product.name;
      setProductSearchTerms({ ...productSearchTerms, [index]: displayText });
      setShowProductDropdown({ ...showProductDropdown, [index]: false });
    }
  };

  const getFilteredProducts = (index) => {
    const searchTerm = productSearchTerms[index] || '';
    const selectedProductIds = items
      .map((item, idx) => idx !== index ? item.product : null)
      .filter(id => id);

    let filtered = products.filter(product => {
      const productId = product.id || product._id;
      if (selectedProductIds.includes(productId)) return false;
      if (!searchTerm) return true;

      const term = searchTerm.toLowerCase();
      return product.name?.toLowerCase().includes(term) ||
        product.productCode?.toLowerCase().includes(term);
    });

    return searchTerm ? filtered : filtered.slice(0, 20);
  };

  // Calculate totals (VND)
  const calculateTotal = () => {
    let subtotal = 0;
    items.forEach(item => {
      const qty = parseFloat(item.quantity) || 0;
      const price = parseFloat(item.costPrice) || 0;
      if (qty > 0 && price >= 0) {
        subtotal += qty * price;
      }
    });

    const shippingFee = parseFloat(formData.shippingFee) || 0;
    const total = subtotal + shippingFee;

    return { subtotal, shippingFee, total };
  };

  // Handle submit
  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validation
    if (!formData.supplier) {
      setError('Please select a supplier');
      return;
    }

    if (items.length === 0) {
      setError('Please add at least one product');
      return;
    }

    // Validate items
    for (let i = 0; i < items.length; i++) {
      const item = items[i];

      if (!item.product) {
        setError(`Item ${i + 1}: Please select a product`);
        return;
      }

      const qty = parseFloat(item.quantity);
      if (!item.quantity || isNaN(qty) || qty <= 0) {
        setError(`Item ${i + 1}: Please enter a positive quantity`);
        return;
      }

      const price = parseFloat(item.costPrice);
      if (item.costPrice === undefined || item.costPrice === null || isNaN(price) || price < 0) {
        setError(`Item ${i + 1}: Please enter a valid cost price`);
        return;
      }
    }

    setLoading(true);
    setError(null);

    try {
      const totals = calculateTotal();

      const poData = {
        supplierId: formData.supplier,
        items: items.map(item => {
          const product = products.find(p => (p.id || p._id) === item.product);
          return {
            productId: item.product,
            productName: product?.name || '',
            quantity: parseInt(item.quantity),
            costPrice: parseFloat(item.costPrice)
          };
        }),
        shippingFee: parseFloat(formData.shippingFee) || 0,
        notes: formData.notes || undefined
      };

      console.log('Creating PO with status=\'draft\':', poData);

      console.log('Creating PO:', poData);

      const response = await purchaseOrderService.createPurchaseOrder(poData);

      if (response.success) {
        console.log('PO created successfully:', response.data);
        if (onSuccess) {
          onSuccess(response.data);
        }
        onClose();
      }
    } catch (err) {
      console.error('Error creating purchase order:', err);
      let errorMessage = 'Failed to create purchase order. Please try again.';
      if (err.response?.data?.error?.message) {
        errorMessage = err.response.data.error.message;
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const totals = calculateTotal();
  const selectedSupplier = suppliers.find(s => (s.id || s._id) === formData.supplier);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Create New Purchase Order
            </h2>
            <p className="text-[12px] text-gray-500 font-['Poppins',sans-serif] mt-1">
              Step 1: Plan the order • Status will be "Draft"
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

          {/* Supplier Selection */}
          <div>
            <label className="block text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529] mb-2">
              Supplier <span className="text-red-500">*</span>
            </label>
            <div ref={supplierDropdownRef} className="relative">
              <input
                type="text"
                value={supplierSearchTerm}
                onChange={(e) => handleSupplierSearch(e.target.value)}
                onFocus={() => setShowSupplierDropdown(true)}
                placeholder="Search supplier by name or code..."
                required
                className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              />

              {selectedSupplier && !showSupplierDropdown && (
                <div className="absolute inset-0 px-3 py-2.5 bg-white border-2 border-emerald-500 rounded-lg text-[13px] font-['Poppins',sans-serif] flex items-center justify-between pointer-events-none">
                  <span className="text-emerald-700 font-semibold">
                    {selectedSupplier.companyName}
                  </span>
                  <span className="text-blue-600 text-[11px] font-semibold">
                    #{selectedSupplier.id}
                  </span>
                </div>
              )}

              {showSupplierDropdown && (
                <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                  {getFilteredSuppliers().length === 0 ? (
                    <div className="px-3 py-2 text-[13px] text-gray-500 font-['Poppins',sans-serif]">
                      No suppliers found
                    </div>
                  ) : (
                    getFilteredSuppliers().map(supplier => (
                      <button
                        key={supplier.id || supplier._id}
                        type="button"
                        onClick={() => selectSupplier(supplier.id || supplier._id)}
                        className="w-full px-3 py-2 text-left text-[13px] font-['Poppins',sans-serif] hover:bg-emerald-50 focus:bg-emerald-50 focus:outline-none border-b border-gray-100 last:border-b-0"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-gray-900">{supplier.companyName}</span>
                          <span className="text-blue-600 text-[11px] font-semibold">#{supplier.id}</span>
                        </div>
                        {supplier.phone && (
                          <div className="text-gray-500 text-[11px] mt-0.5">
                            {supplier.phone}
                          </div>
                        )}
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Dates */}
          <div>
            <label className="block text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529] mb-2">
              Order Date <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={formData.orderDate}
              onChange={(e) => setFormData({ ...formData, orderDate: e.target.value })}
              required
              max={new Date().toISOString().split('T')[0]}
              className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            />
          </div>

          {/* Products */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-[16px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
                Products <span className="text-red-500">*</span>
              </h3>
              <button
                type="button"
                onClick={addItem}
                className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[12px] font-['Poppins',sans-serif] font-medium flex items-center gap-1.5 transition-colors"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Add Product
              </button>
            </div>

            {items.length === 0 && (
              <div className="text-center py-8 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
                <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                  No products added yet. Click "Add Product" to start.
                </p>
              </div>
            )}

            <div className="space-y-3">
              {items.map((item, index) => {
                const selectedProduct = products.find(p => (p.id || p._id) === item.product);
                const filteredProducts = getFilteredProducts(index);

                return (
                  <div key={index} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                    {/* Product Search */}
                    <div ref={el => dropdownRefs.current[index] = el} className="flex-1 relative">
                      <input
                        type="text"
                        value={productSearchTerms[index] || ''}
                        onChange={(e) => handleProductSearch(index, e.target.value)}
                        onFocus={() => setShowProductDropdown({ ...showProductDropdown, [index]: true })}
                        placeholder="Search product by name or code..."
                        required
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />

                      {selectedProduct && !showProductDropdown[index] && (
                        <div className="absolute inset-0 px-3 py-2 bg-white border border-emerald-500 rounded-lg text-[13px] font-['Poppins',sans-serif] flex items-center justify-between pointer-events-none">
                          <span className="text-emerald-700 font-medium truncate">
                            {selectedProduct.name}
                          </span>
                          <span className="text-blue-600 font-semibold text-[11px]">
                            ${selectedProduct.costPrice || selectedProduct.unitPrice || 0}
                          </span>
                        </div>
                      )}

                      {showProductDropdown[index] && (
                        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-xl max-h-60 overflow-y-auto">
                          {filteredProducts.length === 0 ? (
                            <div className="px-3 py-2 text-[13px] text-gray-500 font-['Poppins',sans-serif]">
                              No products found
                            </div>
                          ) : (
                            filteredProducts.map(product => (
                              <button
                                key={product.id || product._id}
                                type="button"
                                onClick={() => selectProduct(index, product.id || product._id)}
                                className="w-full px-3 py-2 text-left text-[13px] font-['Poppins',sans-serif] hover:bg-emerald-50 focus:bg-emerald-50 focus:outline-none border-b border-gray-100 last:border-b-0"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="font-medium text-gray-900">{product.name}</span>
                                  <span className="text-blue-600 font-semibold text-[11px]">
                                    ${product.costPrice || product.unitPrice || 0}
                                  </span>
                                </div>
                                <div className="text-gray-500 text-[11px] mt-0.5">
                                  {product.productCode && <span>Code: {product.productCode}</span>}
                                </div>
                              </button>
                            ))
                          )}
                        </div>
                      )}
                    </div>

                    {/* Quantity */}
                    <div className="w-28">
                      <input
                        type="number"
                        value={item.quantity}
                        onChange={(e) => updateItem(index, 'quantity', e.target.value)}
                        min="1"
                        required
                        placeholder="Qty"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] text-center focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                    </div>

                    {/* Estimated Cost Price (VND) */}
                    <div className="w-36">
                      <input
                        type="number"
                        value={item.costPrice}
                        onChange={(e) => updateItem(index, 'costPrice', e.target.value)}
                        min="0"
                        step="1000"
                        required
                        placeholder="Cost Price (₫)"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] text-center focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                    </div>

                    {/* Total */}
                    <div className="w-36 text-right">
                      <div className="text-[13px] font-bold font-['Poppins',sans-serif] text-gray-900">
                        ₫{((parseFloat(item.quantity) || 0) * (parseFloat(item.costPrice) || 0)).toLocaleString('vi-VN')}
                      </div>
                    </div>

                    {/* Remove Button */}
                    <button
                      type="button"
                      onClick={() => removeItem(index)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0"
                      title="Remove item"
                    >
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M2 4H14M6 4V3C6 2.5 6.5 2 7 2H9C9.5 2 10 2.5 10 3V4M12 4V13C12 13.5 11.5 14 11 14H5C4.5 14 4 13.5 4 13V4H12Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Summary */}
          {items.length > 0 && (
            <div className="bg-emerald-50 border-2 border-emerald-200 rounded-lg p-5">
              <h4 className="text-[14px] font-semibold font-['Poppins',sans-serif] text-[#212529] mb-3">
                Order Summary (Estimated)
              </h4>
              <div className="space-y-2">
                <div className="flex justify-between text-[13px] font-['Poppins',sans-serif]">
                  <span className="text-gray-600">Subtotal (Products):</span>
                  <span className="font-semibold">₫{totals.subtotal.toLocaleString('vi-VN')}</span>
                </div>
                <div className="flex justify-between text-[13px] font-['Poppins',sans-serif] items-center">
                  <div className="flex items-center gap-1">
                    <span className="text-gray-600">Shipping Fee:</span>
                    <span className="text-[10px] text-gray-400" title="Usually free (FOB) or negotiated with supplier">
                      ⓘ
                    </span>
                  </div>
                  <input
                    type="number"
                    value={formData.shippingFee}
                    onChange={(e) => setFormData({ ...formData, shippingFee: e.target.value })}
                    min="0"
                    step="10000"
                    placeholder="0 (if free)"
                    className="w-32 px-2 py-1 border border-gray-300 rounded text-right text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div className="flex justify-between border-t-2 border-emerald-300 pt-2 mt-2">
                  <span className="font-bold text-[15px] font-['Poppins',sans-serif] text-gray-900">Estimated Total:</span>
                  <span className="font-bold text-emerald-600 text-[18px] font-['Poppins',sans-serif]">
                    ₫{totals.total.toLocaleString('vi-VN')}
                  </span>
                </div>
                <p className="text-[10px] text-gray-500 italic mt-2">
                  * Actual cost & selling prices will be entered when receiving goods
                </p>
              </div>
            </div>
          )}

          {/* Notes */}
          <div>
            <label className="block text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529] mb-2">
              Notes <span className="text-gray-400 font-normal">(Optional)</span>
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows="3"
              placeholder="Any additional notes about this purchase order..."
              className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 resize-none"
            />
          </div>
        </form>

        {/* Footer */}
        <div className="border-t-2 border-gray-200 p-6 bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="text-[12px] text-gray-600 font-['Poppins',sans-serif]">
              <p>PO will be created with status: <span className="font-semibold text-gray-600">Draft</span></p>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={loading}
                className="px-5 py-2.5 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-white transition-colors text-[13px] font-['Poppins',sans-serif] font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                type="submit"
                onClick={handleSubmit}
                disabled={loading || items.length === 0 || !formData.supplier}
                className="px-6 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-[13px] font-['Poppins',sans-serif] font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg hover:shadow-xl"
              >
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
                    Create Purchase Order
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
