import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Breadcrumb } from '../components/Breadcrumb';
import { InventoryList, InventoryListHeader, MovementHistoryModal, TransferStockBulkModal } from '../components/InventoryList';
import inventoryService from '../services/inventoryService';

export const Inventories = () => {
  const navigate = useNavigate();

  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Inventories', href: '/inventories' },
  ];

  const [inventory, setInventory] = useState([]);
  const [filteredInventory, setFilteredInventory] = useState([]);
  const [paginatedInventory, setPaginatedInventory] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters and sorting
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('productId');
  const [sortOrder, setSortOrder] = useState('asc');
  const [filterView, setFilterView] = useState('all'); // all, low-stock, out-of-stock, needs-reorder

  // Pagination state
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    itemsPerPage: 10,
  });

  // Movement History Modal state
  const [movementHistoryModal, setMovementHistoryModal] = useState({ isOpen: false, item: null });

  // Bulk Transfer Modal state
  const [bulkTransferModal, setBulkTransferModal] = useState(false);

  // Fetch inventory on component mount
  useEffect(() => {
    fetchInventory();
  }, []);

  // Apply filters and sorting when data or filters change
  useEffect(() => {
    let result = [...inventory];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      result = result.filter(item =>
        item.product?.name?.toLowerCase().includes(query) ||
        String(item.productId).includes(query)
      );
    }

    // Apply view filter
    if (filterView === 'low-stock') {
      result = result.filter(item =>
        item.quantityAvailable > 0 && item.quantityAvailable <= item.reorderPoint
      );
    } else if (filterView === 'out-of-stock') {
      result = result.filter(item => item.quantityAvailable === 0);
    } else if (filterView === 'needs-reorder') {
      result = result.filter(item => item.needsReorder === true);
    }

    // Apply sorting
    result.sort((a, b) => {
      let aVal, bVal;

      // Handle product-related fields
      if (sortField === 'productId') {
        aVal = a.productId || 0;
        bVal = b.productId || 0;
      } else if (sortField === 'productName') {
        aVal = a.product?.name || '';
        bVal = b.product?.name || '';
      } else {
        aVal = a[sortField];
        bVal = b[sortField];
      }

      // Handle null/undefined values
      if (aVal == null) aVal = '';
      if (bVal == null) bVal = '';

      // Handle different data types
      if (['quantityOnHand', 'quantityOnShelf', 'quantityReserved', 'quantityAvailable', 'reorderPoint', 'productId'].includes(sortField)) {
        aVal = Number(aVal) || 0;
        bVal = Number(bVal) || 0;
      } else if (sortField === 'productName') {
        aVal = String(aVal).toLowerCase();
        bVal = String(bVal).toLowerCase();
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    setFilteredInventory(result);

    // Update pagination
    const totalPages = Math.ceil(result.length / itemsPerPage);
    setPagination(prev => ({
      ...prev,
      currentPage: 1, // Reset to first page on filter change
      totalPages,
      itemsPerPage,
    }));
  }, [inventory, searchQuery, sortField, sortOrder, itemsPerPage, filterView]);

  // Paginate filtered inventory
  useEffect(() => {
    const startIndex = (pagination.currentPage - 1) * pagination.itemsPerPage;
    const endIndex = startIndex + pagination.itemsPerPage;
    setPaginatedInventory(filteredInventory.slice(startIndex, endIndex));
  }, [filteredInventory, pagination.currentPage, pagination.itemsPerPage]);

  const fetchInventory = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Fetch all inventory with product details populated
      const response = await inventoryService.getAllInventories();

      // Handle response structure
      if (response.success && response.data && response.data.inventories) {
        setInventory(response.data.inventories);
      } else if (Array.isArray(response)) {
        // Fallback if response is directly an array
        setInventory(response);
      } else {
        console.error('Unexpected response structure:', response);
        setInventory([]);
      }
    } catch (err) {
      console.error('Error fetching inventory:', err);
      setError(err.message || 'Failed to load inventory');
      setInventory([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleColumnSort = (field) => {
    if (sortField === field) {
      // Toggle sort order if clicking the same field
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      // Set new field and default to ascending
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
    // Scroll to top smoothly
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleViewDetail = (productId) => {
    if (productId) {
      navigate(`/inventory/detail/${productId}`);
    }
  };

  const handleEdit = (item) => {
    // TODO: Implement edit inventory settings modal
    console.log('Edit inventory:', item);
    alert('Edit inventory settings modal - To be implemented');
  };

  const handleViewMovementHistory = (item) => {
    setMovementHistoryModal({ isOpen: true, item });
  };

  const handleBulkTransfer = () => {
    setBulkTransferModal(true);
  };

  const handleBulkTransferSuccess = () => {
    fetchInventory(); // Refresh inventory list
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Inventory List Header */}
      <InventoryListHeader
        itemsPerPage={itemsPerPage}
        onItemsPerPageChange={handleItemsPerPageChange}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        filterView={filterView}
        onFilterViewChange={handleFilterViewChange}
        onBulkTransfer={handleBulkTransfer}
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
          <p className="font-medium">Error loading inventory</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={fetchInventory}
            className="mt-2 text-sm underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Inventory List Table */}
      {!isLoading && !error && (
        <>
          <InventoryList
            inventory={paginatedInventory}
            onSort={handleColumnSort}
            sortField={sortField}
            sortOrder={sortOrder}
            onViewDetail={handleViewDetail}
            onEdit={handleEdit}
            onViewMovementHistory={handleViewMovementHistory}
          />

          {/* Pagination */}
          {pagination.totalPages > 1 && (
            <div className="flex items-center justify-center mt-6">
              <div className="flex items-center gap-2">
                {/* Previous button */}
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

                {/* Page numbers */}
                {(() => {
                  const maxPagesToShow = 5;
                  const { totalPages, currentPage } = pagination;

                  // Calculate start and end page numbers to display
                  let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
                  let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);

                  // Adjust start if we're near the end
                  if (endPage - startPage < maxPagesToShow - 1) {
                    startPage = Math.max(1, endPage - maxPagesToShow + 1);
                  }

                  const pages = [];

                  // First page + ellipsis
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
                        <span key="ellipsis-start" className="px-2 text-gray-400">
                          ...
                        </span>
                      );
                    }
                  }

                  // Page numbers
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

                  // Ellipsis + last page
                  if (endPage < totalPages) {
                    if (endPage < totalPages - 1) {
                      pages.push(
                        <span key="ellipsis-end" className="px-2 text-gray-400">
                          ...
                        </span>
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

                {/* Next button */}
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
          {paginatedInventory.length > 0 && (
            <div className="text-center text-sm text-gray-600 font-['Poppins',sans-serif] mt-4">
              Showing {((pagination.currentPage - 1) * pagination.itemsPerPage) + 1} to {Math.min(pagination.currentPage * pagination.itemsPerPage, filteredInventory.length)} of {filteredInventory.length} items
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!isLoading && !error && filteredInventory.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 bg-white rounded-lg">
          <p className="text-gray-500 text-sm">No inventory items found</p>
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

      {/* Movement History Modal */}
      <MovementHistoryModal
        isOpen={movementHistoryModal.isOpen}
        onClose={() => setMovementHistoryModal({ isOpen: false, item: null })}
        inventory={movementHistoryModal.item}
      />

      {/* Bulk Transfer Modal */}
      <TransferStockBulkModal
        isOpen={bulkTransferModal}
        onClose={() => setBulkTransferModal(false)}
        onSuccess={handleBulkTransferSuccess}
      />
    </div>
  );
};

export default Inventories;