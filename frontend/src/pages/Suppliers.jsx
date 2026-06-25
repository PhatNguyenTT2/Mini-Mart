import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Breadcrumb } from '../components/Breadcrumb';
import { SupplierListHeader, SupplierList } from '../components/SupplierList';
import supplierService from '../services/supplierService';

const Suppliers = () => {
  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Suppliers', href: null },
  ];

  // State management
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 10,
    total: 0,
    pages: 0
  });

  // Filters
  const [filters, setFilters] = useState({
    page: 1,
    limit: 10
  });

  const [termFilter, setTermFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('active'); // Default: show only active

  const fetchCounterRef = useRef(0);

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchParams] = useSearchParams();

  // Sync search query from URL parameters
  useEffect(() => {
    const searchVal = searchParams.get('search') || '';
    setSearchQuery(searchVal);
  }, [searchParams]);

  // Sort state
  const [sortField, setSortField] = useState('id');
  const [sortOrder, setSortOrder] = useState('asc');

  // Add Supplier Modal state
  const [addOpen, setAddOpen] = useState(false);

  // Edit Supplier Modal state
  const [editOpen, setEditOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState(null);

  // Fetch suppliers from API
  const fetchSuppliers = async () => {
    const requestId = ++fetchCounterRef.current;
    try {
      setLoading(true);
      setError(null);

      const params = {
        page: filters.page,
        limit: filters.limit,
        sortBy: sortField,
        sortOrder: sortOrder
      };

      // Add search to params if exists
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }

      // Add filters
      if (termFilter) {
        params.paymentTerms = termFilter;
      }
      if (activeFilter) {
        if (activeFilter === 'active') params.isActive = true;
        if (activeFilter === 'inactive') params.isActive = false;
      }

      const response = await supplierService.getAllSuppliers(params);

      // Avoid race conditions: ignore response if a newer fetch was started
      if (requestId !== fetchCounterRef.current) {
        return;
      }

      // API returns { success, data: [...suppliers], pagination: {...} }
      if (response.success) {
        const suppliersList = Array.isArray(response.data) ? response.data : [];
        setSuppliers(suppliersList);

        if (response.pagination) {
          setPagination({
            page: response.pagination.page || 1,
            limit: response.pagination.limit || 10,
            total: response.pagination.total || 0,
            pages: response.pagination.totalPages || 1
          });
        }
      }
    } catch (err) {
      if (requestId !== fetchCounterRef.current) return;
      console.error('Error fetching suppliers:', err);
      setError(err.response?.data?.error || err.message || 'Failed to fetch suppliers. Please try again.');
    } finally {
      if (requestId === fetchCounterRef.current) {
        setLoading(false);
      }
    }
  };

  // Fetch suppliers on component mount and when filters change
  useEffect(() => {
    fetchSuppliers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.page, filters.limit, searchQuery, sortField, sortOrder, termFilter, activeFilter]);

  // Handle filter changes
  const handleItemsPerPageChange = (newLimit) => {
    setFilters({ ...filters, limit: newLimit, page: 1 });
  };

  // Handle search
  const handleSearch = (query) => {
    setSearchQuery(query);
    setFilters({ ...filters, page: 1 }); // Reset to first page when searching
  };

  // Handle column sort
  const handleColumnSort = (field) => {
    let newSortOrder = 'asc';

    // Toggle sort order if clicking the same field
    if (sortField === field) {
      newSortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
    }

    setSortField(field);
    setSortOrder(newSortOrder);
    setFilters({ ...filters, page: 1 }); // Reset to first page when sorting
  };

  // Toggle active handler
  const handleToggleActive = async (supplier) => {
    try {
      const newStatus = !supplier.isActive;
      await supplierService.updateSupplier(supplier.id, { isActive: newStatus });
      await fetchSuppliers();
    } catch (e) {
      console.error('Failed to toggle supplier active:', e);
      alert(e.response?.data?.error || e.message || 'Failed to update supplier status');
    }
  };

  // Delete supplier handler
  const handleDeleteSupplier = async (supplier) => {
    // Validation: must be inactive to delete
    if (supplier.isActive !== false) {
      alert('Cannot delete active supplier. Please deactivate it first.');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete supplier ${supplier.companyName || supplier.supplierCode}?`)) {
      return;
    }

    try {
      await supplierService.deleteSupplier(supplier.id);
      await fetchSuppliers();
    } catch (e) {
      console.error('Failed to delete supplier:', e);
      alert(e.response?.data?.error || e.message || 'Failed to delete supplier');
    }
  };

  // Handle add supplier
  const handleAddSupplier = () => {
    setAddOpen(true);
  };

  const handleAddSuccess = () => {
    setAddOpen(false);
    fetchSuppliers();
  };

  // Handle edit supplier
  const handleEditSupplier = (supplier) => {
    setEditingSupplier(supplier);
    setEditOpen(true);
  };

  const handleEditSuccess = () => {
    setEditOpen(false);
    setEditingSupplier(null);
    fetchSuppliers();
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Supplier List Header */}
      <SupplierListHeader
        itemsPerPage={filters.limit}
        onItemsPerPageChange={handleItemsPerPageChange}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onSearch={handleSearch}
        onAddSupplier={handleAddSupplier}
        termFilter={termFilter}
        onTermFilterChange={setTermFilter}
        activeFilter={activeFilter}
        onActiveFilterChange={setActiveFilter}
      />

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p className="font-medium">Error loading suppliers</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={fetchSuppliers}
            className="mt-2 text-sm underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Supplier List Table */}
      {!loading && !error && (
        <>
          <SupplierList
            suppliers={suppliers}
            onSort={handleColumnSort}
            sortField={sortField}
            sortOrder={sortOrder}
            addModalOpen={addOpen}
            onCloseAddModal={() => setAddOpen(false)}
            onAddSuccess={handleAddSuccess}
            editModalOpen={editOpen}
            editSupplier={editingSupplier}
            onCloseEditModal={() => {
              setEditOpen(false);
              setEditingSupplier(null);
            }}
            onEditSuccess={handleEditSuccess}
            onEdit={handleEditSupplier}
            onToggleActive={handleToggleActive}
            onDelete={handleDeleteSupplier}
          />

          {/* Pagination */}
          {pagination.pages > 1 && (
            <div className="flex items-center justify-center mt-6">
              <div className="flex items-center gap-2">
                {/* Previous button */}
                <button
                  onClick={() => setFilters({ ...filters, page: pagination.page - 1 })}
                  disabled={pagination.page === 1}
                  className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${pagination.page === 1
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-[#3bb77e] hover:bg-[#def9ec]'
                    }`}
                >
                  ‹ Previous
                </button>

                {/* Page numbers */}
                {(() => {
                  const maxPagesToShow = 5;
                  const totalPages = pagination.pages;
                  const currentPage = pagination.page;

                  let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
                  let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);

                  if (endPage - startPage < maxPagesToShow - 1) {
                    startPage = Math.max(1, endPage - maxPagesToShow + 1);
                  }

                  const pages = [];

                  // First page + ellipsis
                  if (startPage > 1) {
                    pages.push(
                      <button
                        key={1}
                        onClick={() => setFilters({ ...filters, page: 1 })}
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
                        onClick={() => setFilters({ ...filters, page })}
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
                        onClick={() => setFilters({ ...filters, page: totalPages })}
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
                  onClick={() => setFilters({ ...filters, page: pagination.page + 1 })}
                  disabled={pagination.page === pagination.pages}
                  className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${pagination.page === pagination.pages
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
          {suppliers.length > 0 && (
            <div className="text-center text-sm text-gray-600 font-['Poppins',sans-serif] mt-4">
              Showing {((pagination.page - 1) * pagination.limit) + 1} to{' '}
              {Math.min(pagination.page * pagination.limit, pagination.total)} of{' '}
              {pagination.total} suppliers
            </div>
          )}

          {/* Empty State */}
          {suppliers.length === 0 && !loading && (
            <div className="bg-white rounded-lg shadow-sm p-12 text-center">
              <p className="text-gray-500 text-[14px] font-['Poppins',sans-serif]">
                No suppliers found
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Suppliers;