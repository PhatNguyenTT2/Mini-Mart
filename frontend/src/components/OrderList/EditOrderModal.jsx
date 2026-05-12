import React, { useState, useEffect, useMemo } from 'react';
import orderService from '../../services/orderService';
import orderDetailService from '../../services/orderDetailService';
import customerService from '../../services/customerService';
import productService from '../../services/productService';
import inventoryService from '../../services/inventoryService';
import employeeService from '../../services/employeeService';

/**
 * EditOrderModal Component
 * 
 * Order Edit Flow:
 * 1. Load existing order data
 * 2. User can modify delivery details, fees, and status
 * 3. Order items are read-only (cannot modify after creation)
 * 4. Cannot edit delivered or cancelled orders
 * 
 * Restrictions:
 * - Cannot edit order items (product, quantity, price) after creation
 * - Cannot edit delivered or cancelled orders
 * - Can only update: delivery type, address, shipping fee, discount, notes, status
 */
export const EditOrderModal = ({ isOpen, onClose, onSuccess, order }) => {
  const [formData, setFormData] = useState({
    deliveryType: 'delivery',
    shippingAddress: '',
    shippingFee: 0,
    discount: 0,
    notes: '',
    status: 'pending',
    paymentStatus: 'pending'
  });

  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [orderDetails, setOrderDetails] = useState([]);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [fullOrder, setFullOrder] = useState(null);
  
  // Enrichment maps (resolve IDs → names)
  const [customerInfo, setCustomerInfo] = useState(null);
  const [createdByName, setCreatedByName] = useState('');

  // For editing draft order items
  const [editedItems, setEditedItems] = useState([]);
  const [itemsChanged, setItemsChanged] = useState(false);

  // Check if order can be edited
  const canEdit = order && order.status !== 'delivered' && order.status !== 'cancelled';

  // Only draft orders can edit items (add/remove/modify products)
  const canEditItems = order && order.status === 'draft';

  // Pending/shipping can only edit metadata (delivery info, fees, notes)
  const canEditMetadata = canEdit && !canEditItems;

  // Load form data when modal opens or order changes
  useEffect(() => {
    if (isOpen && order) {
      setFormData({
        deliveryType: order.deliveryType || 'delivery',
        shippingAddress: order.shippingAddress || order.address || '',
        shippingFee: order.shippingFee || 0,
        discount: order.discount || 0,
        notes: order.notes || '',
        status: order.status || 'pending',
        paymentStatus: order.paymentStatus || 'pending'
      });
      setErrors({});
      setOrderDetails([]);
      setFullOrder(null);
      setEditedItems([]);
      setItemsChanged(false);
      loadCustomers();
      loadProducts();
      loadFullOrder();
      loadOrderDetails();
    }
  }, [isOpen, order]);

  // Load full order data
  const loadFullOrder = async () => {
    const orderId = order?._id || order?.id;
    if (!orderId) return;

    try {
      const response = await orderService.getOrderById(orderId);
      const orderData = response.data?.order || response.order || null;
      setFullOrder(orderData);
      
      // Customer enrichment
      if (orderData?.customerId) {
        resolveCustomer(orderData.customerId);
      }
      // Employee enrichment for createdBy
      if (orderData?.createdBy === -1) {
        setCreatedByName('Customer (Online)');
      } else if (orderData?.createdBy && typeof orderData.createdBy === 'number') {
        resolveEmployee(orderData.createdBy);
      }
    } catch (error) {
      console.error('Failed to load full order:', error);
    }
  };

  // Resolve customer name from auth-service
  const resolveCustomer = async (customerId) => {
    try {
      const res = await customerService.getCustomerById(customerId);
      const cust = res.data?.customer || res.data || res;
      setCustomerInfo({
        fullName: cust.full_name || cust.fullName || `Customer #${customerId}`,
        phone: cust.phone || '',
        customerType: cust.customer_type || cust.customerType || 'guest'
      });
    } catch {
      setCustomerInfo({ fullName: `Customer #${customerId}`, phone: '', customerType: 'guest' });
    }
  };

  // Resolve employee name from auth-service
  const resolveEmployee = async (employeeId) => {
    try {
      const res = await employeeService.getEmployeeById(employeeId);
      const emp = res.data?.employee || res.data || res;
      setCreatedByName(emp.full_name || emp.fullName || emp.username || `User #${employeeId}`);
    } catch {
      setCreatedByName(`User #${employeeId}`);
    }
  };

  // Load customers
  const loadCustomers = async () => {
    try {
      const data = await customerService.getAllCustomers({
        limit: 100,
        isActive: true
      });
      const customersList = data.data?.customers || data.customers || [];
      setCustomers(customersList);
    } catch (error) {
      console.error('Failed to load customers:', error);
    }
  };

  // Load products — only show in-stock products (onShelf > 0)
  const loadProducts = async () => {
    try {
      const [catalogRes, inventoryRes] = await Promise.all([
        productService.getAllProducts({ limit: 200, isActive: true }),
        inventoryService.getInventorySummary()
      ]);

      const catalogProducts = catalogRes.data?.products || catalogRes.products || [];
      const inventoryData = inventoryRes.data || [];

      const inventoryMap = {};
      inventoryData.forEach(inv => {
        inventoryMap[String(inv.productId)] = {
          quantityOnHand: inv.quantityOnHand || 0,
          quantityOnShelf: inv.quantityOnShelf || 0,
          quantityAvailable: inv.quantityAvailable || 0
        };
      });

      const mergedProducts = catalogProducts.map(product => {
        const productId = String(product.id || product._id);
        return {
          ...product,
          inventory: inventoryMap[productId] || { quantityOnHand: 0, quantityOnShelf: 0, quantityAvailable: 0 }
        };
      });

      const inStockProducts = mergedProducts.filter(p => p.inventory.quantityOnShelf > 0);
      setProducts(inStockProducts);
    } catch (error) {
      console.error('Failed to load products:', error);
    }
  };

  // Load order details
  const loadOrderDetails = async () => {
    const orderId = order?._id || order?.id;
    if (!orderId) {
      console.warn('No order ID found:', order);
      return;
    }

    setLoadingDetails(true);
    try {
      const response = await orderDetailService.getDetailsByOrder(orderId);

      // Handle both microservice and legacy response formats
      const details = response.data?.details ||
        response.data?.orderDetails ||
        response.details ||
        response.data ||
        [];

      setOrderDetails(details);

      // If draft order, convert to editable items
      if (order?.status === 'draft' && details.length > 0) {
        const items = details.map(detail => {
          // Microservice: flat fields (productName, batchId)
          // Monolith: nested (product._id, batch._id)
          const productId = detail.productId || detail.product_id || detail.product?._id || detail.product?.id || detail.product;

          return {
            _id: detail.id || detail._id,
            productId: productId ? String(productId) : '',
            quantity: detail.quantity,
            unitPrice: detail.unitPrice || detail.unit_price || 0,
            productName: detail.productName || detail.product_name || detail.product?.name || ''
          };
        });
        setEditedItems(items);
      }
    } catch (error) {
      console.error('Failed to load order details:', error);
      setOrderDetails([]);
    } finally {
      setLoadingDetails(false);
    }
  };

  // Helper: Get product by ID
  const getProductById = (productId) => {
    return products.find(p => p._id === productId);
  };

  // Helper: Get product price
  const getProductPrice = (product) => {
    if (!product) return 0;
    const price = product.unitPrice;
    if (price === null || price === undefined) return 0;
    if (typeof price === 'object' && price !== null) {
      if (price.$numberDecimal) return parseFloat(price.$numberDecimal);
      return parseFloat(price.toString());
    }
    const parsed = parseFloat(price);
    return isNaN(parsed) ? 0 : parsed;
  };

  // Helper: Get available quantity (from inventory.quantityOnShelf)
  // quantityOnShelf = quantity currently on shelf available for sale
  const getAvailableQuantity = (product) => {
    if (!product) {
      console.log('getAvailableQuantity: product is null/undefined');
      return 0;
    }

    const qty = product.inventory?.quantityOnShelf ?? 0;
    return qty;
  };  // Helper: Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount || 0);
  };

  // Helper: Get available products for dropdown (on shelf + not already selected)
  const getAvailableProducts = (currentItemIndex = null) => {
    // Filter products with quantityOnShelf > 0
    const onShelfProducts = products.filter(product => {
      const qtyOnShelf = getAvailableQuantity(product);
      return qtyOnShelf > 0;
    });

    // Get list of already selected product IDs (excluding current item being edited)
    const selectedProductIds = editedItems
      .map((item, index) => {
        // Exclude current item being edited to allow changing its product
        if (currentItemIndex !== null && index === currentItemIndex) {
          return null;
        }
        return item.productId;
      })
      .filter(id => id); // Remove null/undefined

    // Filter out already selected products
    const availableProducts = onShelfProducts.filter(product => {
      const productId = product._id || product.id;
      return !selectedProductIds.includes(productId);
    });

    return availableProducts;
  };

  // === DRAFT ORDER ITEMS HANDLERS ===

  // Add new item to draft order
  const handleAddItem = () => {
    if (!canEditItems) return;

    setEditedItems([
      ...editedItems,
      { productId: '', quantity: 1, unitPrice: 0 }
    ]);
    setItemsChanged(true);
  };

  // Remove item from draft order
  const handleRemoveItem = (index) => {
    if (!canEditItems) return;

    const newItems = editedItems.filter((_, i) => i !== index);
    setEditedItems(newItems);
    setItemsChanged(true);

    // Clear related errors
    const newErrors = { ...errors };
    delete newErrors[`item_${index}_product`];
    delete newErrors[`item_${index}_quantity`];
    setErrors(newErrors);
  };

  // Update item in draft order
  const handleItemChange = (index, field, value) => {
    if (!canEditItems) return;

    const newItems = [...editedItems];
    newItems[index] = { ...newItems[index], [field]: value };

    // Auto-fill price when product is selected
    if (field === 'productId' && value) {
      const product = products.find(p => (p.id || p._id) === value);
      if (product) {
        const price = getProductPrice(product);
        newItems[index].unitPrice = price;
      }
    }

    setEditedItems(newItems);
    setItemsChanged(true);

    // Clear error
    const errorKey = `item_${index}_${field === 'productId' ? 'product' : field}`;
    if (errors[errorKey]) {
      const newErrors = { ...errors };
      delete newErrors[errorKey];
      setErrors(newErrors);
    }
  };

  // Handle form field changes
  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    // Clear error for this field
    if (errors[field]) {
      const newErrors = { ...errors };
      delete newErrors[field];
      setErrors(newErrors);
    }
  };

  // Validate form
  const validateForm = () => {
    const newErrors = {};

    // Validate shipping address for delivery orders
    if (formData.deliveryType === 'delivery' && !formData.shippingAddress.trim()) {
      newErrors.shippingAddress = 'Shipping address is required for delivery orders';
    }

    // Validate items for draft orders with changes
    if (canEditItems && itemsChanged) {
      if (editedItems.length === 0) {
        newErrors.items = 'Please add at least one item';
      }

      editedItems.forEach((item, index) => {
        if (!item.productId) {
          newErrors[`item_${index}_product`] = 'Please select a product';
        }
        if (item.quantity <= 0) {
          newErrors[`item_${index}_quantity`] = 'Quantity must be greater than 0';
        }

        // Check for duplicate products
        if (item.productId) {
          const duplicateIndex = editedItems.findIndex((otherItem, otherIndex) =>
            otherIndex !== index && otherItem.productId === item.productId
          );
          if (duplicateIndex !== -1) {
            newErrors[`item_${index}_product`] = 'Product already selected';
          }
        }

        // Check stock availability
        if (item.productId) {
          const product = products.find(p => (p.id || p._id) === item.productId);
          const available = getAvailableQuantity(product);
          if (item.quantity > available) {
            newErrors[`item_${index}_quantity`] = `Only ${available} available`;
          }
        }
      });
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Calculate subtotal from order details
  const calculateSubtotal = () => {
    // For draft orders with changes, use editedItems
    if (canEditItems && itemsChanged && editedItems.length > 0) {
      return editedItems.reduce((sum, item) => {
        return sum + (item.quantity * item.unitPrice);
      }, 0);
    }

    // For confirmed orders or unchanged draft, use orderDetails
    if (!orderDetails || orderDetails.length === 0) return 0;
    return orderDetails.reduce((sum, detail) => {
      return sum + (detail.quantity * detail.unitPrice);
    }, 0);
  };

  // Get discount percentage based on customer type
  const discountPercentage = useMemo(() => {
    if (!fullOrder?.customer) return 0;

    const discountMap = {
      'guest': 0,
      'retail': 10,
      'wholesale': 15,
      'vip': 20
    };

    return discountMap[fullOrder.customer.customerType?.toLowerCase()] || 0;
  }, [fullOrder]);

  // Calculate discount amount
  const calculateDiscount = () => {
    const subtotal = calculateSubtotal();
    return subtotal * (discountPercentage / 100);
  };

  // Calculate total
  const calculateTotal = () => {
    const subtotal = calculateSubtotal();
    const discount = calculateDiscount();
    return subtotal + Number(formData.shippingFee) - discount;
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!canEdit) {
      setErrors({ submit: 'Cannot edit delivered or cancelled orders' });
      return;
    }

    if (!validateForm()) {
      console.log('Validation failed:', errors);
      return;
    }

    setLoading(true);

    try {
      const updateData = {
        deliveryType: formData.deliveryType,
        shippingAddress: formData.deliveryType === 'delivery'
          ? formData.shippingAddress
          : undefined,
        shippingFee: Number(formData.shippingFee),
        notes: formData.notes || undefined,
        status: formData.status,
        paymentStatus: formData.paymentStatus
      };

      // Handle draft item editing via updateDraftItems API
      if (canEditItems && itemsChanged && editedItems.length > 0) {
        const validItems = editedItems.filter(item =>
          item.productId &&
          item.quantity > 0 &&
          item.unitPrice >= 0
        );

        if (validItems.length === 0) {
          setErrors({ submit: 'No valid items to update' });
          setLoading(false);
          return;
        }

        // Use updateDraftItems API (backend handles FEFO)
        const itemsPayload = validItems.map(item => {
          const product = products.find(p => (p.id || p._id) === item.productId);
          return {
            product_id: item.productId,
            product_name: product?.name || item.productName || 'Product',
            quantity: Number(item.quantity),
            unit_price: Number(item.unitPrice)
          };
        });

        await orderService.updateDraftItems(order.id || order._id, itemsPayload);
      }

      // Update metadata
      await orderService.updateOrder(order.id || order._id, updateData);

      onSuccess && onSuccess();
      handleClose();
    } catch (error) {
      console.error('Failed to update order:', error);
      setErrors({
        submit: error.response?.data?.message ||
          error.response?.data?.error?.message ||
          'Failed to update order'
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle modal close
  const handleClose = () => {
    if (!loading) {
      onClose();
    }
  };

  if (!isOpen || !order) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white z-10">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Edit Order
            </h2>
            <p className="text-[12px] text-gray-500 font-['Poppins',sans-serif] mt-1">
              Order #{order.orderNumber || 'N/A'}
            </p>
          </div>
          <button
            onClick={handleClose}
            disabled={loading}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Cannot Edit Warning */}
          {!canEdit && (
            <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg text-[13px]">
              Cannot edit delivered or cancelled orders
            </div>
          )}

          {/* Submit Error */}
          {errors.submit && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
              {errors.submit}
            </div>
          )}

          {/* Customer Info (Enriched from auth-service) */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Customer
            </label>
            <div className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] bg-gray-50 cursor-not-allowed">
              {customerInfo?.fullName || order._customerName || `Customer #${order.customerId || 'N/A'}`}
              {customerInfo?.phone ? ` - ${customerInfo.phone}` : ''}
              {customerInfo?.customerType && (
                <span className="ml-2 text-emerald-600 font-medium">({customerInfo.customerType})</span>
              )}
            </div>
            <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
              Customer cannot be changed after order creation
            </p>
          </div>

          {/* Created By Info Display (Enriched) */}
          {fullOrder?.createdBy && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <svg width="16" height="16" viewBox="0 0 20 20" fill="currentColor" className="text-blue-600">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                </svg>
                <h3 className="text-[13px] font-semibold text-blue-900">Order Created By</h3>
              </div>
              <div>
                <label className="block text-[11px] text-blue-700 mb-1">Employee</label>
                <input
                  type="text"
                  value={typeof fullOrder.createdBy === 'object'
                    ? (fullOrder.createdBy.fullName || 'N/A')
                    : (createdByName || `User #${fullOrder.createdBy}`)}
                  disabled
                  className="w-full px-3 py-2 border-2 border-blue-300 rounded-lg text-[13px] bg-blue-100 text-blue-900 cursor-not-allowed font-semibold"
                />
              </div>
            </div>
          )}

          {/* Status Selection */}
          <div className="grid grid-cols-2 gap-4">
            {/* Order Status */}
            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Order Status <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.status}
                onChange={(e) => handleChange('status', e.target.value)}
                disabled={!canEdit || loading}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                <option value="draft">Draft</option>
                <option value="pending">Pending</option>
                <option value="shipping">Shipping</option>
                <option value="delivered">Delivered</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>

            {/* Payment Status */}
            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Payment Status <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.paymentStatus}
                onChange={(e) => handleChange('paymentStatus', e.target.value)}
                disabled={!canEdit || loading}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              >
                <option value="pending">Pending</option>
                <option value="paid">Paid</option>
                <option value="failed">Failed</option>
                <option value="refunded">Refunded</option>
              </select>
            </div>
          </div>

          {/* Delivery Type */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Delivery Type <span className="text-red-500">*</span>
            </label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="delivery"
                  checked={formData.deliveryType === 'delivery'}
                  onChange={(e) => handleChange('deliveryType', e.target.value)}
                  disabled={!canEdit || loading}
                  className="w-4 h-4 text-emerald-600 focus:ring-emerald-500 disabled:opacity-50"
                />
                <span className="text-[13px] font-['Poppins',sans-serif] text-[#212529]">
                  Delivery
                </span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  value="pickup"
                  checked={formData.deliveryType === 'pickup'}
                  onChange={(e) => handleChange('deliveryType', e.target.value)}
                  disabled={!canEdit || loading}
                  className="w-4 h-4 text-emerald-600 focus:ring-emerald-500 disabled:opacity-50"
                />
                <span className="text-[13px] font-['Poppins',sans-serif] text-[#212529]">
                  Pickup
                </span>
              </label>
            </div>
          </div>

          {/* Shipping Address (conditional) */}
          {formData.deliveryType === 'delivery' && (
            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Shipping Address <span className="text-red-500">*</span>
              </label>
              <textarea
                value={formData.shippingAddress}
                onChange={(e) => handleChange('shippingAddress', e.target.value)}
                placeholder="Enter delivery address"
                rows={3}
                disabled={!canEdit || loading}
                className={`w-full px-3 py-2 border ${errors.shippingAddress ? 'border-red-500' : 'border-gray-300'} rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none disabled:bg-gray-100 disabled:cursor-not-allowed`}
              />
              {errors.shippingAddress && (
                <p className="mt-1 text-[11px] text-red-500 font-['Poppins',sans-serif]">
                  {errors.shippingAddress}
                </p>
              )}
            </div>
          )}

          {/* Order Items (Read-only) */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Order Items
            </label>

            {/* Info Banner */}
            {canEditItems ? (
              <div className="mb-3 p-2 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-[11px] text-blue-700 flex items-center gap-1">
                  <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <span>Draft order - You can add, remove, or modify items</span>
                </p>
              </div>
            ) : (
              <div className="mb-3 p-2 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-[11px] text-amber-700 flex items-center gap-1">
                  <svg width="14" height="14" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                  <span>Confirmed order - Items are locked. Only delivery info and fees can be changed.</span>
                </p>
              </div>
            )}

            {/* Items List */}
            {loadingDetails ? (
              <div className="text-center py-8">
                <svg className="animate-spin h-8 w-8 text-emerald-600 mx-auto" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <p className="text-[12px] text-gray-500 mt-2">Loading order items...</p>
              </div>
            ) : canEditItems ? (
              // Editable items for draft orders
              <div className="space-y-3">
                {editedItems.map((item, index) => {
                  const selectedProduct = products.find(p => (p.id || p._id) === item.productId);
                  const availableQty = getAvailableQuantity(selectedProduct);
                  const availableProducts = getAvailableProducts(index);

                  // Debug: Log product matching
                  if (index === 0) {
                    console.log('Product matching debug:', {
                      itemProductId: item.productId,
                      totalProducts: products.length,
                      availableProducts: availableProducts.length,
                      firstProduct: products[0] ? {
                        id: products[0].id,
                        _id: products[0]._id,
                        name: products[0].name
                      } : 'No products',
                      selectedProduct: selectedProduct ? selectedProduct.name : 'NOT FOUND'
                    });
                  }

                  return (
                    <div key={index} className="flex gap-2 items-start p-3 bg-white rounded-lg border-2 border-blue-200">
                      <div className="flex-1 grid grid-cols-3 gap-3">
                        {/* Product Selection */}
                        <div>
                          <label className="block text-[11px] font-medium text-gray-700 mb-1">
                            Product <span className="text-red-500">*</span>
                          </label>
                          <select
                            value={item.productId || ''}
                            onChange={(e) => handleItemChange(index, 'productId', e.target.value)}
                            className={`w-full px-3 py-2 border ${errors[`item_${index}_product`] ? 'border-red-500' : 'border-gray-300'} rounded-lg text-[12px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-blue-500`}
                          >
                            <option value="">-- Select Product --</option>
                            {/* Show currently selected product even if not in available list */}
                            {item.productId && selectedProduct && !availableProducts.find(p => (p._id || p.id) === item.productId) && (
                              <option value={item.productId}>
                                {selectedProduct.name} ({selectedProduct.productCode}) - Selected
                              </option>
                            )}
                            {/* Show available products with stock info */}
                            {availableProducts.map(product => {
                              const productId = product._id || product.id;
                              const qtyOnShelf = getAvailableQuantity(product);
                              return (
                                <option key={productId} value={productId}>
                                  {product.name} ({product.productCode}) - {qtyOnShelf} in stock
                                </option>
                              );
                            })}
                          </select>
                          {errors[`item_${index}_product`] && (
                            <p className="mt-1 text-[10px] text-red-500">{errors[`item_${index}_product`]}</p>
                          )}
                          {selectedProduct && (
                            <p className="mt-1 text-[10px] text-emerald-600">
                              Available: {availableQty} units
                            </p>
                          )}
                        </div>

                        {/* Quantity */}
                        <div>
                          <label className="block text-[11px] font-medium text-gray-700 mb-1">
                            Quantity <span className="text-red-500">*</span>
                          </label>
                          <input
                            type="number"
                            min="1"
                            value={item.quantity}
                            onChange={(e) => handleItemChange(index, 'quantity', e.target.value)}
                            className={`w-full px-3 py-2 border ${errors[`item_${index}_quantity`] ? 'border-red-500' : 'border-gray-300'} rounded-lg text-[12px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-blue-500`}
                          />
                          {errors[`item_${index}_quantity`] && (
                            <p className="mt-1 text-[10px] text-red-500">{errors[`item_${index}_quantity`]}</p>
                          )}
                        </div>

                        {/* Unit Price (Read-only) */}
                        <div>
                          <label className="block text-[11px] font-medium text-gray-700 mb-1">Unit Price</label>
                          <input
                            type="text"
                            value={formatCurrency(item.unitPrice)}
                            disabled
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] bg-gray-50 cursor-not-allowed"
                          />
                          <p className="mt-1 text-[10px] text-gray-600">
                            Total: {formatCurrency(item.quantity * item.unitPrice)}
                          </p>
                        </div>
                      </div>

                      {/* Remove Button */}
                      <button
                        type="button"
                        onClick={() => handleRemoveItem(index)}
                        className="mt-7 p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Remove item"
                      >
                        <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                  );
                })}

                {/* Add Item Button */}
                {(() => {
                  const availableProducts = getAvailableProducts();
                  const hasAvailableProducts = availableProducts.length > 0;

                  return (
                    <>
                      <button
                        type="button"
                        onClick={handleAddItem}
                        disabled={!hasAvailableProducts}
                        className={`w-full py-3 border-2 border-dashed rounded-lg text-[13px] flex items-center justify-center gap-2 transition-colors ${hasAvailableProducts
                          ? 'border-blue-300 text-blue-600 hover:bg-blue-50 cursor-pointer'
                          : 'border-gray-300 text-gray-400 cursor-not-allowed bg-gray-50'
                          }`}
                      >
                        <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
                        </svg>
                        Add Item
                      </button>
                      {!hasAvailableProducts && (
                        <p className="text-[11px] text-amber-600 text-center">
                          No more products available to add (all products either out of stock or already selected)
                        </p>
                      )}
                    </>
                  );
                })()}

                {errors.items && (
                  <p className="text-[11px] text-red-500">{errors.items}</p>
                )}
              </div>
            ) : (
              // Read-only items for confirmed orders
              <div className="space-y-3">
                {orderDetails && orderDetails.length > 0 ? (
                  orderDetails.map((detail, index) => {
                    const product = detail.product;
                    const batch = detail.batch;

                    return (
                      <div key={index} className="flex gap-2 items-start p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <div className="flex-1 grid grid-cols-4 gap-2">
                          {/* Product Name */}
                          <div>
                            <label className="block text-[11px] text-gray-600 mb-1">Product</label>
                            <div className="text-[12px] font-medium text-gray-900">
                              {product?.name || 'N/A'}
                            </div>
                            {product?.productCode && (
                              <div className="text-[10px] text-gray-500 mt-0.5">
                                Code: {product.productCode}
                              </div>
                            )}
                          </div>

                          {/* Batch Info */}
                          <div>
                            <label className="block text-[11px] text-gray-600 mb-1">Batch</label>
                            <div className="text-[12px] text-gray-900">
                              {batch?.batchCode || batch?.batchNumber || 'N/A'}
                            </div>
                            {batch?.expiryDate && (
                              <div className="text-[10px] text-gray-500 mt-0.5">
                                Exp: {new Date(batch.expiryDate).toLocaleDateString('en-US')}
                              </div>
                            )}
                          </div>

                          {/* Quantity */}
                          <div>
                            <label className="block text-[11px] text-gray-600 mb-1">Quantity</label>
                            <div className="text-[12px] font-medium text-gray-900">
                              {detail.quantity}
                            </div>
                          </div>

                          {/* Unit Price */}
                          <div>
                            <label className="block text-[11px] text-gray-600 mb-1">Unit Price</label>
                            <div className="text-[12px] font-medium text-gray-900">
                              {formatCurrency(detail.unitPrice)}
                            </div>
                            <div className="text-[10px] text-gray-500 mt-0.5">
                              Total: {formatCurrency(detail.quantity * detail.unitPrice)}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center py-4 text-gray-500 text-[12px]">
                    No items found
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Fees & Discount */}
          <div className="grid grid-cols-2 gap-4">
            {/* Shipping Fee */}
            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Shipping Fee
              </label>
              <input
                type="number"
                value={formData.shippingFee}
                onChange={(e) => handleChange('shippingFee', e.target.value)}
                min="0"
                step="1000"
                disabled={!canEdit || loading}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
            </div>

            {/* Discount Info (Auto-calculated) */}
            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Discount (Auto)
              </label>
              <div className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif]">
                {discountPercentage}%
                {fullOrder?.customer && (
                  <span className="text-gray-500 ml-1">
                    ({fullOrder.customer.customerType || 'N/A'})
                  </span>
                )}
              </div>
              <p className="mt-1 text-[10px] text-gray-500 font-['Poppins',sans-serif]">
                Guest: 0% | Retail: 10% | Wholesale: 15% | VIP: 20%
              </p>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Notes (Optional)
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              placeholder="Enter any additional notes"
              rows={3}
              maxLength={500}
              disabled={!canEdit || loading}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
            <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
              {formData.notes.length}/500
            </p>
          </div>

          {/* Order Summary */}
          <div className="bg-gradient-to-r from-emerald-50 to-blue-50 p-4 rounded-lg border border-emerald-200">
            <h3 className="text-[14px] font-semibold font-['Poppins',sans-serif] text-[#212529] mb-3">
              Order Summary
            </h3>
            <div className="space-y-2">
              <div className="flex justify-between text-[13px] font-['Poppins',sans-serif]">
                <span className="text-gray-600">Subtotal:</span>
                <span className="text-gray-900">{formatCurrency(calculateSubtotal())}</span>
              </div>
              <div className="flex justify-between text-[13px] font-['Poppins',sans-serif]">
                <span className="text-gray-600">Shipping Fee:</span>
                <span className="text-gray-900">{formatCurrency(formData.shippingFee)}</span>
              </div>
              {discountPercentage > 0 && (
                <div className="flex justify-between text-[13px] font-['Poppins',sans-serif]">
                  <span className="text-gray-600">Discount ({discountPercentage}%):</span>
                  <span className="text-red-600">- {formatCurrency(calculateDiscount())}</span>
                </div>
              )}
              <div className="border-t border-emerald-300 pt-2 mt-2">
                <div className="flex justify-between">
                  <span className="text-[16px] font-bold font-['Poppins',sans-serif] text-[#212529]">Total:</span>
                  <span className="text-[18px] font-bold font-['Poppins',sans-serif] text-emerald-600">
                    {formatCurrency(calculateTotal())}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={handleClose}
              disabled={loading}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !canEdit}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Updating...
                </>
              ) : (
                'Update Order'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
