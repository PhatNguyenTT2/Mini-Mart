import React, { useState, useEffect } from 'react';
import { Save, Loader, Trash2 } from 'lucide-react';
import locationService from '../../services/locationService';
import { EditLocationModal } from './EditLocationModal';

export const EditWarehouseMapModal = ({ isOpen, onClose, onSuccess, filterType }) => {
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [editLocationModalOpen, setEditLocationModalOpen] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState(null);

  // Track changes
  const [modifiedBlocks, setModifiedBlocks] = useState({}); // blockId -> { columnGaps }
  const [modifiedLocations, setModifiedLocations] = useState({}); // locationId -> { isActive }

  useEffect(() => {
    if (isOpen) {
      fetchBlocks();
      setModifiedBlocks({});
      setModifiedLocations({});
    }
  }, [isOpen]);

  const fetchBlocks = async () => {
    try {
      setLoading(true);
      const filters = {};
      if (filterType) filters.type = filterType;

      const res = await locationService.getAllBlocks(filters);
      const blocksData = res.success ? res.data : (Array.isArray(res) ? res : []);
      setBlocks(blocksData);
    } catch (err) {
      setError('Failed to load blocks');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLocationClick = (location) => {
    setSelectedLocation(location);
    setEditLocationModalOpen(true);
  };

  const handleEditLocationSuccess = () => {
    setEditLocationModalOpen(false);
    setSelectedLocation(null);
    fetchBlocks();
  };

  const handleDeleteBlock = async (block) => {
    const hasInventory = block.locations?.some(l => (parseInt(l.inventoryItemCount) || 0) > 0);
    if (hasInventory) {
      alert(`Cannot delete Block ${block.name}: some locations still have inventory items. Move or clear all items first.`);
      return;
    }

    const confirmed = window.confirm(
      `Delete Block ${block.name} and all its ${block.locations?.length || 0} locations?\nThis action cannot be undone.`
    );
    if (!confirmed) return;

    try {
      await locationService.deleteBlock(block.id);
      fetchBlocks();
      if (onSuccess) onSuccess();
    } catch (err) {
      console.error('Error deleting block:', err);
      const msg = err.response?.data?.error || err.message || 'Failed to delete block';
      alert(`Error: ${msg}`);
    }
  };

  const toggleLocationActive = (blockId, locationId) => {
    setBlocks(prevBlocks =>
      prevBlocks.map(block => {
        if (block.id !== blockId) return block;
        return {
          ...block,
          locations: block.locations.map(loc =>
            loc.id === locationId ? { ...loc, isActive: !loc.isActive } : loc
          )
        };
      })
    );

    setModifiedLocations(prev => {
      const current = prev[locationId];
      const block = blocks.find(b => b.id === blockId);
      const loc = block?.locations.find(l => l.id === locationId);
      const newActive = !(loc?.isActive);

      return { ...prev, [locationId]: { isActive: newActive } };
    });
  };

  const toggleColumnGap = (blockId, colNum) => {
    setBlocks(prevBlocks =>
      prevBlocks.map(block => {
        if (block.id !== blockId) return block;
        const currentGaps = block.columnGaps || [];
        const hasGap = currentGaps.includes(colNum);
        const newGaps = hasGap
          ? currentGaps.filter(g => g !== colNum)
          : [...currentGaps, colNum].sort((a, b) => a - b);

        // Track modification
        setModifiedBlocks(prev => ({
          ...prev,
          [blockId]: { columnGaps: newGaps }
        }));

        return { ...block, columnGaps: newGaps };
      })
    );
  };

  const saveChanges = async () => {
    setSaving(true);
    setError('');

    try {
      const promises = [];

      // Save block column gap changes
      for (const [blockId, data] of Object.entries(modifiedBlocks)) {
        promises.push(
          locationService.updateBlock(parseInt(blockId), { columnGaps: data.columnGaps })
            .catch(err => {
              console.warn(`Failed to update block ${blockId}:`, err.message);
              return null;
            })
        );
      }

      // Save location active status changes
      for (const [locationId, data] of Object.entries(modifiedLocations)) {
        promises.push(
          locationService.updateLocation(parseInt(locationId), { isActive: data.isActive })
            .catch(err => {
              console.warn(`Failed to update location ${locationId}:`, err.message);
              return null;
            })
        );
      }

      await Promise.all(promises);

      const totalChanges = Object.keys(modifiedBlocks).length + Object.keys(modifiedLocations).length;
      if (onSuccess) onSuccess();
      if (onClose) onClose();
      alert(`Successfully updated ${totalChanges} item(s)`);
    } catch (err) {
      console.error('Error saving changes:', err);
      setError('Failed to save changes. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  const hasChanges = Object.keys(modifiedBlocks).length > 0 || Object.keys(modifiedLocations).length > 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-6xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white z-10">
          <div>
            <h2 className="text-[20px] font-semibold text-gray-900">
              Edit Warehouse Map
            </h2>
            <p className="text-[12px] text-gray-500 mt-1">
              Toggle locations active/inactive and adjust column gaps. Changes are saved to database.
            </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          ) : (
            <>
              {/* Legend */}
              <div className="bg-gray-50 rounded-lg p-4 mb-6 border border-gray-200">
                <div className="flex items-center gap-6 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-emerald-500 border-2 border-emerald-600 rounded"></div>
                    <span className="text-gray-700 font-medium">Active</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-gray-300 border-2 border-gray-400 rounded"></div>
                    <span className="text-gray-700 font-medium">Inactive</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-yellow-400 border-2 border-yellow-500 rounded"></div>
                    <span className="text-gray-700 font-medium">In Use (Cannot Deactivate)</span>
                  </div>
                </div>
              </div>

              {/* Blocks */}
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                {blocks.map(block => {
                  const { rows, cols, columnGaps = [], locations = [] } = block;

                  const gridArray = Array(rows * cols).fill(null);
                  locations.forEach(loc => {
                    const pos = loc.position - 1;
                    if (pos >= 0 && pos < gridArray.length) gridArray[pos] = loc;
                  });

                  const activeCount = locations.filter(l => l.isActive).length;
                  const inUseCount = locations.filter(l => (l.inventoryItemCount || 0) > 0).length;

                  return (
                    <div key={block.id} className="bg-white rounded-lg shadow-md p-6 border-2 border-gray-300">
                      <div className="mb-4 pb-3 border-b-2 border-gray-200">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <h3 className="text-xl font-bold text-gray-900">Block {block.name}</h3>
                            <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${
                              block.type === 'store_shelf' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'
                            }`}>
                              {block.type === 'store_shelf' ? 'Store Shelf' : 'Warehouse'}
                            </span>
                          </div>
                          <button
                            onClick={() => handleDeleteBlock(block)}
                            title={inUseCount > 0 ? 'Cannot delete: has inventory' : `Delete Block ${block.name}`}
                            className={`p-1.5 rounded-lg transition-colors ${
                              inUseCount > 0
                                ? 'text-gray-300 cursor-not-allowed'
                                : 'text-gray-400 hover:text-red-600 hover:bg-red-50'
                            }`}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                        <p className="text-sm text-gray-600 mt-1">
                          {activeCount} active • {inUseCount} in use
                        </p>
                      </div>

                      {/* Column Gaps Configuration */}
                      <div className="mb-4">
                        <label className="block text-xs font-medium text-gray-700 mb-2">
                          Column Spacing (saved to database)
                        </label>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs text-gray-500">Add gap after column:</span>
                          {Array.from({ length: cols - 1 }).map((_, idx) => {
                            const colNum = idx + 1;
                            const hasGap = columnGaps.includes(colNum);
                            return (
                              <button
                                key={colNum}
                                onClick={() => toggleColumnGap(block.id, colNum)}
                                className={`px-2 py-1 text-xs rounded border-2 transition-all ${hasGap
                                  ? 'bg-blue-500 border-blue-600 text-white'
                                  : 'bg-white border-gray-300 text-gray-700 hover:border-blue-400'
                                  }`}
                              >
                                {colNum}
                              </button>
                            );
                          })}
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
                                  style={{ gridTemplateRows: `repeat(${rows}, 50px)` }}
                                >
                                  {Array.from({ length: rows }).map((_, rowIdx) => {
                                    const idx = colIdx * rows + rowIdx;
                                    const location = gridArray[idx];

                                    if (!location) {
                                      return (
                                        <div
                                          key={`empty-${rowIdx}-${colIdx}`}
                                          className="bg-gray-200 rounded border border-gray-300 opacity-30 w-[50px]"
                                        />
                                      );
                                    }

                                    const hasInventory = (location.inventoryItemCount || 0) > 0;

                                    let bgColor = 'bg-white border-gray-300';
                                    if (!location.isActive) {
                                      bgColor = 'bg-gray-300 border-gray-400';
                                    } else if (hasInventory) {
                                      bgColor = 'bg-yellow-400 border-yellow-500';
                                    } else {
                                      bgColor = 'bg-emerald-500 border-emerald-600';
                                    }

                                    return (
                                      <button
                                        key={location.id}
                                        onClick={() => handleLocationClick(location)}
                                        className={`relative rounded border-2 transition-all w-[50px] ${bgColor} cursor-pointer hover:opacity-80`}
                                        title={`${location.name} - Click to edit`}
                                      >
                                        <div className="absolute inset-0 flex items-center justify-center">
                                          <span className={`text-[10px] font-bold ${location.isActive ? (hasInventory ? 'text-gray-900' : 'text-white') : 'text-gray-600'}`}>
                                            {location.name.split('-')[1]}
                                          </span>
                                        </div>
                                      </button>
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
            </>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 mt-6 pt-6 border-t border-gray-200">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-sm font-medium disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={saveChanges}
              disabled={saving || loading || !hasChanges}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {saving ? (
                <>
                  <Loader className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save Changes
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Edit Location Modal */}
      <EditLocationModal
        isOpen={editLocationModalOpen}
        onClose={() => {
          setEditLocationModalOpen(false);
          setSelectedLocation(null);
        }}
        onSuccess={handleEditLocationSuccess}
        location={selectedLocation}
      />
    </div>
  );
};
