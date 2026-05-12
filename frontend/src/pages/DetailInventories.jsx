import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Breadcrumb } from '../components/Breadcrumb';
import { DetailInventoryList, DetailInventoryListHeader, UpdateLocationModal } from '../components/DetailInventoryList';
import {
  AdjustStockBatchModal,
  MovementHistoryBatchModal
} from '../components/DetailInventoryList/BatchMovementModals';
// StockOutBatchModal removed - now using CreateStockOutOrderModal at Inventory level
import detailInventoryService from '../services/detailInventoryService';
import productService from '../services/productService';

export const DetailInventories = () => {
  const { productId } = useParams();
  const navigate = useNavigate();

  const [product, setProduct] = useState(null);
  const [detailInventory, setDetailInventory] = useState([]);
  const [filteredDetailInventory, setFilteredDetailInventory] = useState([]);
  const [paginatedDetailInventory, setPaginatedDetailInventory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters and sorting
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('batchCode');
  const [sortOrder, setSortOrder] = useState('asc');
  const [filterView, setFilterView] = useState('in-stock'); // in-stock, out-of-stock, has-warehouse, has-shelf, expiring-soon, expired

  // Pagination state
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    itemsPerPage: 10,
  });

  // Modals state
  const [stockInModal, setStockInModal] = useState({ isOpen: false, item: null });
  // stockOutModal removed - use CreateStockOutOrderModal at Inventory level instead
  const [adjustModal, setAdjustModal] = useState({ isOpen: false, item: null });
  const [transferModal, setTransferModal] = useState({ isOpen: false, item: null });
  const [historyModal, setHistoryModal] = useState({ isOpen: false, item: null });
  const [updateLocationModal, setUpdateLocationModal] = useState({ isOpen: false, item: null });

  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Inventories', href: '/inventory/management' },
    { label: product?.name || 'Detail Inventories', href: `/inventory/detail/${productId}` },
  ];

  // Fetch product and detail inventory on component mount
  useEffect(() => {
    if (productId) {
      fetchProduct();
      fetchDetailInventory();
    }
  }, [productId]);

  // Apply filters and sorting when data or filters change
  useEffect(() => {
    let result = [...detailInventory];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      result = result.filter(item =>
        item.batchId?.batchCode?.toLowerCase().includes(query) ||
        item.batchId?.notes?.toLowerCase().includes(query) ||
        item.location?.toLowerCase().includes(query)
      );
    }

    // Apply view filter
    if (filterView === 'in-stock') {
      result = result.filter(item => item.quantityAvailable > 0);
    } else if (filterView === 'out-of-stock') {
      result = result.filter(item => item.quantityAvailable === 0);
    } else if (filterView === 'has-warehouse') {
      result = result.filter(item => item.quantityOnHand > 0);
    } else if (filterView === 'has-shelf') {
      result = result.filter(item => item.quantityOnShelf > 0);
    } else if (filterView === 'expiring-soon') {
      const thirtyDaysFromNow = new Date();
      thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30);
      result = result.filter(item =>
        item.batchId?.expiryDate &&
        new Date(item.batchId.expiryDate) <= thirtyDaysFromNow &&
        new Date(item.batchId.expiryDate) > new Date()
      );
    } else if (filterView === 'expired') {
      result = result.filter(item =>
        item.batchId?.expiryDate &&
        new Date(item.batchId.expiryDate) < new Date()
      );
    }

    // Apply sorting
    result.sort((a, b) => {
      let aVal, bVal;

      // Handle nested fields
      if (sortField === 'batchCode') {
        aVal = a.batchId?.batchCode || '';
        bVal = b.batchId?.batchCode || '';
      } else if (sortField === 'expiryDate') {
        aVal = a.batchId?.expiryDate ? new Date(a.batchId.expiryDate).getTime() : 0;
        bVal = b.batchId?.expiryDate ? new Date(b.batchId.expiryDate).getTime() : 0;
      } else {
        aVal = a[sortField];
        bVal = b[sortField];
      }

      // Handle null/undefined values
      if (aVal == null) aVal = '';
      if (bVal == null) bVal = '';

      // Handle different data types
      if (['quantityOnHand', 'quantityOnShelf', 'quantityReserved', 'quantityAvailable'].includes(sortField)) {
        aVal = Number(aVal) || 0;
        bVal = Number(bVal) || 0;
      } else if (sortField === 'batchCode') {
        aVal = String(aVal).toLowerCase();
        bVal = String(bVal).toLowerCase();
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    setFilteredDetailInventory(result);

    // Update pagination
    const totalPages = Math.ceil(result.length / itemsPerPage);
    setPagination(prev => ({
      ...prev,
      currentPage: 1,
      totalPages,
      itemsPerPage,
    }));
  }, [detailInventory, searchQuery, sortField, sortOrder, itemsPerPage, filterView]);

  // Paginate filtered detail inventory
  useEffect(() => {
    const startIndex = (pagination.currentPage - 1) * pagination.itemsPerPage;
    const endIndex = startIndex + pagination.itemsPerPage;
    setPaginatedDetailInventory(filteredDetailInventory.slice(startIndex, endIndex));
  }, [filteredDetailInventory, pagination.currentPage, pagination.itemsPerPage]);

  const fetchProduct = async () => {
    try {
      const response = await productService.getProductById(productId);
      if (response.success && response.data && response.data.product) {
        setProduct(response.data.product);
      }
    } catch (err) {
      console.error('Error fetching product:', err);
    }
  };

  const fetchDetailInventory = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await detailInventoryService.getDetailInventoriesByProduct(productId);

      if (response.success && response.data && response.data.detailInventories) {
        setDetailInventory(response.data.detailInventories);
      } else if (Array.isArray(response.data)) {
        setDetailInventory(response.data);
      } else {
        console.error('Unexpected response structure:', response);
        setDetailInventory([]);
      }
    } catch (err) {
      console.error('Error fetching detail inventory:', err);
      setError(err.message || 'Failed to load detail inventory');
      setDetailInventory([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleColumnSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const handleSearchChange = (query) => {
    setSearchQuery(query);
  };

  const handleItemsPerPageChange = (value) => {
    setItemsPerPage(value);
  };

  const handleFilterViewChange = (view) => {
    setFilterView(view);
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({
      ...prev,
      currentPage: newPage
    }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleStockIn = (item) => {
    setStockInModal({ isOpen: true, item });
  };

  // handleStockOut removed - redirect to Inventory page to create StockOutOrder
  const handleStockOut = (item) => {
    alert('Please use "Create Stock Out" button on the Inventory Management page to create a stock out order with multiple batches.');
    navigate('/inventory/management');
  };

  const handleAdjust = (item) => {
    setAdjustModal({ isOpen: true, item });
  };

  const handleTransfer = (item) => {
    setTransferModal({ isOpen: true, item });
  };

  const handleViewHistory = (item) => {
    setHistoryModal({ isOpen: true, item });
  };

  const handleUpdateLocation = (item) => {
    setUpdateLocationModal({ isOpen: true, item });
  };

  const handleMovementSuccess = () => {
    fetchDetailInventory();
  };

  const handleUpdateLocationSuccess = () => {
    fetchDetailInventory();
    setUpdateLocationModal({ isOpen: false, item: null });
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Product Info Card */}
      {product && (
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="flex items-center gap-4">
            {product.image && (
              <img
                src={product.image}
                alt={product.name}
                className="w-16 h-16 object-cover rounded-lg"
              />
            )}
            <div>
              <h3 className="text-[16px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
                {product.name}
              </h3>
              <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-gray-600">
                Product ID: #{productId}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Detail Inventory List Header */}
      <DetailInventoryListHeader
        itemsPerPage={itemsPerPage}
        onItemsPerPageChange={handleItemsPerPageChange}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        filterView={filterView}
        onFilterViewChange={handleFilterViewChange}
      />

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p className="font-medium">Error loading detail inventory</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={fetchDetailInventory}
            className="mt-2 text-sm underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Detail Inventory List Table */}
      {!isLoading && !error && (
        <>
          <DetailInventoryList
            detailInventory={paginatedDetailInventory}
            onSort={handleColumnSort}
            sortField={sortField}
            sortOrder={sortOrder}
            onViewHistory={handleViewHistory}
            onStockOut={handleStockOut}
            onAdjust={handleAdjust}
            onUpdateLocation={handleUpdateLocation}
          />

          {/* Pagination */}
          {pagination.totalPages > 1 && (
            <div className="flex items-center justify-center mt-6">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handlePageChange(pagination.currentPage - 1)}
                  disabled={pagination.currentPage === 1}
                  className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${pagination.currentPage === 1
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-[#3bb77e] hover:bg-[#def9ec]'
                    }`}
                >
                  ‹ Previous
                </button>

                {(() => {
                  const maxPagesToShow = 5;
                  const { totalPages, currentPage } = pagination;
                  let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
                  let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);

                  if (endPage - startPage < maxPagesToShow - 1) {
                    startPage = Math.max(1, endPage - maxPagesToShow + 1);
                  }

                  const pages = [];

                  if (startPage > 1) {
                    pages.push(
                      <button
                        key={1}
                        onClick={() => handlePageChange(1)}
                        className="px-3 py-2 rounded text-[#3bb77e] hover:bg-[#def9ec] transition-colors text-[12px] font-['Poppins',sans-serif]"
                      >
                        1
                      </button>
                    );
                    if (startPage > 2) {
                      pages.push(
                        <span key="ellipsis-start" className="px-2 text-gray-400">...</span>
                      );
                    }
                  }

                  for (let page = startPage; page <= endPage; page++) {
                    pages.push(
                      <button
                        key={page}
                        onClick={() => handlePageChange(page)}
                        className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${currentPage === page
                          ? 'bg-[#3bb77e] text-white'
                          : 'text-[#3bb77e] hover:bg-[#def9ec]'
                          }`}
                      >
                        {page}
                      </button>
                    );
                  }

                  if (endPage < totalPages) {
                    if (endPage < totalPages - 1) {
                      pages.push(
                        <span key="ellipsis-end" className="px-2 text-gray-400">...</span>
                      );
                    }
                    pages.push(
                      <button
                        key={totalPages}
                        onClick={() => handlePageChange(totalPages)}
                        className="px-3 py-2 rounded text-[#3bb77e] hover:bg-[#def9ec] transition-colors text-[12px] font-['Poppins',sans-serif]"
                      >
                        {totalPages}
                      </button>
                    );
                  }

                  return pages;
                })()}

                <button
                  onClick={() => handlePageChange(pagination.currentPage + 1)}
                  disabled={pagination.currentPage === pagination.totalPages}
                  className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${pagination.currentPage === pagination.totalPages
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-[#3bb77e] hover:bg-[#def9ec]'
                    }`}
                >
                  Next ›
                </button>
              </div>
            </div>
          )}

          {/* Results Summary */}
          {paginatedDetailInventory.length > 0 && (
            <div className="text-center text-sm text-gray-600 font-['Poppins',sans-serif] mt-4">
              Showing {((pagination.currentPage - 1) * pagination.itemsPerPage) + 1} to {Math.min(pagination.currentPage * pagination.itemsPerPage, filteredDetailInventory.length)} of {filteredDetailInventory.length} batches
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!isLoading && !error && filteredDetailInventory.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 bg-white rounded-lg">
          <p className="text-gray-500 text-sm">No batch inventory items found</p>
          {(searchQuery || filterView !== 'all') && (
            <button
              onClick={() => {
                setSearchQuery('');
                setFilterView('all');
              }}
              className="mt-2 text-sm text-emerald-600 hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      {/* Modals */}
      {/* StockOutBatchModal removed - use CreateStockOutOrderModal at Inventory level */}

      <AdjustStockBatchModal
        isOpen={adjustModal.isOpen}
        onClose={() => setAdjustModal({ isOpen: false, item: null })}
        onSuccess={handleMovementSuccess}
        detailInventory={adjustModal.item}
      />

      <MovementHistoryBatchModal
        isOpen={historyModal.isOpen}
        onClose={() => setHistoryModal({ isOpen: false, item: null })}
        detailInventory={historyModal.item}
      />

      <UpdateLocationModal
        isOpen={updateLocationModal.isOpen}
        onClose={() => setUpdateLocationModal({ isOpen: false, item: null })}
        onSuccess={handleUpdateLocationSuccess}
        detailInventory={updateLocationModal.item}
      />
    </div>
  );
};

export default DetailInventories;
