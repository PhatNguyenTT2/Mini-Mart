import React, { useState, useEffect, useRef, useMemo } from 'react';
import { MapPin, X, Plus, MoveRight, ArrowRight } from 'lucide-react';
import locationService from '../../services/locationService';
import productService from '../../services/productService';

export const LocationDetailModal = ({ isOpen, location, onClose, onSuccess }) => {
  const [locationDetail, setLocationDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  // Assign form states
  const [unassignedGroups, setUnassignedGroups] = useState([]); // [{productId, items}]
  const [selectedProduct, setSelectedProduct] = useState('');
  const [selectedItem, setSelectedItem] = useState('');
  const [loadingUnassigned, setLoadingUnassigned] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [error, setError] = useState('');
  const [showAssignForm, setShowAssignForm] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [productNameMap, setProductNameMap] = useState({});

  // Move modal states
  const [showMoveModal, setShowMoveModal] = useState(false);
  const [itemToMove, setItemToMove] = useState(null);
  const [allBlocks, setAllBlocks] = useState([]);
  const [loadingBlocks, setLoadingBlocks] = useState(false);
  const [selectedTargetLocation, setSelectedTargetLocation] = useState(null);
  const [moving, setMoving] = useState(false);

  // Dropdown states
  const [activeDropdown, setActiveDropdown] = useState(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const dropdownRef = useRef(null);

  // Hover tooltip
  const [hoveredLocation, setHoveredLocation] = useState(null);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });

  // Fetch location detail when location changes
  useEffect(() => {
    if (isOpen && location?.id) {
      fetchLocationDetail(location.id);
      setShowAssignForm(false);
      setSelectedProduct('');
      setSelectedItem('');
      setUnassignedGroups([]);
      setError('');
      setSuccessMessage('');
    }
  }, [isOpen, location?.id]);

  // Filter items when product selected
  const availableItems = useMemo(() => {
    if (!selectedProduct) return [];
    const group = unassignedGroups.find(g => String(g.productId) === String(selectedProduct));
    return group?.items || [];
  }, [selectedProduct, unassignedGroups]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setActiveDropdown(null);
      }
    };
    if (activeDropdown) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [activeDropdown]);

  const fetchLocationDetail = async (locationId) => {
    try {
      setLoadingDetail(true);
      const res = await locationService.getLocationById(locationId);
      if (res.success && res.data) {
        setLocationDetail(res.data);
        // Enrich product names from catalog
        resolveProductNames(res.data.inventoryItems || []);
      }
    } catch (err) {
      console.error('Error fetching location detail:', err);
      setLocationDetail(location);
    } finally {
      setLoadingDetail(false);
    }
  };

  const resolveProductNames = async (items) => {
    const productIds = [...new Set(items.map(i => i.productId).filter(Boolean))];
    if (productIds.length === 0) return;
    try {
      const res = await productService.getAllProducts({ limit: 200 });
      const products = res.data?.products || res.products || [];
      const nameMap = {};
      products.forEach(p => { nameMap[p._id || p.id] = p.name; });
      setProductNameMap(prev => ({ ...prev, ...nameMap }));
    } catch (err) {
      console.error('Error resolving product names:', err);
    }
  };

  const fetchUnassignedItems = async () => {
    try {
      setLoadingUnassigned(true);
      const res = await locationService.getUnassignedItems();
      const data = res.success ? res.data : (Array.isArray(res) ? res : []);
      setUnassignedGroups(data);
    } catch (err) {
      console.error('Error fetching unassigned items:', err);
      setUnassignedGroups([]);
    } finally {
      setLoadingUnassigned(false);
    }
  };

  const handleAssignBatch = async () => {
    if (!selectedItem) {
      setError('Please select an inventory item to assign');
      return;
    }

    try {
      setAssigning(true);
      setError('');
      setSuccessMessage('');

      const itemId = parseInt(selectedItem);
      await locationService.assignItemToLocation(locationDetail?.id || location.id, itemId);

      setSuccessMessage('Item assigned successfully!');
      setShowAssignForm(false);
      setSelectedProduct('');
      setSelectedItem('');
      setUnassignedGroups([]);

      // Refresh location detail
      fetchLocationDetail(locationDetail?.id || location.id);
      if (onSuccess) onSuccess();

      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      console.error('Error assigning batch:', err);
      const errorData = err.response?.data?.error;
      const msg = typeof errorData === 'string' ? errorData : errorData?.message || err.message || 'Failed to assign batch';
      setError(msg);
    } finally {
      setAssigning(false);
    }
  };

  // Move Modal
  const handleOpenMoveModal = async (item) => {
    setItemToMove(item);
    setShowMoveModal(true);
    setSelectedTargetLocation(null);
    setError('');

    try {
      setLoadingBlocks(true);
      const res = await locationService.getAllBlocks();
      const blocksData = res.success ? res.data : (Array.isArray(res) ? res : []);
      setAllBlocks(blocksData);
    } catch (err) {
      console.error('Error loading blocks:', err);
      setError('Failed to load available locations');
      setAllBlocks([]);
    } finally {
      setLoadingBlocks(false);
    }
  };

  const handleMoveBatch = async () => {
    if (!selectedTargetLocation || !itemToMove) {
      setError('Please select a target location');
      return;
    }

    try {
      setMoving(true);
      setError('');

      await locationService.moveItemToLocation(
        selectedTargetLocation.id,
        itemToMove.id,
        `Relocated from ${locationDetail?.name || 'unknown'} to ${selectedTargetLocation.name}`
      );

      setSuccessMessage(`Item moved successfully to ${selectedTargetLocation.name}!`);
      setShowMoveModal(false);
      setItemToMove(null);
      setSelectedTargetLocation(null);

      fetchLocationDetail(locationDetail?.id || location.id);
      if (onSuccess) onSuccess();

      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      console.error('Error moving item:', err);
      const errorData = err.response?.data?.error;
      const msg = typeof errorData === 'string' ? errorData : errorData?.message || err.message || 'Failed to move item';
      setError(msg);
    } finally {
      setMoving(false);
    }
  };

  // Dropdown toggle
  const toggleDropdown = (itemId, event) => {
    if (activeDropdown === itemId) {
      setActiveDropdown(null);
    } else {
      const rect = event.currentTarget.getBoundingClientRect();
      setDropdownPosition({ top: rect.bottom + 4, left: rect.right - 160 });
      setActiveDropdown(itemId);
    }
  };

  // Helpers
  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('vi-VN');
  };

  const getStockStatus = (item) => {
    const total = (item.quantityOnHand || 0) + (item.quantityOnShelf || 0);
    const expiryDate = item.expiryDate ? new Date(item.expiryDate) : null;
    const now = new Date();

    if (expiryDate && expiryDate < now) {
      return <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-700 rounded-full">Expired</span>;
    }
    if (expiryDate && (expiryDate - now) < (30 * 24 * 60 * 60 * 1000)) {
      return <span className="px-2 py-1 text-xs font-medium bg-orange-100 text-orange-700 rounded-full">Expiring Soon</span>;
    }
    if (total === 0) {
      return <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded-full">Out of Stock</span>;
    }
    return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">In Stock</span>;
  };

  // Location capacity for move modal
  const getLocationCapacity = (loc) => {
    const locOccupied = loc.occupiedCapacity || 0;
    const locMax = loc.maxCapacity || 100;
    const locAvailable = locMax - locOccupied;
    const itemQty = (itemToMove?.quantityOnHand || 0) + (itemToMove?.quantityOnShelf || 0);
    const hasCapacity = locAvailable >= itemQty;
    const capacityPercent = locMax > 0 ? (locOccupied / locMax) * 100 : 0;
    const isCurrentLocation = loc.id === (locationDetail?.id || location?.id);
    const isActive = loc.isActive !== false;
    const isSelectable = isActive && !isCurrentLocation && hasCapacity;

    return { locOccupied, locMax, locAvailable, itemQty, hasCapacity, capacityPercent, isCurrentLocation, isActive, isSelectable };
  };

  // Computed values
  const occupiedCapacity = locationDetail?.occupiedCapacity || 0;
  const maxCapacity = locationDetail?.maxCapacity || 100;
  const inventoryItems = locationDetail?.inventoryItems || [];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999] p-4">
      <div className="bg-white rounded-lg shadow-2xl max-w-7xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Location {locationDetail?.name || location?.name || 'N/A'}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {locationDetail?.blockName && `Block ${locationDetail.blockName} • `}
              {locationDetail?.blockType && (
                <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full mr-2 ${
                  locationDetail.blockType === 'store_shelf' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
                }`}>
                  {locationDetail.blockType === 'store_shelf' ? 'Store Shelf' : 'Warehouse'}
                </span>
              )}
              Capacity ({locationDetail?.blockType === 'store_shelf' ? 'On Shelf' : 'On Hand'}): {occupiedCapacity} / {maxCapacity}
            </p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <X className="w-6 h-6 text-gray-500" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Success Message */}
          {successMessage && (
            <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
              <p className="text-sm text-green-600">{successMessage}</p>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {loadingDetail ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin h-8 w-8 border-4 border-emerald-500 border-t-transparent rounded-full"></div>
            </div>
          ) : (
            <>
              {/* Capacity Bar */}
              <div className="mb-6 bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Storage Capacity</span>
                  <span className="text-sm text-gray-600">{occupiedCapacity} / {maxCapacity} units</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full transition-all ${
                      (occupiedCapacity / maxCapacity) > 0.9 ? 'bg-red-500' :
                      (occupiedCapacity / maxCapacity) > 0.8 ? 'bg-yellow-500' :
                      occupiedCapacity > 0 ? 'bg-emerald-500' : 'bg-gray-300'
                    }`}
                    style={{ width: `${Math.min((occupiedCapacity / maxCapacity) * 100, 100)}%` }}
                  />
                </div>
              </div>

              {/* Current Inventory Items */}
              <div className="mb-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Inventory Items ({inventoryItems.length})
                  </h3>
                  <button
                    onClick={() => {
                      setShowAssignForm(!showAssignForm);
                      if (!showAssignForm) fetchUnassignedItems();
                    }}
                    className="flex items-center gap-2 px-3 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 text-sm font-medium"
                  >
                    <Plus className="w-4 h-4" />
                    Assign Batch
                  </button>
                </div>

                {/* Assign Form */}
                {showAssignForm && (
                  <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg space-y-3">
                    <h4 className="text-sm font-semibold text-blue-900">Assign Unassigned Inventory Item</h4>

                    {loadingUnassigned ? (
                      <p className="text-sm text-gray-500">Loading unassigned items...</p>
                    ) : unassignedGroups.length === 0 ? (
                      <p className="text-sm text-orange-600">No unassigned inventory items found. All items already have locations.</p>
                    ) : (
                      <>
                        {/* Product Select */}
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">Product (with unassigned items)</label>
                          <select
                            value={selectedProduct}
                            onChange={(e) => { setSelectedProduct(e.target.value); setSelectedItem(''); }}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                          >
                            <option value="">-- Select Product --</option>
                            {unassignedGroups.map(g => (
                              <option key={g.productId} value={g.productId}>
                                {productNameMap[g.productId] || `Product #${g.productId}`} ({g.items.length} unassigned item{g.items.length > 1 ? 's' : ''})
                              </option>
                            ))}
                          </select>
                        </div>

                        {/* Item Select */}
                        {selectedProduct && (
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">
                              Inventory Items (unassigned, with stock)
                            </label>
                            {availableItems.length === 0 ? (
                              <p className="text-sm text-orange-600">No items available for this product.</p>
                            ) : (
                              <select
                                value={selectedItem}
                                onChange={(e) => setSelectedItem(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                              >
                                <option value="">-- Select Item --</option>
                                {availableItems.map(item => (
                                  <option key={item.id} value={item.id}>
                                    Batch #{item.batchId} — Hand: {item.quantityOnHand}, Shelf: {item.quantityOnShelf}
                                    {item.expiryDate ? ` — Exp: ${formatDate(item.expiryDate)}` : ''}
                                  </option>
                                ))}
                              </select>
                            )}
                          </div>
                        )}
                      </>
                    )}

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-2">
                      <button
                        onClick={handleAssignBatch}
                        disabled={!selectedItem || assigning}
                        className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {assigning ? 'Assigning...' : 'Assign to Location'}
                      </button>
                      <button
                        onClick={() => {
                          setShowAssignForm(false);
                          setSelectedProduct('');
                          setSelectedItem('');
                          setUnassignedGroups([]);
                          setError('');
                        }}
                        className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm font-medium"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {/* Items Table */}
                {inventoryItems.length === 0 ? (
                  <div className="text-center py-8 bg-gray-50 rounded-lg border border-gray-200">
                    <MapPin className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                    <p className="text-gray-500 font-medium">No inventory items at this location</p>
                    <p className="text-sm text-gray-400 mt-1">Assign batches using the button above</p>
                  </div>
                ) : (
                  <div className="border border-gray-200 rounded-lg overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="text-left px-4 py-3 text-xs font-semibold text-gray-600 uppercase">Batch</th>
                          <th className="text-left px-4 py-3 text-xs font-semibold text-gray-600 uppercase">Product</th>
                          <th className="text-right px-4 py-3 text-xs font-semibold text-gray-600 uppercase">On Hand</th>
                          <th className="text-right px-4 py-3 text-xs font-semibold text-gray-600 uppercase">On Shelf</th>
                          <th className="text-center px-4 py-3 text-xs font-semibold text-gray-600 uppercase">Expiry</th>
                          <th className="text-center px-4 py-3 text-xs font-semibold text-gray-600 uppercase">Status</th>
                          <th className="text-center px-4 py-3 text-xs font-semibold text-gray-600 uppercase">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {inventoryItems.map(item => (
                          <tr key={item.id} className="hover:bg-gray-50">
                            <td className="px-4 py-3 text-sm font-mono text-gray-900">
                              B-{item.batchId}
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-700">
                              {productNameMap[item.productId] || `Product #${item.productId}`}
                            </td>
                            <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">
                              {item.quantityOnHand || 0}
                            </td>
                            <td className="px-4 py-3 text-sm text-right font-semibold text-emerald-600">
                              {item.quantityOnShelf || 0}
                            </td>
                            <td className="px-4 py-3 text-sm text-center text-gray-600">
                              {formatDate(item.expiryDate)}
                            </td>
                            <td className="px-4 py-3 text-center">
                              {getStockStatus(item)}
                            </td>
                            <td className="px-4 py-3 text-center relative">
                              <button
                                onClick={(e) => toggleDropdown(item.id, e)}
                                className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-600 transition-colors"
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                                  <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
                                </svg>
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Action Dropdown Portal */}
      {activeDropdown && (
        <div
          ref={dropdownRef}
          className="fixed z-[10000] bg-white rounded-lg shadow-xl border border-gray-200 py-1 w-40"
          style={{ top: dropdownPosition.top, left: dropdownPosition.left }}
        >
          <button
            onClick={() => {
              const item = inventoryItems.find(i => i.id === activeDropdown);
              if (item) handleOpenMoveModal(item);
              setActiveDropdown(null);
            }}
            className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
          >
            <MoveRight className="w-4 h-4" />
            Move Location
          </button>
        </div>
      )}

      {/* Move Modal */}
      {showMoveModal && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-[10001] p-4">
          <div className="bg-white rounded-lg shadow-2xl max-w-6xl w-full max-h-[85vh] overflow-y-auto">
            {/* Move Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white z-10">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Move Inventory Item</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Moving B-{itemToMove?.batchId} from <strong>{locationDetail?.name}</strong>
                  {selectedTargetLocation && (
                    <> <ArrowRight className="w-4 h-4 inline" /> <strong>{selectedTargetLocation.name}</strong></>
                  )}
                </p>
              </div>
              <button
                onClick={() => {
                  setShowMoveModal(false);
                  setItemToMove(null);
                  setSelectedTargetLocation(null);
                }}
                className="p-2 hover:bg-gray-100 rounded-full"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Move Body: Block-based Map */}
            <div className="p-6">
              {loadingBlocks ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
                </div>
              ) : (
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                  {allBlocks.map(block => {
                    const { rows, cols, columnGaps = [], locations = [] } = block;
                    const gridArray = Array(rows * cols).fill(null);
                    locations.forEach(loc => {
                      const pos = loc.position - 1;
                      if (pos >= 0 && pos < gridArray.length) gridArray[pos] = loc;
                    });

                    return (
                      <div key={block.id} className="bg-white rounded-lg border-2 border-gray-300 p-4">
                        <div className="mb-3 pb-2 border-b border-gray-200">
                          <div className="flex items-center gap-2">
                            <h4 className="text-lg font-bold text-gray-900">Block {block.name}</h4>
                            <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${
                              block.type === 'store_shelf' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
                            }`}>
                              {block.type === 'store_shelf' ? 'Shelf' : 'WH'}
                            </span>
                          </div>
                        </div>

                        <div className="inline-block border-2 border-gray-400 rounded-lg">
                          <div className="flex gap-0 p-2 bg-gray-300">
                            {Array.from({ length: cols }).map((_, colIdx) => {
                              const hasGapAfter = columnGaps.includes(colIdx + 1);
                              return (
                                <React.Fragment key={colIdx}>
                                  <div
                                    className="grid gap-1"
                                    style={{ gridTemplateRows: `repeat(${rows}, 45px)` }}
                                  >
                                    {Array.from({ length: rows }).map((_, rowIdx) => {
                                      const idx = colIdx * rows + rowIdx;
                                      const loc = gridArray[idx];

                                      if (!loc) {
                                        return (
                                          <div
                                            key={`empty-${rowIdx}-${colIdx}`}
                                            className="bg-gray-200 rounded border border-gray-300 opacity-30 w-[45px]"
                                          />
                                        );
                                      }

                                      const { locOccupied, locMax, locAvailable, capacityPercent, isCurrentLocation, isActive, isSelectable } = getLocationCapacity(loc);
                                      const isSelected = selectedTargetLocation?.id === loc.id;

                                      let bgColor = 'bg-white border-gray-300';
                                      let textColor = 'text-gray-900';

                                      if (isSelected) {
                                        bgColor = 'bg-blue-500 border-blue-600 ring-2 ring-blue-400';
                                        textColor = 'text-white';
                                      } else if (isCurrentLocation) {
                                        bgColor = 'bg-amber-400 border-amber-500';
                                        textColor = 'text-amber-900';
                                      } else if (!isActive) {
                                        bgColor = 'bg-gray-300 border-gray-400';
                                        textColor = 'text-gray-600';
                                      } else if (!isSelectable) {
                                        bgColor = 'bg-red-200 border-red-300';
                                        textColor = 'text-red-800';
                                      } else if (capacityPercent > 0) {
                                        bgColor = 'bg-emerald-200 border-emerald-300 hover:bg-emerald-300';
                                        textColor = 'text-emerald-900';
                                      } else {
                                        bgColor = 'bg-white border-gray-300 hover:bg-blue-50 hover:border-blue-300';
                                      }

                                      return (
                                        <div
                                          key={loc.id}
                                          onClick={() => isSelectable && setSelectedTargetLocation(loc)}
                                          onMouseEnter={(e) => {
                                            const rect = e.currentTarget.getBoundingClientRect();
                                            setHoveredLocation(loc);
                                            setTooltipPosition({ top: rect.top - 60, left: rect.left + rect.width / 2 });
                                          }}
                                          onMouseLeave={() => setHoveredLocation(null)}
                                          className={`relative rounded border-2 transition-all w-[45px] ${bgColor} ${isSelectable ? 'cursor-pointer' : 'cursor-not-allowed opacity-70'}`}
                                          title={loc.name}
                                        >
                                          <div className="absolute inset-0 flex items-center justify-center">
                                            <span className={`text-[10px] font-bold ${textColor}`}>
                                              {loc.name.split('-')[1]}
                                            </span>
                                          </div>
                                          {isCurrentLocation && (
                                            <span className="absolute top-0.5 right-0.5 text-[6px] bg-amber-600 text-white px-1 rounded font-bold">
                                              SRC
                                            </span>
                                          )}
                                        </div>
                                      );
                                    })}
                                  </div>
                                  {hasGapAfter && <div className="w-3 bg-transparent" />}
                                </React.Fragment>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Tooltip */}
              {hoveredLocation && (
                <div
                  className="fixed z-[10002] pointer-events-none"
                  style={{ top: tooltipPosition.top, left: tooltipPosition.left, transform: 'translateX(-50%)' }}
                >
                  <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-xl whitespace-nowrap">
                    <div className="font-bold">{hoveredLocation.name}</div>
                    <div className="text-gray-400">
                      {hoveredLocation.occupiedCapacity || 0} / {hoveredLocation.maxCapacity || 100}
                      {' '}({((hoveredLocation.occupiedCapacity || 0) / (hoveredLocation.maxCapacity || 100) * 100).toFixed(0)}%)
                    </div>
                  </div>
                </div>
              )}

              {/* Move Legend */}
              <div className="mt-4 bg-gray-50 rounded-lg p-4 border border-gray-200">
                <div className="flex items-center gap-6 flex-wrap text-xs">
                  <div className="flex items-center gap-1.5">
                    <div className="w-5 h-5 bg-amber-400 border-2 border-amber-500 rounded"></div>
                    <span className="text-gray-700 font-medium">Source</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-5 h-5 bg-blue-500 border-2 border-blue-600 rounded"></div>
                    <span className="text-gray-700 font-medium">Selected Target</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-5 h-5 bg-white border-2 border-gray-300 rounded"></div>
                    <span className="text-gray-700 font-medium">Available</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-5 h-5 bg-red-200 border-2 border-red-300 rounded"></div>
                    <span className="text-gray-700 font-medium">No Capacity</span>
                  </div>
                </div>
              </div>

              {/* Move Actions */}
              <div className="flex items-center justify-end gap-3 mt-6 pt-4 border-t border-gray-200">
                <button
                  onClick={() => {
                    setShowMoveModal(false);
                    setItemToMove(null);
                    setSelectedTargetLocation(null);
                  }}
                  disabled={moving}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleMoveBatch}
                  disabled={!selectedTargetLocation || moving}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {moving ? 'Moving...' : (
                    <>
                      <MoveRight className="w-4 h-4" />
                      Move to {selectedTargetLocation?.name || '...'}
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
