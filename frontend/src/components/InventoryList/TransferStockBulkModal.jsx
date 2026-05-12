import React, { useState, useEffect } from 'react';
import inventoryService from '../../services/inventoryService';
import authService from '../../services/authService';

export const TransferStockBulkModal = ({ isOpen, onClose, onSuccess }) => {
  const [step, setStep] = useState(1); // 1: Select Products, 2: Select Batches, 3: Review

  // Step 1: Product Selection
  const [allProducts, setAllProducts] = useState([]);
  const [selectedProducts, setSelectedProducts] = useState([]); // Array of product IDs
  const [productSearch, setProductSearch] = useState('');

  // Step 2: Batch Selection per Product
  const [productBatches, setProductBatches] = useState({}); // { productId: [batches] }
  const [batchSelections, setBatchSelections] = useState({}); // { detailInventoryId: { selected: bool, quantity: number } }

  // Common
  const [direction, setDirection] = useState('toShelf'); // toShelf | toWarehouse
  const [currentUser, setCurrentUser] = useState(null);
  const [currentEmployee, setCurrentEmployee] = useState(null);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    performedBy: '',
    reason: 'Bulk Stock Movement',
    notes: ''
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loadingBatches, setLoadingBatches] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchInitialData();
      resetModal();
    }
  }, [isOpen]);

  const resetModal = () => {
    setStep(1);
    setSelectedProducts([]);
    setProductBatches({});
    setBatchSelections({});
    setDirection('toShelf');
    setProductSearch('');
    setFormData({
      date: new Date().toISOString().split('T')[0],
      performedBy: '',
      reason: 'Bulk Stock Movement',
      notes: ''
    });
    setError(null);
  };

  const fetchInitialData = async () => {
    try {
      setLoading(true);

      // Get current user
      const user = authService.getUser();
      setCurrentUser(user);

      // Fetch all inventories/products
      const inventoryResponse = await inventoryService.getAllInventories();
      if (inventoryResponse.success && inventoryResponse.data) {
        setAllProducts(inventoryResponse.data.inventories || []);
      }

      if (user) {
        setFormData(prev => ({
          ...prev,
          performedBy: user.id
        }));
      }
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  // Step 1: Product Selection Handlers
  const handleProductToggle = (productId) => {
    setSelectedProducts(prev => {
      if (prev.includes(productId)) {
        return prev.filter(id => id !== productId);
      } else {
        return [...prev, productId];
      }
    });
  };

  const handleNextToBatches = async () => {
    if (selectedProducts.length === 0) {
      setError('Please select at least one product');
      return;
    }

    setLoadingBatches(true);
    setError(null);

    try {
      // Fetch batches for all selected products
      const batchesData = {};

      for (const inventoryId of selectedProducts) {
        // Find the actual product ID from the inventory
        const inventory = allProducts.find(p => (p._id || p.id) === inventoryId);
        const productId = inventory?.product?.id || inventory?.product?._id || inventory?.productId;

        if (productId) {
          const response = await inventoryService.getBatchesByProduct(productId);
          if (response.success && Array.isArray(response.data)) {
            batchesData[inventoryId] = response.data.map(b => ({
              id: String(b.id),
              expiryDate: b.expiryDate,
              mfgDate: b.mfgDate,
              quantityOnHand: b.totalOnHand,
              quantityOnShelf: b.totalOnShelf,
              costPrice: b.costPrice,
              unitPrice: b.unitPrice,
              status: b.status
            }));
          }
        }
      }
      setProductBatches(batchesData);
      setStep(2);
    } catch (err) {
      console.error('Error fetching batches:', err);
      setError('Failed to load batches');
    } finally {
      setLoadingBatches(false);
    }
  };

  // Step 2: Batch Selection Handlers
  const handleBatchToggle = (detailInventoryId) => {
    setBatchSelections(prev => ({
      ...prev,
      [detailInventoryId]: {
        selected: !prev[detailInventoryId]?.selected,
        quantity: prev[detailInventoryId]?.quantity || ''
      }
    }));
  };

  const handleBatchQuantityChange = (detailInventoryId, quantity) => {
    setBatchSelections(prev => ({
      ...prev,
      [detailInventoryId]: {
        ...(prev[detailInventoryId] || { selected: true }),
        quantity: quantity
      }
    }));
  };

  const handleNextToReview = () => {
    const selectedBatches = Object.entries(batchSelections).filter(([_, data]) => data.selected);

    if (selectedBatches.length === 0) {
      setError('Please select at least one batch');
      return;
    }

    // Validate that each product has at least one batch selected
    const productsWithoutBatches = [];
    for (const inventoryId of selectedProducts) {
      const inventory = allProducts.find(p => (p._id || p.id) === inventoryId);
      const batches = productBatches[inventoryId] || [];

      // Check if any batch from this product is selected
      const hasBatchSelected = batches.some(batch => {
        const detailId = batch._id || batch.id;
        return batchSelections[detailId]?.selected;
      });

      if (!hasBatchSelected) {
        productsWithoutBatches.push(inventory?.product?.name || 'Unknown Product');
      }
    }

    if (productsWithoutBatches.length > 0) {
      setError(`Please select at least one batch for: ${productsWithoutBatches.join(', ')}`);
      return;
    }

    // Validate quantities
    for (const [detailInventoryId, data] of selectedBatches) {
      if (!data.quantity || data.quantity <= 0) {
        setError('Please enter valid quantities for all selected batches');
        return;
      }
    }

    setError(null);
    setStep(3);
  };

  // Step 3: Submit
  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      // Prepare transfer data
      const transfers = Object.entries(batchSelections)
        .filter(([_, data]) => data.selected && data.quantity > 0)
        .map(([detailInventoryId, data]) => {
          // Find the batch details
          let batchInfo = null;
          for (const batches of Object.values(productBatches)) {
            const found = batches.find(b => (b._id || b.id) === detailInventoryId);
            if (found) {
              batchInfo = found;
              break;
            }
          }

          const quantity = parseInt(data.quantity, 10);

          return {
            detailInventoryId,
            quantity: quantity
          };
        });

      // Prepare additional data
      const additionalData = {
        date: formData.date,
        performedBy: formData.performedBy,
        reason: formData.reason,
        notes: formData.notes
      };

      // Execute transfers one by one via backend
      let succeeded = 0;
      let failed = 0;

      for (const transfer of transfers) {
        try {
          const moveQty = direction === 'toShelf' ? transfer.quantity : -transfer.quantity;
          await inventoryService.transferToShelf(
            parseInt(transfer.detailInventoryId), // batchId
            null, // locationId — null for unassigned items
            moveQty
          );
          succeeded++;
        } catch (err) {
          console.error('Transfer failed for batch:', transfer.detailInventoryId, err);
          failed++;
        }
      }

      const response = { success: true, data: { summary: { succeeded, failed } } };

      if (response.success) {
        // Show success message
        const { succeeded, failed } = response.data.summary;
        let message = `Successfully transferred ${succeeded} batch${succeeded !== 1 ? 'es' : ''}!`;

        if (failed > 0) {
          message += `\n${failed} batch${failed !== 1 ? 'es' : ''} failed.`;
        }

        alert(message);

        if (onSuccess) {
          onSuccess();
        }

        onClose();
      } else {
        setError(response.error?.message || 'Failed to transfer stock');
      }
    } catch (err) {
      console.error('Error bulk transferring:', err);
      setError(err.response?.data?.error?.message || err.message || 'Failed to transfer stock');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  // Filter products for search
  const filteredProducts = allProducts.filter(item =>
    item.product?.name?.toLowerCase().includes(productSearch.toLowerCase()) ||
    item.product?.productCode?.toLowerCase().includes(productSearch.toLowerCase())
  );

  // Calculate summary
  const selectedBatchCount = Object.values(batchSelections).filter(data => data.selected).length;
  const totalQuantity = Object.values(batchSelections)
    .filter(data => data.selected)
    .reduce((sum, data) => sum + (parseInt(data.quantity) || 0), 0);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000] p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Bulk Transfer Stock
            </h2>
            <p className="text-[12px] text-gray-500 mt-1">
              Step {step} of 3: {step === 1 ? 'Select Products' : step === 2 ? 'Select Batches' : 'Review & Confirm'}
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Progress Bar */}
        <div className="px-6 pt-4 pb-2">
          <div className="flex items-center justify-center">
            {[1, 2, 3].map((stepNum, index) => (
              <div key={stepNum} className="flex items-center">
                {/* Step Circle */}
                <div className="flex flex-col items-center">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center text-[14px] font-bold transition-all duration-300 ${stepNum < step
                      ? 'bg-emerald-500 text-white'
                      : stepNum === step
                        ? 'bg-blue-600 text-white ring-4 ring-blue-100'
                        : 'bg-gray-100 text-gray-400 border-2 border-gray-200'
                    }`}>
                    {stepNum < step ? (
                      <svg width="18" height="18" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M13.5 4L6 11.5L2.5 8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : (
                      stepNum
                    )}
                  </div>
                  <span className={`mt-2 text-[11px] font-medium whitespace-nowrap ${stepNum <= step ? 'text-blue-600' : 'text-gray-400'
                    }`}>
                    {stepNum === 1 ? 'Select Products' : stepNum === 2 ? 'Select Batches' : 'Review & Confirm'}
                  </span>
                </div>

                {/* Connector Line */}
                {index < 2 && (
                  <div className="w-24 h-1 mx-4 rounded-full overflow-hidden bg-gray-200">
                    <div
                      className={`h-full transition-all duration-500 ease-out ${stepNum < step ? 'bg-emerald-500 w-full' : 'bg-gray-200 w-0'
                        }`}
                      style={{ width: stepNum < step ? '100%' : '0%' }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px] mb-4">
              {error}
            </div>
          )}

          {/* Step 1: Product Selection */}
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <label className="block text-[13px] font-semibold text-[#212529] mb-2">
                  Transfer Direction <span className="text-red-500">*</span>
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setDirection('toShelf')}
                    className={`p-4 border-2 rounded-lg text-center transition-all ${direction === 'toShelf'
                      ? 'border-blue-600 bg-blue-50 text-blue-900'
                      : 'border-gray-300 hover:border-blue-400'
                      }`}
                  >
                    <div className="text-[14px] font-semibold mb-1">Warehouse <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline mx-1"><path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg> Shelf</div>
                    <div className="text-[11px] text-gray-600">Move to sales floor</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setDirection('toWarehouse')}
                    className={`p-4 border-2 rounded-lg text-center transition-all ${direction === 'toWarehouse'
                      ? 'border-blue-600 bg-blue-50 text-blue-900'
                      : 'border-gray-300 hover:border-blue-400'
                      }`}
                  >
                    <div className="text-[14px] font-semibold mb-1">Shelf <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline mx-1"><path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg> Warehouse</div>
                    <div className="text-[11px] text-gray-600">Return to storage</div>
                  </button>
                </div>
              </div>

              {/* Search Products */}
              <div>
                <label className="block text-[13px] font-semibold text-[#212529] mb-2">
                  Search Products
                </label>
                <input
                  type="text"
                  value={productSearch}
                  onChange={(e) => setProductSearch(e.target.value)}
                  placeholder="Search by name or code..."
                  className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Products List */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-[13px] font-semibold text-[#212529]">
                    Select Products ({selectedProducts.length} selected)
                  </label>
                  <button
                    onClick={() => setSelectedProducts(filteredProducts.map(p => p._id || p.id))}
                    className="text-[12px] text-blue-600 hover:underline"
                  >
                    Select All
                  </button>
                </div>

                <div className="border-2 border-gray-200 rounded-lg max-h-[400px] overflow-y-auto">
                  {filteredProducts.map((item) => {
                    const productId = item._id || item.id;
                    const isSelected = selectedProducts.includes(productId);
                    const hasStock = direction === 'toShelf'
                      ? item.quantityOnHand > 0
                      : item.quantityOnShelf > 0;

                    return (
                      <label
                        key={productId}
                        className={`flex items-center p-3 border-b border-gray-100 cursor-pointer hover:bg-gray-50 ${!hasStock ? 'opacity-50 cursor-not-allowed' : ''
                          }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => hasStock && handleProductToggle(productId)}
                          disabled={!hasStock}
                          className="w-4 h-4 text-blue-600 rounded"
                        />
                        <div className="ml-3 flex-1">
                          <p className="text-[13px] font-semibold text-[#212529]">
                            {item.product?.name || 'N/A'}
                          </p>
                          <p className="text-[11px] text-gray-500">
                            {item.product?.productCode} •
                            {direction === 'toShelf'
                              ? ` Warehouse: ${item.quantityOnHand}`
                              : ` Shelf: ${item.quantityOnShelf}`}
                          </p>
                        </div>
                        {!hasStock && (
                          <span className="text-[11px] text-red-600 font-semibold">No Stock</span>
                        )}
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Batch Selection */}
          {step === 2 && (
            <div className="space-y-6">
              {selectedProducts.map(inventoryId => {
                const inventory = allProducts.find(p => (p._id || p.id) === inventoryId);
                const batches = productBatches[inventoryId] || [];

                // Filter batches based on direction and expiry
                const availableBatches = batches.filter(batch => {
                  const isExpired = batch.expiryDate &&
                    new Date(batch.expiryDate) <= new Date();

                  if (direction === 'toShelf' && isExpired) return false;

                  if (direction === 'toShelf') {
                    return (batch.quantityOnHand || 0) > 0;
                  } else {
                    return (batch.quantityOnShelf || 0) > 0;
                  }
                });

                return (
                  <div key={inventoryId} className="border-2 border-gray-200 rounded-lg p-4">
                    <h3 className="text-[15px] font-semibold text-[#212529] mb-3">
                      {inventory?.product?.name || 'N/A'}
                    </h3>

                    {availableBatches.length === 0 ? (
                      <p className="text-[13px] text-gray-500">
                        {direction === 'toShelf'
                          ? 'No active batches available for transfer to shelf'
                          : 'No batches available for transfer to warehouse'}
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {availableBatches.map(batch => {
                          const detailId = batch.id;
                          const selection = batchSelections[detailId] || { selected: false, quantity: '' };

                          const maxQty = direction === 'toShelf'
                            ? (batch.quantityOnHand || 0)
                            : (batch.quantityOnShelf || 0);

                          const isExpired = batch.expiryDate &&
                            new Date(batch.expiryDate) <= new Date();

                          const isExpiringSoon = batch.expiryDate &&
                            (() => {
                              const expiryDate = new Date(batch.expiryDate);
                              const thirtyDaysFromNow = new Date();
                              thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);
                              return expiryDate <= thirtyDaysFromNow && expiryDate > new Date();
                            })();

                          return (
                            <div
                              key={detailId}
                              className={`flex items-center gap-3 p-3 border rounded-lg ${isExpired
                                ? 'border-red-300 bg-red-50'
                                : isExpiringSoon
                                  ? 'border-amber-300 bg-amber-50'
                                  : 'border-gray-200'
                                }`}
                            >
                              <input
                                type="checkbox"
                                checked={selection.selected}
                                onChange={() => handleBatchToggle(detailId)}
                                className="w-4 h-4 text-blue-600 rounded"
                              />
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  <p className="text-[13px] font-semibold text-emerald-600">
                                    Batch #{detailId}
                                  </p>
                                  {isExpired && (
                                    <span className="text-[10px] font-semibold text-red-700 bg-red-200 px-2 py-0.5 rounded">
                                      EXPIRED
                                    </span>
                                  )}
                                  {!isExpired && isExpiringSoon && (
                                    <span className="text-[10px] font-semibold text-amber-700 bg-amber-200 px-2 py-0.5 rounded">
                                      Expiring Soon
                                    </span>
                                  )}
                                </div>
                                <p className="text-[11px] text-gray-500">
                                  {direction === 'toShelf' ? 'Warehouse' : 'Shelf'}: {maxQty} units •
                                  Exp: {batch.expiryDate ? new Date(batch.expiryDate).toLocaleDateString() : 'N/A'}
                                </p>
                                {isExpired && direction === 'toWarehouse' && (
                                  <p className="text-[10px] text-red-600 mt-1 italic">
                                    Transfer to warehouse for disposal processing
                                  </p>
                                )}
                              </div>
                              {selection.selected && (
                                <input
                                  type="number"
                                  value={selection.quantity}
                                  onChange={(e) => handleBatchQuantityChange(detailId, e.target.value)}
                                  min="1"
                                  max={maxQty}
                                  placeholder="Qty"
                                  className="w-24 px-2 py-1.5 border-2 border-gray-300 rounded text-[13px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Step 3: Review */}
          {step === 3 && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h3 className="text-[14px] font-semibold text-blue-900 mb-3">Transfer Summary</h3>
                <div className="grid grid-cols-2 gap-4 text-[13px]">
                  <div>
                    <p className="text-blue-700">Direction:</p>
                    <p className="font-semibold text-blue-900">
                      {direction === 'toShelf' ? (<>Warehouse <svg width="12" height="12" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline mx-1"><path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg> Shelf</>) : (<>Shelf <svg width="12" height="12" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline mx-1"><path d="M3 8H13M13 8L9 4M13 8L9 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg> Warehouse</>)}
                    </p>
                  </div>
                  <div>
                    <p className="text-blue-700">Total Batches:</p>
                    <p className="font-semibold text-blue-900">{selectedBatchCount}</p>
                  </div>
                  <div>
                    <p className="text-blue-700">Total Quantity:</p>
                    <p className="font-semibold text-blue-900">{totalQuantity} units</p>
                  </div>
                  <div>
                    <p className="text-blue-700">Products:</p>
                    <p className="font-semibold text-blue-900">{selectedProducts.length}</p>
                  </div>
                </div>
              </div>

              {/* Batch Details */}
              <div>
                <h3 className="text-[14px] font-semibold text-[#212529] mb-2">Batch Details:</h3>
                <div className="border-2 border-gray-200 rounded-lg max-h-[250px] overflow-y-auto">
                  {Object.entries(batchSelections)
                    .filter(([_, data]) => data.selected)
                    .map(([detailId, data]) => {
                      // Find batch info
                      let batchInfo = null;
                      let inventoryInfo = null;

                      for (const [inventoryId, batches] of Object.entries(productBatches)) {
                        const found = batches.find(b => b.id === detailId);
                        if (found) {
                          batchInfo = found;
                          inventoryInfo = allProducts.find(p => (p._id || p.id) === inventoryId);
                          break;
                        }
                      }

                      return (
                        <div key={detailId} className="p-3 border-b border-gray-100 last:border-0">
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="text-[13px] font-semibold text-[#212529]">
                                {inventoryInfo?.product?.name || 'N/A'}
                              </p>
                              <p className="text-[11px] text-gray-500">
                                Batch #{detailId}
                              </p>
                            </div>
                            <p className="text-[14px] font-bold text-blue-600">
                              {data.quantity} units
                            </p>
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>

              {/* Additional Details */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] font-semibold text-[#212529] mb-2">
                    Date <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    required
                    className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-[13px] font-semibold text-[#212529] mb-2">
                    Performed By
                  </label>
                  <input
                    type="text"
                    value={currentEmployee?.fullName || currentUser?.username || 'N/A'}
                    disabled
                    className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] bg-gray-100 text-gray-600 cursor-not-allowed"
                  />
                  <p className="text-[11px] text-gray-500 mt-1">Current logged in employee</p>
                </div>
              </div>

              <div>
                <label className="block text-[13px] font-semibold text-[#212529] mb-2">
                  Reason
                </label>
                <input
                  type="text"
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-[13px] font-semibold text-[#212529] mb-2">
                  Notes
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows="3"
                  className="w-full px-3 py-2.5 border-2 border-gray-300 rounded-lg text-[13px] focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer Buttons */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200">
          <div>
            {step > 1 && (
              <button
                type="button"
                onClick={() => setStep(step - 1)}
                disabled={loading || loadingBatches}
                className="px-5 py-2.5 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-[13px] font-semibold disabled:opacity-50"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline mr-1"><path d="M10 12L6 8L10 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>Back
              </button>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading || loadingBatches}
              className="px-5 py-2.5 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-[13px] font-semibold disabled:opacity-50"
            >
              Cancel
            </button>

            {step === 1 && (
              <button
                type="button"
                onClick={handleNextToBatches}
                disabled={loading || loadingBatches || selectedProducts.length === 0}
                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-[13px] font-semibold disabled:opacity-50"
              >
                {loadingBatches ? 'Loading...' : (<>Next: Select Batches <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline ml-1"><path d="M6 4L10 8L6 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg></>)}
              </button>
            )}

            {step === 2 && (
              <button
                type="button"
                onClick={handleNextToReview}
                disabled={loading || selectedBatchCount === 0}
                className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-[13px] font-semibold disabled:opacity-50"
              >
                Next: Review <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline ml-1"><path d="M6 4L10 8L6 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </button>
            )}

            {step === 3 && (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={loading}
                className="px-5 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 text-[13px] font-semibold disabled:opacity-50 flex items-center gap-2"
              >
                {loading ? 'Processing...' : `Transfer ${totalQuantity} Units`}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
