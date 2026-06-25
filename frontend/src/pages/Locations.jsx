import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Breadcrumb } from '../components/Breadcrumb';
import { WarehouseMapBuilder, EditWarehouseMapModal, WarehouseMapView } from '../components/Location';
import locationService from '../services/locationService';
import productService from '../services/productService';
import api from '../services/api';

export const Locations = () => {
  const [blocks, setBlocks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter by type
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'warehouse' | 'store_shelf'
  const [searchParams] = useSearchParams();

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [categories, setCategories] = useState([]);
  const [highlightProductId, setHighlightProductId] = useState(null);
  const [highlightProductName, setHighlightProductName] = useState('');

  // Modals
  const [mapBuilderModal, setMapBuilderModal] = useState(false);
  const [editMapModal, setEditMapModal] = useState(false);
  const [builderType, setBuilderType] = useState('warehouse');

  // Breadcrumb
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Inventory', href: '/inventory/management' },
    { label: 'Locations', href: '/inventory/locations' }
  ];

  useEffect(() => {
    fetchBlocks();
    fetchCategories();
  }, []);

  useEffect(() => {
    const highlight = searchParams.get('highlight');
    if (highlight) {
      setHighlightProductId(highlight);
    }
    const searchVal = searchParams.get('search') || '';
    setSearchQuery(searchVal);
  }, [searchParams]);

  // Fetch highlighted product details (name) to show in alerts if not found
  useEffect(() => {
    if (highlightProductId) {
      productService.getProductById(highlightProductId)
        .then(res => {
          if (res.success && res.data) {
            setHighlightProductName(res.data.name);
          }
        })
        .catch(err => {
          console.error('Error fetching product name for highlight:', err);
        });
    } else {
      setHighlightProductName('');
    }
  }, [highlightProductId]);

  const fetchCategories = async () => {
    try {
      const res = await api.get('/categories');
      if (res.data && res.data.success && res.data.data) {
        setCategories(res.data.data.categories || []);
      }
    } catch (err) {
      console.error('Error loading categories:', err);
    }
  };

  const fetchBlocks = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await locationService.getStoreMapData({ type: 'all' });
      const data = res.success ? res.data : (Array.isArray(res) ? res : []);
      setBlocks(data);
    } catch (err) {
      console.error('Error fetching blocks:', err);
      setError(err.message || 'Failed to load locations');
      setBlocks([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Filter blocks by tab
  const filteredBlocks = activeTab === 'all'
    ? blocks
    : blocks.filter(b => b.type === activeTab);

  // Check if highlighted product exists in any block locations in the database map structure
  const isProductInMap = useMemo(() => {
    if (!highlightProductId || blocks.length === 0) return true;
    return blocks.some(b =>
      (b.locations || []).some(l =>
        (l.products || []).some(p => String(p.productId) === String(highlightProductId))
      )
    );
  }, [blocks, highlightProductId]);

  // Dynamically filter blocks to only output blocks containing matching query/category or highlighted product
  const displayedBlocks = useMemo(() => {
    if (!searchQuery && !categoryFilter && !highlightProductId) {
      return filteredBlocks;
    }
    return filteredBlocks.filter(block => {
      return (block.locations || []).some(loc => {
        const matchesSearch = searchQuery
          ? (loc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (loc.products || []).some(p => p.productName.toLowerCase().includes(searchQuery.toLowerCase())))
          : true;
        const matchesCategory = categoryFilter
          ? (loc.products || []).some(p => String(p.categoryId) === String(categoryFilter))
          : true;
        const hasHighlightedProduct = highlightProductId
          ? (loc.products || []).some(p => String(p.productId) === String(highlightProductId))
          : false;

        return (matchesSearch && matchesCategory) || hasHighlightedProduct;
      });
    });
  }, [filteredBlocks, searchQuery, categoryFilter, highlightProductId]);

  const warehouseCount = blocks.filter(b => b.type === 'warehouse').length;
  const storeShelfCount = blocks.filter(b => b.type === 'store_shelf').length;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Locations</h1>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setEditMapModal(true)}
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 text-sm font-medium"
          >
            Edit Map
          </button>
          <button
            onClick={() => {
              setBuilderType('warehouse');
              setMapBuilderModal(true);
            }}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium"
          >
            + Warehouse Block
          </button>
          <button
            onClick={() => {
              setBuilderType('store_shelf');
              setMapBuilderModal(true);
            }}
            className="px-4 py-2 bg-teal-500 text-white rounded-lg hover:bg-teal-600 text-sm font-medium"
          >
            + Store Shelf Block
          </button>
        </div>
      </div>

      {/* Warning alert if highlight product has no configured location */}
      {highlightProductId && !isProductInMap && (
        <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-md shadow-sm">
          <div className="flex">
            <div className="flex-shrink-0">
              <span className="text-yellow-600 text-base">⚠️</span>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-bold text-amber-800">Sản phẩm chưa được sắp xếp</h3>
              <div className="text-xs text-amber-700 mt-1">
                Sản phẩm <strong>{highlightProductName || `ID #${highlightProductId}`}</strong> hiện chưa được sắp xếp vào bất kỳ vị trí kệ hàng hoặc ô kho nào.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Type Tabs, Search & Filter Input row */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-4 rounded-lg shadow-sm border border-gray-200">
        <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1 w-fit">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === 'all'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
              }`}
          >
            All ({blocks.length})
          </button>
          <button
            onClick={() => setActiveTab('warehouse')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === 'warehouse'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
              }`}
          >
            Warehouse ({warehouseCount})
          </button>
          <button
            onClick={() => setActiveTab('store_shelf')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${activeTab === 'store_shelf'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
              }`}
          >
            Store Shelf ({storeShelfCount})
          </button>
        </div>

        <div className="flex flex-1 max-w-lg items-center gap-2">
          <input
            type="text"
            placeholder="Search products in locations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 min-w-[200px] px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm"
          />
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 text-sm bg-white"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </select>
          {(searchQuery || categoryFilter || highlightProductId) && (
            <button
              onClick={() => {
                setSearchQuery('');
                setCategoryFilter('');
                setHighlightProductId(null);
              }}
              className="text-sm text-red-600 hover:text-red-800 font-medium px-2 py-1"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p className="font-medium">Error loading locations</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={fetchBlocks}
            className="mt-2 text-sm underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading ? (
        <div className="bg-white rounded-lg shadow-sm p-12 text-center">
          <div className="animate-spin h-12 w-12 border-4 border-emerald-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-500">Loading locations...</p>
        </div>
      ) : (
        <WarehouseMapView
          blocks={displayedBlocks}
          onRefresh={fetchBlocks}
          highlightProductId={highlightProductId}
          searchQuery={searchQuery}
          categoryFilter={categoryFilter}
        />
      )}

      {/* Map Builder Modal */}
      <WarehouseMapBuilder
        isOpen={mapBuilderModal}
        onClose={() => setMapBuilderModal(false)}
        onSuccess={fetchBlocks}
        defaultType={builderType}
      />

      {/* Edit Map Modal */}
      <EditWarehouseMapModal
        isOpen={editMapModal}
        onClose={() => setEditMapModal(false)}
        onSuccess={fetchBlocks}
        filterType={activeTab !== 'all' ? activeTab : undefined}
      />
    </div>
  );
};

export default Locations;
