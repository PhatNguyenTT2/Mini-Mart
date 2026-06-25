import React, { useMemo, useState } from 'react';
import { MapPin, Trash2 } from 'lucide-react';
import { LocationDetailModal } from './LocationDetailModal';
import locationService from '../../services/locationService';

/**
 * WarehouseMapView
 * Now works with block-based data from /api/warehouse/blocks.
 * Props:
 * - blocks: array of block objects from API (each with locations sub-array)
 * - onRefresh: callback to refresh data from parent
 */
export const WarehouseMapView = ({
  blocks = [],
  onRefresh,
  highlightProductId = null,
  searchQuery = '',
  categoryFilter = ''
}) => {
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [deletingBlockId, setDeletingBlockId] = useState(null);

  const handleDeleteBlock = async (block) => {
    // Check if any location in this block has inventory
    const hasInventory = block.locations?.some(l => (parseInt(l.inventory_item_count) || 0) > 0);
    if (hasInventory) {
      alert(`Cannot delete Block ${block.name}: some locations still have inventory items. Move or clear all items first.`);
      return;
    }

    const confirmed = window.confirm(
      `Delete Block ${block.name} and all its ${block.locations?.length || 0} locations?\nThis action cannot be undone.`
    );
    if (!confirmed) return;

    try {
      setDeletingBlockId(block.id);
      await locationService.deleteBlock(block.id);
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error('Error deleting block:', err);
      const msg = err.response?.data?.error || err.message || 'Failed to delete block';
      alert(`Error: ${msg}`);
    } finally {
      setDeletingBlockId(null);
    }
  };

  const handleLocationUpdate = async () => {
    if (selectedLocation) {
      try {
        const res = await locationService.getLocationById(selectedLocation.id);
        if (res.success && res.data) {
          setSelectedLocation(res.data);
        }
      } catch (error) {
        console.error('Error refreshing location:', error);
      }
    }
    if (onRefresh) onRefresh();
  };

  const renderBlock = (block) => {
    const { rows, cols, columnGaps = [], locations = [] } = block;

    const getLocationCapacity = (location) => {
      const occupiedCapacity = location.occupiedCapacity || 0;
      const maxCapacity = location.maxCapacity || 100;
      const capacityPercent = maxCapacity > 0 ? (occupiedCapacity / maxCapacity) * 100 : 0;
      return { occupiedCapacity, maxCapacity, capacityPercent };
    };

    // Position locations into grid
    const gridArray = Array(rows * cols).fill(null);
    locations.forEach(loc => {
      const pos = loc.position - 1; // 0-indexed
      if (pos >= 0 && pos < gridArray.length) {
        gridArray[pos] = loc;
      }
    });

    const emptyCount = locations.filter(l => {
      const { capacityPercent } = getLocationCapacity(l);
      return capacityPercent === 0;
    }).length;

    const nearlyFullCount = locations.filter(l => {
      const { capacityPercent } = getLocationCapacity(l);
      return capacityPercent > 80 && capacityPercent < 100;
    }).length;

    const fullCount = locations.filter(l => {
      const { capacityPercent } = getLocationCapacity(l);
      return capacityPercent > 90;
    }).length;

    return (
      <div key={block.id} className="bg-white rounded-lg shadow-md p-6 border-2 border-gray-300">
        {/* Block Header */}
        <div className="mb-4 pb-3 border-b-2 border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h3 className="text-xl font-bold text-gray-900">Block {block.name}</h3>
              <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${block.type === 'store_shelf'
                ? 'bg-blue-100 text-blue-700'
                : 'bg-emerald-100 text-emerald-700'
                }`}>
                {block.type === 'store_shelf' ? 'Store Shelf' : 'Warehouse'}
              </span>
            </div>
            <button
              onClick={() => handleDeleteBlock(block)}
              disabled={deletingBlockId === block.id}
              title={`Delete Block ${block.name}`}
              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
            >
              {deletingBlockId === block.id ? (
                <div className="w-4 h-4 border-2 border-red-400 border-t-transparent rounded-full animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="text-sm text-gray-600 mt-1">
            <span className="text-gray-600 font-medium">{emptyCount} empty</span>
            {' • '}
            <span className="text-yellow-600 font-medium">{nearlyFullCount} nearly full</span>
            {' • '}
            <span className="text-red-600 font-medium">{fullCount} full</span>
          </p>
        </div>

        {/* Grid Container */}
        <div className="flex justify-center overflow-visible">
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

                        const { occupiedCapacity, maxCapacity, capacityPercent } = getLocationCapacity(location);
                        const active = location.isActive;

                        let bgColor = 'bg-white border-gray-300';
                        let textColor = 'text-gray-900';

                        if (!active) {
                          bgColor = 'bg-gray-300 border-gray-400';
                          textColor = 'text-gray-600';
                        } else if (capacityPercent > 90) {
                          bgColor = 'bg-red-500 border-red-600 hover:bg-red-600';
                          textColor = 'text-white';
                        } else if (capacityPercent > 80) {
                          bgColor = 'bg-yellow-400 border-yellow-500 hover:bg-yellow-500';
                          textColor = 'text-gray-900';
                        } else if (capacityPercent > 0) {
                          bgColor = 'bg-emerald-500 border-emerald-600 hover:bg-emerald-600';
                          textColor = 'text-white';
                        }

                        // Filtering & Highlighting
                        const hasHighlightedProduct = highlightProductId
                          ? (location.products || []).some(p => String(p.productId) === String(highlightProductId))
                          : false;

                        const isSearchActive = !!searchQuery || !!categoryFilter;

                        const matchesSearch = searchQuery
                          ? (location.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            (location.products || []).some(p => p.productName.toLowerCase().includes(searchQuery.toLowerCase())))
                          : true;

                        const matchesCategory = categoryFilter
                          ? (location.products || []).some(p => String(p.categoryId) === String(categoryFilter))
                          : true;

                        const isMatched = matchesSearch && matchesCategory;

                        const opacityClass = isSearchActive && !isMatched && !hasHighlightedProduct
                          ? 'opacity-20 scale-95 border-dashed border-gray-400'
                          : '';

                        const highlightClass = hasHighlightedProduct
                          ? 'ring-4 ring-amber-400 animate-pulse relative z-10 scale-105 border-amber-500 border-opacity-100 shadow-xl'
                          : '';

                        return (
                          <div
                            key={location.id}
                            onClick={() => setSelectedLocation(location)}
                            className={`relative rounded border-2 transition-all cursor-pointer group w-[50px] ${bgColor} ${opacityClass} ${highlightClass} hover:shadow-lg`}
                          >
                            <div className="absolute inset-0 flex flex-col items-center justify-center p-1">
                              <span className={`text-[10px] font-bold ${textColor}`}>
                                {location.name.split('-')[1]}
                              </span>
                            </div>

                            {!active && (
                              <span className="absolute top-0.5 right-0.5 bg-red-500 text-white text-[6px] px-1 py-0.5 rounded font-bold">
                                OFF
                              </span>
                            )}

                            {/* Hover Tooltip */}
                            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-[9999] pointer-events-none">
                              <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-xl min-w-[150px]">
                                <div className="font-bold">{location.name}</div>
                                <div className="text-[10px] text-gray-400 mt-1">
                                  Capacity: {occupiedCapacity} / {maxCapacity} ({capacityPercent.toFixed(1)}%)
                                </div>
                                {location.products && location.products.length > 0 && (
                                  <div className="mt-1 pt-1 border-t border-gray-700 max-h-32 overflow-y-auto">
                                    <div className="text-[9px] uppercase font-bold text-gray-400 mb-1">Products inside:</div>
                                    {location.products.map((p, pIdx) => (
                                      <div key={pIdx} className="text-[10px] text-emerald-300 truncate">
                                        • {p.productName} ({p.totalOnShelf})
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                              <div className="w-0 h-0 border-l-4 border-r-4 border-b-4 border-transparent border-b-gray-900 mx-auto"></div>
                            </div>
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
      </div>
    );
  };

  if (blocks.length === 0) {
    const isFiltered = !!searchQuery || !!categoryFilter || !!highlightProductId;
    return (
      <div className="bg-white rounded-lg shadow-sm p-12 text-center">
        <MapPin className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          {isFiltered ? 'Không tìm thấy vị trí khớp' : 'No warehouse map'}
        </h3>
        <p className="text-sm text-gray-500">
          {isFiltered
            ? 'Không tìm thấy kệ hàng hoặc ô kho nào chứa sản phẩm khớp với bộ lọc.'
            : 'Create locations using the Map Builder to see the layout'}
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Legend */}
      <div className="bg-white rounded-lg shadow-sm p-4 mb-6 border border-gray-200">
        <div className="flex items-center gap-8">
          <h4 className="text-sm font-bold text-gray-700">Legend:</h4>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-white border-2 border-gray-300 rounded"></div>
            <span className="text-sm text-gray-700 font-medium">Empty</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-emerald-500 border-2 border-emerald-600 rounded"></div>
            <span className="text-sm text-gray-700 font-medium">In Use (&lt;80%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-yellow-400 border-2 border-yellow-500 rounded"></div>
            <span className="text-sm text-gray-700 font-medium">Nearly Full (&gt;80%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-red-500 border-2 border-red-600 rounded"></div>
            <span className="text-sm text-gray-700 font-medium">Full (&gt;90%)</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gray-300 border-2 border-gray-400 rounded"></div>
            <span className="text-sm text-gray-700 font-medium">Inactive</span>
          </div>
        </div>
      </div>

      {/* Blocks Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {blocks.map(block => renderBlock(block))}
      </div>

      {/* Location Detail Modal */}
      <LocationDetailModal
        isOpen={!!selectedLocation}
        location={selectedLocation}
        onClose={() => setSelectedLocation(null)}
        onSuccess={handleLocationUpdate}
      />
    </div>
  );
};
