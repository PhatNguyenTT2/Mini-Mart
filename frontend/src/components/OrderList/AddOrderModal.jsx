import React, { useState, useEffect, useMemo } from 'react';
import orderService from '../../services/orderService';
import customerService from '../../services/customerService';
import productService from '../../services/productService';
import inventoryService from '../../services/inventoryService';
import customerDiscountSettingsService from '../../services/customerDiscountSettingsService';
import api from '../../services/api';

/**
 * AddOrderModal Component
 * 
 * Order Creation Flow:
 * 1. User selects customer
 * 2. User adds products with quantities (NO batch selection needed)
 * 3. Backend automatically selects batch using FEFO (First Expired First Out)
 * 4. System picks the batch on shelf with nearest expiry date
 * 5. OrderDetail is created with auto-selected batch
 * 
 * Price Logic:
 * - unitPrice comes from Product master data (reference price)
 * - unitPrice is saved in OrderDetail (price at transaction time)
 * - Batch selection is transparent to user
 */
export const AddOrderModal = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    customerId: '',
    deliveryType: 'delivery',
    shippingAddress: '',
    shippingFee: 0,
    notes: '',
    items: []
  });

  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [availableBatches, setAvailableBatches] = useState({}); // { productId: [batches] }
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});

  // Customer discount settings from system configuration
  const [customerDiscounts, setCustomerDiscounts] = useState({
    retail: 10,
    wholesale: 15,
    vip: 20
  });

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setFormData({
        customerId: '',
        deliveryType: 'delivery',
        shippingAddress: '',
        shippingFee: 0,
        notes: '',
        items: []
      });
      setErrors({});
      loadCustomers();
      loadProducts();
      loadCustomerDiscounts();
    }
  }, [isOpen]);

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
      setErrors(prev => ({ ...prev, loadCustomers: 'Failed to load customers' }));
    }
  };

  // Load customer discount settings from system configuration
  const loadCustomerDiscounts = async () => {
    try {
      const response = await customerDiscountSettingsService.getActiveDiscounts();
      if (response.success && response.data) {
        setCustomerDiscounts(response.data);
        console.log('Loaded customer discounts:', response.data);
      }
    } catch (error) {
      console.error('Error loading customer discounts:', error);
      // Keep default values if fetch fails
    }
  };

  // Load products with inventory — only show products with onShelf > 0
  const loadProducts = async () => {
    try {
      // 1. Fetch products from catalog (name, category, price)
      const [catalogRes, inventoryRes] = await Promise.all([
        productService.getAllProducts({ limit: 200, isActive: true }),
        inventoryService.getInventorySummary()
      ]);

      const catalogProducts = catalogRes.data?.products || catalogRes.products || [];
      const inventoryData = inventoryRes.data || [];

      // 2. Build inventory lookup: productId → { quantityOnShelf, quantityOnHand }
      const inventoryMap = {};
      inventoryData.forEach(inv => {
        inventoryMap[String(inv.productId)] = {
          quantityOnHand: inv.quantityOnHand || 0,
          quantityOnShelf: inv.quantityOnShelf || 0,
          quantityAvailable: inv.quantityAvailable || 0
        };
      });

      // 3. Merge: attach inventory to each product
      const mergedProducts = catalogProducts.map(product => {
        const productId = String(product.id || product._id);
        return {
          ...product,
          inventory: inventoryMap[productId] || { quantityOnHand: 0, quantityOnShelf: 0, quantityAvailable: 0 }
        };
      });

      // 4. Filter: only products with onShelf > 0 (sellable from store shelf)
      const inStockProducts = mergedProducts.filter(p => p.inventory.quantityOnShelf > 0);

      setProducts(inStockProducts);
    } catch (error) {
      console.error('Failed to load products:', error);
      setErrors(prev => ({ ...prev, loadProducts: 'Failed to load products' }));
    }
  };  // Helper: Get product unit price (handle Decimal128)
  const getProductPrice = (product) => {
    if (!product) return 0;

    const price = product.unitPrice;

    // Handle null or undefined
    if (price === null || price === undefined) return 0;

    // Handle Decimal128 object
    if (typeof price === 'object' && price !== null) {
      // Check if it's a Decimal128 object with $numberDecimal property
      if (price.$numberDecimal) {
        return parseFloat(price.$numberDecimal);
      }
      // Try toString() for other object types
      return parseFloat(price.toString());
    }

    // Handle number or string
    const parsed = parseFloat(price);
    return isNaN(parsed) ? 0 : parsed;
  };

  // Helper: Get current price after discount (FEFO batch discount)
  const getCurrentPrice = (product) => {
    if (!product) return 0;

    const basePrice = getProductPrice(product);
    const discountPercentage = product.discountPercentage || 0;

    if (discountPercentage > 0) {
      return basePrice * (1 - discountPercentage / 100);
    }

    return basePrice;
  };

  // Helper: Get discount percentage
  const getDiscountPercentage = (product) => {
    if (!product) return 0;
    return product.discountPercentage || 0;
  };

  // Helper: Get batch unit price (handle Decimal128)
  const getBatchPrice = (batch) => {
    if (!batch) return 0;

    const price = batch.unitPrice;

    // Handle null or undefined
    if (price === null || price === undefined) return 0;

    // Handle Decimal128 object
    if (typeof price === 'object' && price !== null) {
      if (price.$numberDecimal) {
        return parseFloat(price.$numberDecimal);
      }
      return parseFloat(price.toString());
    }

    // Handle number or string
    const parsed = parseFloat(price);
    return isNaN(parsed) ? 0 : parsed;
  };

  // Helper: Get batch discount percentage
  const getBatchDiscountPercentage = (batch) => {
    if (!batch) return 0;
    return batch.discountPercentage || 0;
  };

  // Helper: Get current batch price after discount
  const getCurrentBatchPrice = (batch) => {
    if (!batch) return 0;

    const basePrice = getBatchPrice(batch);
    const discountPercentage = getBatchDiscountPercentage(batch);

    if (discountPercentage > 0) {
      return basePrice * (1 - discountPercentage / 100);
    }

    return basePrice;
  };

  // Helper: Get available quantity on shelf
  const getAvailableQuantity = (product) => {
    if (!product || !product.inventory) return 0;
    return product.inventory.quantityOnShelf ??
      product.inventory.quantityAvailable ??
      0;
  };

  // Helper: Check if product is perishable (replaces hard-coded 'fresh' check)
  const isFreshProduct = (product) => {
    if (!product) return false;
    return product.isPerishable || product.category?.isPerishable || product.category?.is_perishable || false;
  };

  // Load available batches for fresh product (via inventory API)
  const loadBatchesForProduct = async (productId) => {
    try {
      const response = await api.get(`/inventory/batches/${productId}`);
      const data = response.data;

      if (data.success && Array.isArray(data.data)) {
        // Filter batches with stock on shelf > 0 and not expired
        const availableBatchesForProduct = data.data.filter(batch => {
          return batch.totalOnShelf > 0 && batch.status === 'active'
            && new Date(batch.expiryDate) > new Date();
        }).sort((a, b) => new Date(a.expiryDate) - new Date(b.expiryDate)); // FEFO sort

        setAvailableBatches(prev => ({
          ...prev,
          [productId]: availableBatchesForProduct
        }));
      }
    } catch (error) {
      console.error('Error loading batches for product:', error);
    }
  };

  // Add new item to order
  const handleAddItem = () => {
    setFormData({
      ...formData,
      items: [
        ...formData.items,
        {
          productId: '',
          quantity: 1, // For non-fresh products
          unitPrice: 0,
          batchSelections: [] // For fresh products: [{ batchId, quantity }]
        }
      ]
    });
  };

  // Remove item from order
  const handleRemoveItem = (index) => {
    const newItems = formData.items.filter((_, i) => i !== index);
    setFormData({ ...formData, items: newItems });

    // Clear related errors
    const newErrors = { ...errors };
    delete newErrors[`item_${index}_product`];
    delete newErrors[`item_${index}_quantity`];
    delete newErrors[`item_${index}_price`];
    setErrors(newErrors);
  };

  // Add batch selection for fresh product
  const handleAddBatchSelection = (itemIndex) => {
    const newItems = [...formData.items];
    if (!newItems[itemIndex].batchSelections) {
      newItems[itemIndex].batchSelections = [];
    }
    newItems[itemIndex].batchSelections.push({ batchId: '', quantity: 1, unitPrice: 0 });
    setFormData({ ...formData, items: newItems });
  };

  // Remove batch selection
  const handleRemoveBatchSelection = (itemIndex, batchIndex) => {
    const newItems = [...formData.items];
    newItems[itemIndex].batchSelections = newItems[itemIndex].batchSelections.filter((_, i) => i !== batchIndex);
    setFormData({ ...formData, items: newItems });
  };

  // Update batch selection
  const handleBatchSelectionChange = (itemIndex, batchIndex, field, value) => {
    const newItems = [...formData.items];
    const item = newItems[itemIndex];

    // Update the field
    item.batchSelections[batchIndex][field] = value;

    // If batchId is selected, store the batch's unit price
    if (field === 'batchId' && value) {
      const productBatches = availableBatches[item.productId] || [];
      const selectedBatch = productBatches.find(b => (b.id || b._id) === value);

      if (selectedBatch) {
        const batchPrice = getCurrentBatchPrice(selectedBatch);
        item.batchSelections[batchIndex].unitPrice = batchPrice;

        console.log('Batch price stored:', {
          batchCode: selectedBatch.batchCode,
          basePrice: getBatchPrice(selectedBatch),
          discount: getBatchDiscountPercentage(selectedBatch) + '%',
          currentPrice: batchPrice
        });
      }
    }

    setFormData({ ...formData, items: newItems });
  };

  // Update item (product selection or quantity change)
  const handleItemChange = (index, field, value) => {
    console.log('handleItemChange called:', { index, field, value });

    const newItems = [...formData.items];
    newItems[index] = { ...newItems[index], [field]: value };

    // Auto-fill price when product is selected
    if (field === 'productId' && value) {
      console.log('Looking for product with ID:', value);
      console.log('Total products available:', products.length);

      // Find product by id or _id
      const product = products.find(p => (p.id || p._id) === value);
      console.log('Selected product:', {
        searchId: value,
        found: !!product,
        productName: product?.name,
        rawUnitPrice: product?.unitPrice,
        typeOfPrice: typeof product?.unitPrice,
        isFresh: product ? isFreshProduct(product) : false
      });

      if (product) {
        const currentPrice = getCurrentPrice(product);
        newItems[index].unitPrice = currentPrice;

        // Load batches if product is fresh
        if (isFreshProduct(product)) {
          loadBatchesForProduct(value);
          newItems[index].batchSelections = [];
          newItems[index].quantity = 0;
        } else {
          newItems[index].batchSelections = [];
          newItems[index].quantity = 1;
        }
      }
    }

    setFormData({ ...formData, items: newItems });

    // Clear error for this field
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

    // Validate customer
    if (!formData.customerId) {
      newErrors.customerId = 'Please select a customer';
    }

    // Validate shipping address for delivery orders
    if (formData.deliveryType === 'delivery' && !formData.shippingAddress.trim()) {
      newErrors.shippingAddress = 'Shipping address is required for delivery orders';
    }

    // Validate items
    if (formData.items.length === 0) {
      newErrors.items = 'Please add at least one item';
    }

    formData.items.forEach((item, index) => {
      // Validate product selection
      if (!item.productId) {
        newErrors[`item_${index}_product`] = 'Please select a product';
      }

      const product = products.find(p => (p.id || p._id) === item.productId);

      // Validate batch selections for fresh products
      if (item.productId && product && isFreshProduct(product)) {
        if (!item.batchSelections || item.batchSelections.length === 0) {
          newErrors[`item_${index}_batches`] = 'Please add at least one batch for fresh products';
        } else {
          // Validate each batch selection
          item.batchSelections.forEach((batchSel, batchIdx) => {
            if (!batchSel.batchId) {
              newErrors[`item_${index}_batch_${batchIdx}_id`] = 'Please select a batch';
            }
            if (!batchSel.quantity || batchSel.quantity <= 0) {
              newErrors[`item_${index}_batch_${batchIdx}_qty`] = 'Quantity must be greater than 0';
            }

            // Check batch availability
            if (batchSel.batchId) {
              const productBatches = availableBatches[item.productId] || [];
              const selectedBatch = productBatches.find(b => (b.id || b._id) === batchSel.batchId);
              const batchQty = selectedBatch?.detailInventory?.quantityOnShelf || 0;

              if (batchQty > 0 && batchSel.quantity > batchQty) {
                newErrors[`item_${index}_batch_${batchIdx}_qty`] = `Only ${batchQty} available`;
              }
            }
          });
        }
      } else if (item.productId && product && !isFreshProduct(product)) {
        // For non-fresh products, validate quantity
        if (item.quantity <= 0) {
          newErrors[`item_${index}_quantity`] = 'Quantity must be greater than 0';
        }

        // Check total availability (FEFO auto-allocation)
        const availableQty = getAvailableQuantity(product);
        if (availableQty > 0 && item.quantity > availableQty) {
          newErrors[`item_${index}_quantity`] = `Only ${availableQty} available`;
        }
      }

      // Validate price
      if (item.unitPrice < 0) {
        newErrors[`item_${index}_price`] = 'Price cannot be negative';
      }
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Calculate subtotal
  const calculateSubtotal = () => {
    return formData.items.reduce((sum, item) => {
      const product = products.find(p => (p.id || p._id) === item.productId);

      // For fresh products with batch selections, sum using batch-specific prices
      if (product && isFreshProduct(product) && item.batchSelections && item.batchSelections.length > 0) {
        const batchTotal = item.batchSelections.reduce((batchSum, batchSel) => {
          // Use batch-specific unitPrice stored in batchSelection
          const batchPrice = batchSel.unitPrice || 0;
          return batchSum + ((Number(batchSel.quantity) || 0) * batchPrice);
        }, 0);
        return sum + batchTotal;
      }

      // For non-fresh products, use the single quantity with product price
      return sum + ((Number(item.quantity) || 0) * item.unitPrice);
    }, 0);
  };

  // Get discount percentage based on customer type (memoized to avoid repeated calculations)
  const discountPercentage = useMemo(() => {
    if (!formData.customerId || customers.length === 0) return 0;

    const customer = customers.find(c => {
      const customerId = c.id || c._id;
      return customerId === formData.customerId ||
        (typeof customerId === 'object' ? customerId.toString() === formData.customerId : false);
    });

    if (!customer) return 0;

    // Use dynamic discount rates from system configuration
    const customerType = customer.customerType?.toLowerCase();

    if (customerType === 'guest') return 0;
    if (customerType === 'retail') return customerDiscounts.retail;
    if (customerType === 'wholesale') return customerDiscounts.wholesale;
    if (customerType === 'vip') return customerDiscounts.vip;

    return 0;
  }, [formData.customerId, customers, customerDiscounts]);

  // Get customer info for display (memoized)
  const selectedCustomerInfo = useMemo(() => {
    if (!formData.customerId || customers.length === 0) return null;
    return customers.find(c => {
      const customerId = c.id || c._id;
      return customerId === formData.customerId ||
        (typeof customerId === 'object' ? customerId.toString() === formData.customerId : false);
    });
  }, [formData.customerId, customers]);

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

    if (!validateForm()) {
      return;
    }

    setLoading(true);

    try {
      const orderData = {
        customer_id: Number(formData.customerId),
        delivery_type: formData.deliveryType,
        address: formData.deliveryType === 'delivery'
          ? formData.shippingAddress
          : '',
        shipping_fee: Number(formData.shippingFee),
        discount_percentage: discountPercentage,
        items: formData.items.flatMap(item => {
          const product = products.find(p => (p.id || p._id) === item.productId);

          // Fresh products: manual batch selection → send batch_id
          if (product && isFreshProduct(product) && item.batchSelections && item.batchSelections.length > 0) {
            return item.batchSelections.map(batchSel => ({
              product_id: product.id || product._id,
              product_name: product.name,
              batch_id: Number(batchSel.batchId),
              quantity: Number(batchSel.quantity),
              unit_price: Number(batchSel.unitPrice || item.unitPrice)
            }));
          }

          // Non-fresh: NO batch_id → backend FEFO auto-allocate
          return [{
            product_id: product?.id || product?._id,
            product_name: product?.name || 'Product',
            quantity: Number(item.quantity),
            unit_price: Number(item.unitPrice)
          }];
        })
      };

      await orderService.createOrder(orderData);
      onSuccess && onSuccess();
      handleClose();
    } catch (error) {
      console.error('Failed to create order:', error);
      setErrors({
        submit: error.response?.data?.message ||
          error.response?.data?.error?.message ||
          'Failed to create order'
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

  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount || 0);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white z-10">
          <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
            Create New Order
          </h2>
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
          {/* Submit Error */}
          {errors.submit && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
              {errors.submit}
            </div>
          )}
          {/* Customer Selection */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Customer <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.customerId}
              onChange={(e) => {
                const value = e.target.value;
                console.log('Customer selected:', value);
                handleChange('customerId', value);
              }}
              className={`w-full px-3 py-2 border ${errors.customerId ? 'border-red-500' : 'border-gray-300'} rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500`}
            >
              <option value="">Select customer</option>
              {customers.map((customer) => {
                const customerId = customer.id || customer._id;
                return (
                  <option key={customerId} value={customerId}>
                    {customer.fullName} {customer.phone ? `- ${customer.phone}` : ''} ({customer.customerType || 'N/A'})
                  </option>
                );
              })}
            </select>
            {errors.customerId && (
              <p className="mt-1 text-[11px] text-red-500 font-['Poppins',sans-serif]">
                {errors.customerId}
              </p>
            )}
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
                  className="w-4 h-4 text-emerald-600 focus:ring-emerald-500"
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
                  className="w-4 h-4 text-emerald-600 focus:ring-emerald-500"
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
                className={`w-full px-3 py-2 border ${errors.shippingAddress ? 'border-red-500' : 'border-gray-300'} rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none`}
              />
              {errors.shippingAddress && (
                <p className="mt-1 text-[11px] text-red-500 font-['Poppins',sans-serif]">
                  {errors.shippingAddress}
                </p>
              )}
            </div>
          )}

          {/* Order Items Section */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529]">
                Order Items <span className="text-red-500">*</span>
              </label>
              <button
                type="button"
                onClick={handleAddItem}
                className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[12px] font-['Poppins',sans-serif] font-medium flex items-center gap-1"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Add Item
              </button>
            </div>
            {/* Items List */}
            <div className="space-y-4">
              {formData.items.map((item, index) => {
                const product = products.find(p => (p.id || p._id) === item.productId);
                const availableQty = getAvailableQuantity(product);
                const isFresh = product && isFreshProduct(product);
                const productBatches = item.productId ? (availableBatches[item.productId] || []) : [];

                // Debug logging
                if (item.productId && isFresh) {
                  console.log('Rendering item #', index, ':', {
                    productId: item.productId,
                    productName: product?.name,
                    isFresh,
                    batchesAvailable: productBatches.length,
                    batchCodes: productBatches.map(b => b.batchCode)
                  });
                }

                return (
                  <div key={index} className="p-4 bg-white rounded-lg border-2 border-blue-200 space-y-3">
                    {/* Header with Product Selection and Remove Button */}
                    <div className="flex gap-2 items-start">
                      <div className="flex-1">
                        <label className="block text-[11px] font-medium text-gray-700 mb-1">
                          Product <span className="text-red-500">*</span>
                        </label>
                        <select
                          value={item.productId}
                          onChange={(e) => handleItemChange(index, 'productId', e.target.value)}
                          className={`w-full px-3 py-2 border ${errors[`item_${index}_product`] ? 'border-red-500' : 'border-gray-300'} rounded-lg text-[12px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-blue-500`}
                        >
                          <option value="">-- Select Product --</option>
                          {products
                            .filter(prod => {
                              const pid = String(prod.id || prod._id);
                              // Keep current item's product visible, hide others already selected
                              const selectedByOthers = formData.items
                                .filter((_, i) => i !== index)
                                .map(i => String(i.productId));
                              return !selectedByOthers.includes(pid);
                            })
                            .map((prod) => {
                            const onShelf = getAvailableQuantity(prod);
                            const productId = prod.id || prod._id;
                            const categoryLabel = isFreshProduct(prod) ? ' [Fresh]' : '';
                            const discount = getDiscountPercentage(prod);
                            const discountLabel = discount > 0 ? ` -${discount}%` : '';
                            return (
                              <option key={productId} value={productId}>
                                {prod.name}{categoryLabel}{discountLabel} ({onShelf} in stock)
                              </option>
                            );
                          })}
                        </select>
                        {errors[`item_${index}_product`] && (
                          <p className="mt-1 text-[10px] text-red-500">{errors[`item_${index}_product`]}</p>
                        )}
                        {product && (
                          <div className="mt-1 space-y-0.5">
                            {!isFresh && (
                              <p className="text-[10px] text-emerald-600">
                                Available: {availableQty} units
                              </p>
                            )}
                            {getDiscountPercentage(product) > 0 && (
                              <p className="text-[10px] text-red-600 font-semibold">
                                {getDiscountPercentage(product)}% OFF - Current Price: {formatCurrency(getCurrentPrice(product))}
                              </p>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Unit Price (Read-only) */}
                      <div className="w-40">
                        <label className="block text-[11px] font-medium text-gray-700 mb-1">
                          Unit Price
                          {product && getDiscountPercentage(product) > 0 && (
                            <span className="ml-1 text-red-600 font-semibold">-{getDiscountPercentage(product)}%</span>
                          )}
                        </label>
                        <input
                          type="text"
                          value={formatCurrency(item.unitPrice)}
                          disabled
                          className={`w-full px-3 py-2 border rounded-lg text-[12px] cursor-not-allowed ${product && getDiscountPercentage(product) > 0
                            ? 'bg-red-50 border-red-300 text-red-700 font-semibold'
                            : 'bg-gray-50 border-gray-300'
                            }`}
                        />
                        {product && getDiscountPercentage(product) > 0 && (
                          <p className="mt-0.5 text-[9px] text-gray-500 line-through">
                            Was: {formatCurrency(getProductPrice(product))}
                          </p>
                        )}
                      </div>

                      {/* Remove Button */}
                      <button
                        type="button"
                        onClick={() => handleRemoveItem(index)}
                        className="mt-6 p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        title="Remove item"
                      >
                        <svg width="18" height="18" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>

                    {/* Batch Selections for Fresh Products */}
                    {isFresh && (
                      <div className="mt-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="block text-[11px] font-semibold text-orange-700">
                            Batch Selections <span className="text-red-500">*</span>
                          </label>
                          <button
                            type="button"
                            onClick={() => handleAddBatchSelection(index)}
                            className="px-2 py-1 bg-orange-100 text-orange-700 rounded hover:bg-orange-200 text-[11px] font-medium flex items-center gap-1"
                          >
                            <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                              <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                            Add Batch
                          </button>
                        </div>

                        {errors[`item_${index}_batches`] && (
                          <p className="text-[10px] text-red-500">{errors[`item_${index}_batches`]}</p>
                        )}

                        {/* Batch Selections List */}
                        <div className="space-y-2 ml-4 border-l-2 border-orange-200 pl-3">
                          {(!item.batchSelections || item.batchSelections.length === 0) && (
                            <p className="text-[11px] text-gray-500 italic">No batches selected. Click "Add Batch" to add.</p>
                          )}

                          {item.batchSelections && item.batchSelections.map((batchSel, batchIdx) => {
                            const selectedBatch = productBatches.find(b => (b.id || b._id) === batchSel.batchId);
                            return (
                              <div key={batchIdx} className="flex gap-2 items-start p-2 bg-orange-50 rounded border border-orange-200">
                                <div className="flex-1 grid grid-cols-2 gap-2">
                                  {/* Batch Dropdown */}
                                  <div>
                                    <select
                                      value={batchSel.batchId}
                                      onChange={(e) => handleBatchSelectionChange(index, batchIdx, 'batchId', e.target.value)}
                                      className={`w-full px-2 py-1.5 border ${errors[`item_${index}_batch_${batchIdx}_id`] ? 'border-red-500' : 'border-orange-300'} rounded text-[11px] focus:outline-none focus:ring-1 focus:ring-orange-500`}
                                    >
                                      <option value="">-- Select Batch --</option>
                                      {productBatches.map((batch) => {
                                        const batchId = batch.id;
                                        const qtyOnShelf = batch.totalOnShelf || 0;
                                        const expiryDate = new Date(batch.expiryDate);
                                        const today = new Date();
                                        const daysToExpiry = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));

                                        return (
                                          <option key={batchId} value={batchId}>
                                            Batch #{batchId} ({daysToExpiry}d, {qtyOnShelf}u) - {formatCurrency(batch.unitPrice)}/u
                                          </option>
                                        );
                                      })}
                                    </select>
                                    {errors[`item_${index}_batch_${batchIdx}_id`] && (
                                      <p className="mt-0.5 text-[9px] text-red-500">{errors[`item_${index}_batch_${batchIdx}_id`]}</p>
                                    )}
                                    {selectedBatch && (
                                      <div className="mt-0.5 space-y-0.5">
                                        <p className="text-[9px] text-gray-600">
                                          Exp: {new Date(selectedBatch.expiryDate).toLocaleDateString('vi-VN')} • {selectedBatch.totalOnShelf || 0} units
                                        </p>
                                        <p className="text-[9px] text-emerald-600">
                                          Price: {formatCurrency(selectedBatch.unitPrice)}/unit
                                        </p>
                                      </div>
                                    )}
                                  </div>

                                  {/* Quantity Input */}
                                  <div>
                                    <input
                                      type="number"
                                      value={batchSel.quantity}
                                      onChange={(e) => handleBatchSelectionChange(index, batchIdx, 'quantity', e.target.value)}
                                      min="1"
                                      placeholder="Qty"
                                      className={`w-full px-2 py-1.5 border ${errors[`item_${index}_batch_${batchIdx}_qty`] ? 'border-red-500' : 'border-orange-300'} rounded text-[11px] focus:outline-none focus:ring-1 focus:ring-orange-500`}
                                    />
                                    {errors[`item_${index}_batch_${batchIdx}_qty`] && (
                                      <p className="mt-0.5 text-[9px] text-red-500">{errors[`item_${index}_batch_${batchIdx}_qty`]}</p>
                                    )}
                                    {selectedBatch && batchSel.quantity && (
                                      <p className="mt-0.5 text-[9px] text-gray-600">
                                        Total: {formatCurrency(batchSel.quantity * (batchSel.unitPrice || 0))}
                                      </p>
                                    )}
                                  </div>
                                </div>

                                {/* Remove Batch Button */}
                                <button
                                  type="button"
                                  onClick={() => handleRemoveBatchSelection(index, batchIdx)}
                                  className="mt-0.5 p-1 text-red-600 hover:bg-red-100 rounded transition-colors"
                                  title="Remove batch"
                                >
                                  <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                    <path d="M5.5 5.5A.5.5 0 016 6v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm2.5 0a.5.5 0 01.5.5v6a.5.5 0 01-1 0V6a.5.5 0 01.5-.5zm3 .5a.5.5 0 00-1 0v6a.5.5 0 001 0V6z" />
                                    <path fillRule="evenodd" d="M14.5 3a1 1 0 01-1 1H13v9a2 2 0 01-2 2H5a2 2 0 01-2-2V4h-.5a1 1 0 01-1-1V2a1 1 0 011-1H6a1 1 0 011-1h2a1 1 0 011 1h3.5a1 1 0 011 1v1zM4.118 4L4 4.059V13a1 1 0 001 1h6a1 1 0 001-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z" />
                                  </svg>
                                </button>
                              </div>
                            );
                          })}
                        </div>

                        {/* Total Summary for Fresh Product */}
                        {item.batchSelections && item.batchSelections.length > 0 && (
                          <div className="mt-2 p-2 bg-orange-100 rounded border border-orange-300">
                            <p className="text-[11px] font-semibold text-orange-900">
                              Total Quantity: {item.batchSelections.reduce((sum, bs) => sum + (Number(bs.quantity) || 0), 0)} units
                              {' • '}
                              Total Amount: {formatCurrency(item.batchSelections.reduce((sum, bs) => sum + ((Number(bs.quantity) || 0) * (bs.unitPrice || 0)), 0))}
                            </p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Quantity for Non-Fresh Products */}
                    {!isFresh && item.productId && (
                      <div className="flex gap-2">
                        <div className="flex-1">
                          <label className="block text-[11px] font-medium text-gray-700 mb-1">
                            Quantity <span className="text-red-500">*</span>
                          </label>
                          <input
                            type="number"
                            value={item.quantity}
                            onChange={(e) => handleItemChange(index, 'quantity', e.target.value)}
                            min="1"
                            className={`w-full px-3 py-2 border ${errors[`item_${index}_quantity`] ? 'border-red-500' : 'border-gray-300'} rounded-lg text-[12px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-blue-500`}
                          />
                          {errors[`item_${index}_quantity`] && (
                            <p className="mt-1 text-[10px] text-red-500">{errors[`item_${index}_quantity`]}</p>
                          )}
                        </div>
                        <div className="w-40">
                          <label className="block text-[11px] font-medium text-gray-700 mb-1">Total</label>
                          <input
                            type="text"
                            value={formatCurrency(item.quantity * item.unitPrice)}
                            disabled
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] bg-gray-50 cursor-not-allowed font-semibold"
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {
              errors.items && (
                <p className="text-[11px] text-red-500">{errors.items}</p>
              )
            }
          </div>

          {/* Fees */}
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
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            {/* Discount Info (Auto-calculated) */}
            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Discount (Auto)
              </label>
              <div className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif]">
                {discountPercentage}%
                {selectedCustomerInfo && (
                  <span className="text-gray-500 ml-1">
                    ({selectedCustomerInfo.customerType || 'N/A'})
                  </span>
                )}
              </div>
              <p className="mt-1 text-[10px] text-gray-500 font-['Poppins',sans-serif]">
                Guest: 0% | Retail: {customerDiscounts.retail}% | Wholesale: {customerDiscounts.wholesale}% | VIP: {customerDiscounts.vip}%
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
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
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
              disabled={loading}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50 flex items-center gap-2"
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
                'Create Order'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
