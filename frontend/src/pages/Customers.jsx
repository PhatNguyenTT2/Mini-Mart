import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Breadcrumb } from '../components/Breadcrumb';
import { CustomerListHeader, CustomerList } from '../components/CustomerList';
import customerService from '../services/customerService';

const Customers = () => {
  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Customers', href: null },
  ];

  // State management
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    current_page: 1,
    per_page: 10,
    total: 0,
    total_pages: 0
  });

  // Filters
  const [filters, setFilters] = useState({
    page: 1,
    per_page: 10
  });

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchParams] = useSearchParams();

  // Additional Filters
  const [genderFilter, setGenderFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('true'); // Default: show only active

  const fetchCounterRef = useRef(0);

  // Sync search query from URL parameters
  useEffect(() => {
    const searchVal = searchParams.get('search') || '';
    setSearchQuery(searchVal);
    const typeVal = searchParams.get('type') || '';
    setTypeFilter(typeVal);
  }, [searchParams]);

  // Sort state
  const [sortField, setSortField] = useState('id');
  const [sortOrder, setSortOrder] = useState('asc');

  // Modal states
  const [addCustomerModal, setAddCustomerModal] = useState(false);
  const [editCustomerModal, setEditCustomerModal] = useState(false);

  const [selectedCustomer, setSelectedCustomer] = useState(null);

  // Fetch customers from API
  const fetchCustomers = async () => {
    const requestId = ++fetchCounterRef.current;
    try {
      setLoading(true);
      setError(null);

      // Build query params
      const params = {
        page: filters.page,
        limit: filters.per_page,
        sortBy: sortField,
        sortOrder: sortOrder
      };

      // Add search if exists
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }

      // Add filters
      if (genderFilter) {
        params.gender = genderFilter;
      }
      if (typeFilter) {
        params.customerType = typeFilter;
      }
      if (activeFilter !== '') {
        params.isActive = activeFilter;
      }

      const response = await customerService.getAllCustomers(params);

      // Avoid race conditions: ignore response if a newer fetch was started
      if (requestId !== fetchCounterRef.current) {
        return;
      }

      if (response.success) {
        // Map API response to display format
        const formattedCustomers = (response.data.customers || []).map(customer => ({
          id: customer._id || customer.id,
          fullName: customer.fullName,
          email: customer.email || '',
          phone: customer.phone || '',
          address: customer.address || '',
          dateOfBirth: customer.dateOfBirth,
          gender: customer.gender,
          customerType: customer.customerType,
          totalSpent: customer.totalSpent || 0,
          isActive: customer.isActive !== false
        }));

        setCustomers(formattedCustomers);
        setPagination({
          current_page: response.data.pagination.currentPage,
          per_page: response.data.pagination.limit,
          total: response.data.pagination.total,
          total_pages: response.data.pagination.totalPages,
          has_prev: response.data.pagination.currentPage > 1,
          has_next: response.data.pagination.currentPage < response.data.pagination.totalPages
        });
      }
    } catch (err) {
      if (requestId !== fetchCounterRef.current) return;
      console.error('Error fetching customers:', err);
      setError(err.response?.data?.error || err.message || 'Failed to fetch customers');
    } finally {
      if (requestId === fetchCounterRef.current) {
        setLoading(false);
      }
    }
  };

  // Fetch customers on component mount and when filters change
  useEffect(() => {
    fetchCustomers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.page, filters.per_page, sortField, sortOrder, searchQuery, genderFilter, typeFilter, activeFilter]);

  // Handle filter changes
  const handleItemsPerPageChange = (newPerPage) => {
    setFilters({ ...filters, per_page: newPerPage, page: 1 });
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
  };

  // Handle toggle active status
  const handleToggleActive = async (customer) => {
    const newStatus = !customer.isActive;
    try {
      await customerService.toggleActive(customer.id, newStatus);
      await fetchCustomers();
    } catch (err) {
      console.error('Error toggling customer status:', err);
      alert(err.response?.data?.error || 'Failed to update customer status');
    }
  };

  // Handle add customer
  const handleAddCustomer = () => {
    setAddCustomerModal(true);
  };

  // Handle edit customer
  const handleEditCustomer = (customer) => {
    setSelectedCustomer(customer);
    setEditCustomerModal(true);
  };

  // Handle customer created successfully
  const handleCustomerSuccess = () => {
    fetchCustomers(); // Refresh list
  };

  // Handle customer updated successfully
  const handleCustomerUpdateSuccess = () => {
    fetchCustomers(); // Refresh list
    setSelectedCustomer(null);
  };



  // Handle delete customer
  const handleDeleteCustomer = async (customer) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete customer "${customer.fullName}" (ID: ${customer.id})?\n\nThis action cannot be undone.`
    );

    if (!confirmed) return;

    try {
      await customerService.deleteCustomer(customer.id);
      fetchCustomers();
    } catch (error) {
      console.error('Error deleting customer:', error);
      alert(error.response?.data?.error || error.message || 'Failed to delete customer');
    }
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Customer List Header */}
      <CustomerListHeader
        itemsPerPage={filters.per_page}
        onItemsPerPageChange={handleItemsPerPageChange}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onAddCustomer={handleAddCustomer}

        genderFilter={genderFilter}
        onGenderFilterChange={setGenderFilter}
        typeFilter={typeFilter}
        onTypeFilterChange={setTypeFilter}
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
          <p className="font-medium">Error loading customers</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={fetchCustomers}
            className="mt-2 text-sm underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Customer List Table */}
      {!loading && !error && (
        <>
          <CustomerList
            customers={customers}
            onSort={handleColumnSort}
            sortField={sortField}
            sortOrder={sortOrder}
            onToggleActive={handleToggleActive}
            onEdit={handleEditCustomer}
            onDelete={handleDeleteCustomer}
            addModalOpen={addCustomerModal}
            onCloseAddModal={() => setAddCustomerModal(false)}
            onAddSuccess={handleCustomerSuccess}
            editModalOpen={editCustomerModal}
            editCustomer={selectedCustomer}
            onCloseEditModal={() => {
              setEditCustomerModal(false);
              setSelectedCustomer(null);
            }}
            onEditSuccess={handleCustomerUpdateSuccess}
          />

          {/* Pagination */}
          {pagination.total_pages > 1 && (
            <div className="flex items-center justify-center mt-6">
              <div className="flex items-center gap-2">
                {/* Previous button */}
                <button
                  onClick={() => setFilters({ ...filters, page: pagination.current_page - 1 })}
                  disabled={!pagination.has_prev}
                  className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${!pagination.has_prev
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-[#3bb77e] hover:bg-[#def9ec]'
                    }`}
                >
                  ‹ Previous
                </button>

                {/* Page numbers */}
                {(() => {
                  const maxPagesToShow = 5;
                  const totalPages = pagination.total_pages;
                  const currentPage = pagination.current_page;

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
                  onClick={() => setFilters({ ...filters, page: pagination.current_page + 1 })}
                  disabled={!pagination.has_next}
                  className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${!pagination.has_next
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
          {customers.length > 0 && (
            <div className="text-center text-sm text-gray-600 font-['Poppins',sans-serif] mt-4">
              Showing {((pagination.current_page - 1) * pagination.per_page) + 1} to{' '}
              {Math.min(pagination.current_page * pagination.per_page, pagination.total)} of{' '}
              {pagination.total} customers
            </div>
          )}

          {/* Empty State */}
          {customers.length === 0 && !loading && (
            <div className="bg-white rounded-lg shadow-sm p-12 text-center">
              <p className="text-gray-500 text-[14px] font-['Poppins',sans-serif]">
                No customers found
              </p>
            </div>
          )}
        </>
      )}

    </div>
  );
};

export default Customers;
