import React, { useState, useEffect, useMemo, useRef } from 'react';
import { X, Map as MapIcon, Search, ShoppingCart, Package, RefreshCw } from 'lucide-react';
import posDataService from '../../services/posDataService';

// In-memory cache: shared across modal open/close cycles
let _mapDataCache = null;
let _mapDataTimestamp = 0;
const CACHE_TTL = 60_000; // 60 seconds

/**
 * POS Store Map Modal
 * Shows store_shelf blocks with locations and products.
 * Uses single optimized API endpoint + in-memory caching.
 */
export const POSStoreMapModal = ({ isOpen, onClose, onLocationSelect, initialSearchTerm = '' }) => {
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedLocation, setSelectedLocation] = useState(null);
  const searchRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      fetchMapData();
      setSearchTerm(initialSearchTerm || '');
      setSelectedLocation(null);
      // Focus search after opening
      setTimeout(() => searchRef.current?.focus(), 200);
    }
  }, [isOpen, initialSearchTerm]);

  const fetchMapData = async (forceRefresh = false) => {
    // Use cache if still fresh
    if (!forceRefresh && _mapDataCache && (Date.now() - _mapDataTimestamp < CACHE_TTL)) {
      setBlocks(_mapDataCache);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await posDataService.getStoreMapData();
      const data = res.success ? res.data : (Array.isArray(res) ? res : []);
      setBlocks(data);

      // Update cache
      _mapDataCache = data;
      _mapDataTimestamp = Date.now();
    } catch (err) {
      console.error('Error fetching store map:', err);
      setError('Failed to load store map');
    } finally {
      setLoading(false);
    }
  };

  // Build a flat product→locations index for search
  const productLocationIndex = useMemo(() => {
    const index = {}; // { productName_lower: [{ locationId, locName, blockName, productId, totalOnShelf }] }
    blocks.forEach(block => {
      (block.locations || []).forEach(loc => {
        (loc.products || []).forEach(prod => {
          const key = (prod.productName || '').toLowerCase();
          if (!index[key]) index[key] = [];
          index[key].push({
            locationId: loc.id,
            locName: loc.name,
            blockName: block.name,
            productId: prod.productId,
            productName: prod.productName,
            totalOnShelf: prod.totalOnShelf,
            unitPrice: prod.unitPrice
          });
        });
      });
    });
    return index;
  }, [blocks]);

  // Filter: which locations match the search term
  const matchingLocationIds = useMemo(() => {
    if (!searchTerm.trim()) return null;
    const term = searchTerm.toLowerCase();
    const ids = new Set();

    Object.entries(productLocationIndex).forEach(([name, locations]) => {
      if (name.includes(term)) {
        locations.forEach(l => ids.add(l.locationId));
      }
    });

    return ids;
  }, [searchTerm, productLocationIndex]);

  // Search results for the sidebar
  const searchResults = useMemo(() => {
    if (!searchTerm.trim()) return [];
    const term = searchTerm.toLowerCase();
    const results = [];

    Object.entries(productLocationIndex).forEach(([name, locations]) => {
      if (name.includes(term)) {
        results.push(...locations);
      }
    });

    return results;
  }, [searchTerm, productLocationIndex]);

  const handleProductAddToCart = (productInfo) => {
    if (onLocationSelect) {
      onLocationSelect(productInfo);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-7xl h-[95vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
          <div className="flex items-center gap-4 flex-1">
            <div className="flex items-center gap-2.5 mr-4">
              <div className="w-9 h-9 bg-emerald-100 rounded-lg flex items-center justify-center">
                <MapIcon className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-gray-900">Store Shelf Map</h2>
                <p className="text-xs text-gray-500">Click a product to add to cart</p>
              </div>
            </div>

            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
              <input
                ref={searchRef}
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search product by name..."
                className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
              />
              {searchTerm && matchingLocationIds && (
                <span className="absolute right-3 top-2.5 text-xs text-emerald-600 font-medium">
                  {matchingLocationIds.size} location{matchingLocationIds.size !== 1 ? 's' : ''}
                </span>
              )}
            </div>

            {/* Legend + Refresh */}
            <div className="flex items-center gap-3 ml-4 pl-4 border-l border-gray-200">
              <div className="flex items-center gap-1.5">
                <div className="w-3.5 h-3.5 bg-white border border-gray-300 rounded-sm"></div>
                <span className="text-[10px] text-gray-500">Empty</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-3.5 h-3.5 bg-emerald-500 rounded-sm"></div>
                <span className="text-[10px] text-gray-500">Stocked</span>
              </div>
              {searchTerm && (
                <div className="flex items-center gap-1.5">
                  <div className="w-3.5 h-3.5 bg-amber-400 rounded-sm ring-1 ring-amber-500"></div>
                  <span className="text-[10px] text-amber-700 font-medium">Match</span>
                </div>
              )}
              <button
                onClick={() => fetchMapData(true)}
                className="p-1.5 text-gray-400 hover:text-emerald-600 hover:bg-emerald-50 rounded transition-colors"
                title="Refresh map data"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 ml-4 p-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Map Grid */}
          <div className="flex-1 p-5 bg-gray-50 overflow-auto">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="animate-spin h-8 w-8 border-4 border-emerald-500 border-t-transparent rounded-full mx-auto mb-3"></div>
                  <p className="text-sm text-gray-500">Loading store map...</p>
                </div>
              </div>
            ) : error ? (
              <div className="text-center py-12">
                <p className="text-red-600 mb-3">{error}</p>
                <button
                  onClick={() => fetchMapData(true)}
                  className="px-4 py-2 text-sm bg-white border border-red-200 rounded-lg hover:bg-red-50"
                >
                  Retry
                </button>
              </div>
            ) : blocks.length === 0 ? (
              <div className="text-center py-12">
                <MapIcon className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">No store shelves</h3>
                <p className="text-sm text-gray-500">Create store shelf blocks in Inventory → Locations</p>
              </div>
            ) : (
              <div className="flex flex-wrap justify-center gap-6">
                {blocks.map(block => {
                  const { rows, cols, columnGaps = [], locations = [] } = block;
                  const gridArray = Array(rows * cols).fill(null);
                  locations.forEach(loc => {
                    const pos = loc.position - 1;
                    if (pos >= 0 && pos < gridArray.length) gridArray[pos] = loc;
                  });

                  return (
                    <div key={block.id} className="bg-white rounded-lg shadow-md border border-gray-200">
                      <div className="px-5 py-3 border-b border-gray-100">
                        <h3 className="text-base font-bold text-gray-900">{block.name}</h3>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {locations.filter(l => (l.products?.length || 0) > 0).length} occupied
                          {' • '}
                          {locations.filter(l => (l.products?.length || 0) === 0).length} empty
                        </p>
                      </div>

                      <div className="p-3 bg-gray-100 rounded-b-lg">
                        <div className="flex gap-0">
                          {Array.from({ length: cols }).map((_, colIdx) => {
                            const hasGapAfter = columnGaps.includes(colIdx + 1);
                            return (
                              <React.Fragment key={colIdx}>
                                <div
                                  className="grid gap-1"
                                  style={{ gridTemplateRows: `repeat(${rows}, 48px)` }}
                                >
                                  {Array.from({ length: rows }).map((_, rowIdx) => {
                                    const idx = colIdx * rows + rowIdx;
                                    const location = gridArray[idx];

                                    if (!location) {
                                      return (
                                        <div
                                          key={`empty-${rowIdx}-${colIdx}`}
                                          className="bg-gray-200 rounded border border-gray-300 opacity-30 w-[48px]"
                                        />
                                      );
                                    }

                                    const hasProducts = (location.products?.length || 0) > 0;
                                    const isSearchMatch = matchingLocationIds?.has(location.id);
                                    const isSelected = selectedLocation?.id === location.id;

                                    return (
                                      <div
                                        key={location.id}
                                        onClick={() => hasProducts && setSelectedLocation(
                                          selectedLocation?.id === location.id ? null : location
                                        )}
                                        className={`relative rounded border-2 transition-all w-[48px] group ${isSelected
                                          ? 'bg-blue-500 border-blue-600 ring-2 ring-blue-300 cursor-pointer'
                                          : isSearchMatch
                                            ? 'bg-amber-400 border-amber-500 ring-2 ring-amber-300 hover:bg-amber-500 cursor-pointer animate-pulse'
                                            : hasProducts
                                              ? 'bg-emerald-500 border-emerald-600 hover:bg-emerald-600 cursor-pointer'
                                              : 'bg-white border-gray-300 cursor-default'
                                          }`}
                                      >
                                        <div className="absolute inset-0 flex items-center justify-center">
                                          <span className={`text-[10px] font-bold ${isSelected || isSearchMatch || hasProducts ? 'text-white' : 'text-gray-400'
                                            }`}>
                                            {location.name.split('-')[1] || location.name}
                                          </span>
                                        </div>

                                        {/* Tooltip */}
                                        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-[9999] pointer-events-none">
                                          <div className="bg-gray-900 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap shadow-xl max-w-[280px]">
                                            <div className="font-bold mb-1">{location.name}</div>
                                            {hasProducts ? (
                                              location.products.slice(0, 4).map((p, i) => (
                                                <div key={i} className="text-[10px] text-emerald-300 truncate">
                                                  • {p.productName} ({p.totalOnShelf})
                                                </div>
                                              ))
                                            ) : (
                                              <div className="text-[10px] text-gray-400">Empty</div>
                                            )}
                                            {location.products?.length > 4 && (
                                              <div className="text-[10px] text-gray-400">
                                                +{location.products.length - 4} more...
                                              </div>
                                            )}
                                          </div>
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
                  );
                })}
              </div>
            )}
          </div>

          {/* Right Sidebar: Location Detail / Search Results */}
          <div className="w-80 border-l border-gray-200 bg-white flex flex-col overflow-hidden">
            {searchTerm.trim() && searchResults.length > 0 ? (
              /* Search Results */
              <div className="flex-1 overflow-auto">
                <div className="p-3 border-b border-gray-100 bg-gray-50">
                  <h4 className="text-sm font-semibold text-gray-700">
                    Search Results ({searchResults.length})
                  </h4>
                </div>
                <div className="divide-y divide-gray-100">
                  {searchResults.map((item, idx) => (
                    <div key={idx} className="p-3 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {item.productName}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {item.blockName} → {item.locName}
                          </p>
                          <p className="text-xs text-emerald-600 font-medium mt-0.5">
                            {item.totalOnShelf} on shelf
                          </p>
                        </div>
                        <button
                          onClick={() => handleProductAddToCart(item)}
                          className="flex-shrink-0 p-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition-colors"
                          title="Add to cart"
                        >
                          <ShoppingCart className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : selectedLocation ? (
              /* Location Detail */
              <div className="flex-1 overflow-auto">
                <div className="p-3 border-b border-gray-100 bg-gray-50">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-gray-700">
                      {selectedLocation.name}
                    </h4>
                    <button
                      onClick={() => setSelectedLocation(null)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {selectedLocation.products?.length || 0} products at this location
                  </p>
                </div>
                <div className="divide-y divide-gray-100">
                  {(selectedLocation.products || []).map((product, idx) => (
                    <div key={idx} className="p-3 hover:bg-gray-50 transition-colors">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {product.productName}
                          </p>
                          <div className="flex items-center gap-3 mt-1">
                            <span className="text-xs text-emerald-600 font-medium">
                              <Package className="w-3 h-3 inline mr-0.5" />
                              {product.totalOnShelf} on shelf
                            </span>
                            {product.unitPrice > 0 && (
                              <span className="text-xs text-gray-500">
                                {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(product.unitPrice)}
                              </span>
                            )}
                          </div>
                          {product.earliestExpiry && (
                            <p className="text-[10px] text-orange-500 mt-0.5">
                              Earliest expiry: {new Date(product.earliestExpiry).toLocaleDateString('vi-VN')}
                            </p>
                          )}
                        </div>
                        <button
                          onClick={() => handleProductAddToCart(product)}
                          className="flex-shrink-0 p-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition-colors"
                          title="Add to cart"
                        >
                          <ShoppingCart className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              /* Empty state */
              <div className="flex-1 flex items-center justify-center p-6 text-center">
                <div>
                  <MapIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-sm text-gray-500">
                    Click a location on the map to view products
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Or search by product name to find its location
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
