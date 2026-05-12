import React, { useState, useEffect } from 'react';
import { Breadcrumb } from '../components/Breadcrumb';
import { WarehouseMapBuilder, EditWarehouseMapModal, WarehouseMapView } from '../components/Location';
import locationService from '../services/locationService';

export const Locations = () => {
  const [blocks, setBlocks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter by type
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'warehouse' | 'store_shelf'

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
  }, []);

  const fetchBlocks = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await locationService.getAllBlocks();
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

      {/* Type Tabs */}
      <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setActiveTab('all')}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === 'all'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          All ({blocks.length})
        </button>
        <button
          onClick={() => setActiveTab('warehouse')}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === 'warehouse'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Warehouse ({warehouseCount})
        </button>
        <button
          onClick={() => setActiveTab('store_shelf')}
          className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === 'store_shelf'
              ? 'bg-white text-gray-900 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          Store Shelf ({storeShelfCount})
        </button>
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
          blocks={filteredBlocks}
          onRefresh={fetchBlocks}
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
