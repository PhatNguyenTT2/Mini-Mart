import React, { useState } from 'react';
import { X, Package, Calendar, DollarSign, AlertCircle, Clock, ShoppingCart, Minus, Plus, Check } from 'lucide-react';

export const POSBatchSelectModal = ({
  isOpen,
  productData,
  onClose,
  onBatchSelected
}) => {
  // Single batch selection with quantity
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [quantity, setQuantity] = useState(1);
  const [filterStatus, setFilterStatus] = useState('all'); // 'all', 'expiring', 'normal'

  if (!isOpen || !productData) return null;

  const { product, batches: allBatches } = productData;

  // Helper: Get batch quantity on shelf (handles both API formats)
  const getBatchQuantityOnShelf = (batch) => {
    if (!batch) return 0;
    return batch.detailInventory?.quantityOnShelf
      || batch.totalOnShelf
      || batch.quantityOnShelf
      || 0;
  };

  // Filter: Only show batches with quantityOnShelf > 0 (currently being sold)
  // Sort by expiry date (FEFO - First Expire First Out)
  const batches = (allBatches || [])
    .filter(batch => {
      const onShelf = getBatchQuantityOnShelf(batch);
      return onShelf > 0;
    })
    .sort((a, b) => {
      if (!a.expiryDate) return 1;
      if (!b.expiryDate) return -1;
      return new Date(a.expiryDate) - new Date(b.expiryDate);
    });

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  const formatVND = (amount) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount);
  };

  // Helper: Get days until expiry
  const getDaysUntilExpiry = (expiryDate) => {
    if (!expiryDate) return null;
    const today = new Date();
    const expiry = new Date(expiryDate);
    const diffTime = expiry - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  // Helper: Get expiry status with styling
  const getExpiryStatus = (expiryDate) => {
    const days = getDaysUntilExpiry(expiryDate);
    if (days === null) return { color: 'gray', text: 'No expiry', icon: null, status: 'normal' };
    if (days < 0) return { color: 'red', text: `Expired ${Math.abs(days)}d ago`, icon: <AlertCircle className="w-4 h-4" />, status: 'expired' };
    if (days === 0) return { color: 'red', text: 'Expires today!', icon: <AlertCircle className="w-4 h-4" />, status: 'expiring' };
    if (days <= 7) return { color: 'red', text: `${days}d left`, icon: <AlertCircle className="w-4 h-4" />, status: 'expiring' };
    if (days <= 30) return { color: 'amber', text: `${days}d left`, icon: <Clock className="w-4 h-4" />, status: 'expiring' };
    return { color: 'green', text: `${days}d left`, icon: <Clock className="w-4 h-4" />, status: 'normal' };
  };

  // Helper: Get batch unit price (handle Decimal128)
  const getBatchPrice = (batch) => {
    if (!batch) return 0;
    const price = batch.unitPrice;
    if (price === null || price === undefined) return 0;
    if (typeof price === 'object' && price !== null) {
      if (price.$numberDecimal) {
        return parseFloat(price.$numberDecimal);
      }
      return parseFloat(price.toString());
    }
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

  // Filter batches based on selected status
  const getFilteredBatches = () => {
    if (filterStatus === 'all') return batches;
    return batches.filter(batch => {
      const status = getExpiryStatus(batch.expiryDate).status;
      return status === filterStatus;
    });
  };

  // Count batches by status
  const getCounts = () => {
    const counts = { all: batches.length, expiring: 0, normal: 0 };
    batches.forEach(batch => {
      const status = getExpiryStatus(batch.expiryDate).status;
      if (status === 'expiring' || status === 'expired') {
        counts.expiring++;
      } else {
        counts.normal++;
      }
    });
    return counts;
  };

  const filteredBatches = getFilteredBatches();
  const counts = getCounts();

  const handleQuantityChange = (value) => {
    if (!selectedBatch) return;
    const maxQty = getBatchQuantityOnShelf(selectedBatch);
    const newQty = Math.max(1, Math.min(value, maxQty));
    setQuantity(newQty);
  };

  const handleConfirm = () => {
    if (!onBatchSelected || !selectedBatch) {
      alert('Please select a batch');
      return;
    }
    if (quantity <= 0) {
      alert('Quantity must be greater than 0');
      return;
    }
    onBatchSelected(selectedBatch, quantity);
    setSelectedBatch(null);
    setQuantity(1);
    onClose();
  };

  const handleBatchSelect = (batch) => {
    setSelectedBatch(batch);
    setQuantity(1);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between bg-gradient-to-r from-emerald-50 to-blue-50">
          <div className="flex items-center gap-4">
            {product.image && (
              <img
                src={product.image}
                alt={product.name}
                className="w-14 h-14 object-cover rounded-lg border-2 border-white shadow-sm"
              />
            )}
            <div>
              <h2 className="text-xl font-semibold text-gray-900">Select Batch</h2>
              <p className="text-sm text-gray-600 mt-0.5">
                {product.name} {product.barcode ? `(${product.barcode})` : ''}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {batches.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Package className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500 font-medium">No batches available on shelf</p>
                <p className="text-xs text-gray-400 mt-1">All batches are in warehouse or out of stock</p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Filter Tabs */}
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  onClick={() => setFilterStatus('all')}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${filterStatus === 'all'
                    ? 'bg-gray-800 text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                >
                  All ({counts.all})
                </button>
                <button
                  onClick={() => setFilterStatus('expiring')}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${filterStatus === 'expiring'
                    ? 'bg-amber-500 text-white'
                    : 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                    }`}
                >
                  Expiring Soon ({counts.expiring})
                </button>
                <button
                  onClick={() => setFilterStatus('normal')}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${filterStatus === 'normal'
                    ? 'bg-emerald-600 text-white'
                    : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                    }`}
                >
                  Normal ({counts.normal})
                </button>
              </div>

              {/* Summary */}
              <div className={`border rounded-lg p-4 ${counts.expiring > 0
                ? 'bg-amber-50 border-amber-200'
                : 'bg-blue-50 border-blue-200'
                }`}>
                <div className="flex items-center justify-between text-sm">
                  <span className={`font-medium ${counts.expiring > 0 ? 'text-amber-900' : 'text-blue-900'}`}>
                    {counts.expiring > 0 && `${counts.expiring} batch(es) expiring soon - Consider FEFO`}
                    {counts.expiring === 0 && `Total batches available: ${batches.length}`}
                  </span>
                  <span className={counts.expiring > 0 ? 'text-amber-700' : 'text-blue-700'}>
                    Showing: {filteredBatches.length} | Total qty: {filteredBatches.reduce((sum, b) => sum + (b.detailInventory?.quantityOnShelf || 0), 0)} units
                  </span>
                </div>
              </div>

              {/* No results for filter */}
              {filteredBatches.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <Package className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm">No batches match this filter</p>
                </div>
              )}

              {/* Batch Cards */}
              {filteredBatches.map((batch) => {
                const onShelf = getBatchQuantityOnShelf(batch);
                const hasDiscount = getBatchDiscountPercentage(batch) > 0;
                const finalPrice = getCurrentBatchPrice(batch);
                const expiryStatus = getExpiryStatus(batch.expiryDate);
                const isSelected = selectedBatch?.id === batch.id;

                return (
                  <div
                    key={batch.id}
                    onClick={() => handleBatchSelect(batch)}
                    className={`border-2 rounded-lg p-4 transition-all cursor-pointer ${isSelected
                      ? 'border-emerald-500 bg-emerald-50 ring-2 ring-emerald-200 shadow-md'
                      : expiryStatus.status === 'expiring' || expiryStatus.status === 'expired'
                        ? 'border-amber-300 bg-amber-50/30 hover:border-amber-400'
                        : 'border-gray-200 hover:border-emerald-400 hover:shadow-md'
                      }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      {/* Batch Code */}
                      <div className="flex items-center gap-3">
                        {/* Selection indicator */}
                        <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${isSelected
                          ? 'bg-emerald-500 border-emerald-500'
                          : 'border-gray-300'
                          }`}>
                          {isSelected && <Check className="w-4 h-4 text-white" />}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm font-semibold text-gray-900">
                              Batch #{batch.id}
                            </span>
                            {hasDiscount && (
                              <span className="bg-red-100 text-red-700 text-xs font-semibold px-2 py-0.5 rounded">
                                -{getBatchDiscountPercentage(batch)}% OFF
                              </span>
                            )}
                            {isSelected && (
                              <span className="bg-emerald-500 text-white text-xs font-semibold px-2 py-0.5 rounded">
                                Selected
                              </span>
                            )}
                          </div>
                          {batch.notes && (
                            <p className="text-xs text-gray-500 mt-1">{batch.notes}</p>
                          )}
                        </div>
                      </div>

                      {/* Quantity Badge */}
                      <div className="bg-emerald-100 text-emerald-800 px-3 py-1 rounded-full text-sm font-semibold">
                        {onShelf} units
                      </div>
                    </div>

                    {/* Details Grid */}
                    <div className="grid grid-cols-2 gap-4 ml-9">
                      {/* Price */}
                      <div className="flex items-center gap-2">
                        <DollarSign className="w-4 h-4 text-gray-400" />
                        <div className="flex flex-col">
                          <span className="text-xs text-gray-500">Price</span>
                          {hasDiscount ? (
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-bold text-red-600">
                                {formatVND(finalPrice)}
                              </span>
                              <span className="text-xs text-gray-400 line-through">
                                {formatVND(getBatchPrice(batch))}
                              </span>
                            </div>
                          ) : (
                            <span className="text-sm font-semibold text-gray-900">
                              {formatVND(getBatchPrice(batch))}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Expiry Date */}
                      <div className="flex items-center gap-2">
                        <Calendar className={`w-4 h-4 ${expiryStatus.status === 'expired' || expiryStatus.status === 'expiring' ? 'text-amber-500' : 'text-gray-400'}`} />
                        <div className="flex flex-col">
                          <span className="text-xs text-gray-500">Expiry Date</span>
                          <div className="flex items-center gap-2">
                            <span className={`text-sm font-semibold ${expiryStatus.status === 'expired' || expiryStatus.status === 'expiring' ? 'text-amber-700' : 'text-gray-900'}`}>
                              {formatDate(batch.expiryDate)}
                            </span>
                            {expiryStatus.icon && (
                              <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full ${expiryStatus.status === 'expired'
                                ? 'bg-red-100 text-red-700'
                                : 'bg-amber-100 text-amber-700'
                                }`}>
                                {expiryStatus.icon}
                                <span className="text-xs font-medium">
                                  {expiryStatus.text}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Manufacturing Date */}
                      {batch.mfgDate && (
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-gray-400" />
                          <div className="flex flex-col">
                            <span className="text-xs text-gray-500">Mfg Date</span>
                            <span className="text-sm font-semibold text-gray-900">
                              {formatDate(batch.mfgDate)}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Quantity Selection */}
          {selectedBatch && (
            <div className="mt-6 p-5 bg-gradient-to-br from-emerald-50 to-blue-50 border-2 border-emerald-300 rounded-lg">
              <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                <ShoppingCart className="w-5 h-5 text-emerald-600" />
                Add to Cart
              </h3>

              <div className="mb-4 p-3 bg-white rounded-lg border border-emerald-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono font-bold text-gray-900">Batch #{selectedBatch.id}</span>
                  {getBatchDiscountPercentage(selectedBatch) > 0 && (
                    <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-semibold">
                      -{getBatchDiscountPercentage(selectedBatch)}% OFF
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Expiry: {formatDate(selectedBatch.expiryDate)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Package className="w-3.5 h-3.5" />
                    <span>Available: {getBatchQuantityOnShelf(selectedBatch)} units</span>
                  </div>
                </div>
              </div>

              {/* Quantity Controls */}
              <div className="mb-4">
                <label className="block text-sm font-bold text-gray-700 mb-3">
                  Quantity
                </label>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => handleQuantityChange(quantity - 1)}
                    className="w-12 h-12 bg-white border-2 border-emerald-500 text-emerald-600 rounded-lg font-bold text-xl hover:bg-emerald-50 transition-colors flex items-center justify-center"
                  >
                    <Minus className="w-5 h-5" />
                  </button>

                  <input
                    type="number"
                    value={quantity}
                    onChange={(e) => handleQuantityChange(parseInt(e.target.value) || 1)}
                    min="1"
                    max={getBatchQuantityOnShelf(selectedBatch)}
                    className="w-28 h-12 text-center text-2xl font-bold border-2 border-emerald-300 rounded-lg focus:border-emerald-500 focus:outline-none"
                  />

                  <button
                    onClick={() => handleQuantityChange(quantity + 1)}
                    className="w-12 h-12 bg-white border-2 border-emerald-500 text-emerald-600 rounded-lg font-bold text-xl hover:bg-emerald-50 transition-colors flex items-center justify-center"
                  >
                    <Plus className="w-5 h-5" />
                  </button>

                  <span className="text-sm text-gray-600">
                    / {getBatchQuantityOnShelf(selectedBatch)} units on shelf
                  </span>
                </div>
              </div>

              {/* Subtotal */}
              <div className="pt-4 border-t-2 border-emerald-400">
                <div className="flex justify-between items-center">
                  <span className="text-lg text-gray-700 font-semibold">Subtotal:</span>
                  <span className="text-3xl font-bold text-emerald-600">
                    {formatVND(getCurrentBatchPrice(selectedBatch) * quantity)}
                  </span>
                </div>
                {getBatchDiscountPercentage(selectedBatch) > 0 && (
                  <div className="mt-2 text-right">
                    <span className="text-sm text-gray-500 line-through">
                      {formatVND(getBatchPrice(selectedBatch) * quantity)}
                    </span>
                    <span className="ml-2 text-sm text-red-600 font-semibold">
                      (Save {formatVND((getBatchPrice(selectedBatch) - getCurrentBatchPrice(selectedBatch)) * quantity)})
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-600">Sorted by expiry date (FEFO - First Expire First Out)</span>
            <div className="flex items-center gap-3">
              <button
                onClick={onClose}
                className="px-5 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-100 transition-colors text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={!selectedBatch}
                className={`px-6 py-2.5 rounded-lg font-bold text-white transition-all text-sm flex items-center gap-2 ${selectedBatch
                  ? 'bg-emerald-600 hover:bg-emerald-700 shadow-lg hover:shadow-xl'
                  : 'bg-gray-300 cursor-not-allowed'
                  }`}
              >
                <ShoppingCart className="w-4 h-4" />
                {selectedBatch ? `Add ${quantity} to Cart` : 'Select a Batch'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
