import React, { useState, useEffect } from 'react';
import { Breadcrumb } from '../components/Breadcrumb';
import { PaymentListHeader } from '../components/PaymentList/PaymentListHeader';
import { PaymentList } from '../components/PaymentList/PaymentList';
import { AddPaymentModal } from '../components/PaymentList/AddPaymentModal';
import { EditPaymentModal } from '../components/PaymentList/EditPaymentModal';
import paymentService from '../services/paymentService';

export const Payments = () => {
  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Payments', href: '/payments' },
  ];

  const [payments, setPayments] = useState([]);
  const [filteredPayments, setFilteredPayments] = useState([]);
  const [paginatedPayments, setPaginatedPayments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal states (for future implementation)
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState(null);

  // Filters and sorting
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  const [methodFilter, setMethodFilter] = useState('all');
  const [referenceFilter, setReferenceFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortField, setSortField] = useState('createdAt');
  const [sortOrder, setSortOrder] = useState('desc');

  // Pagination state
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    itemsPerPage: 10,
  });

  // Fetch payments on component mount
  useEffect(() => {
    fetchPayments();
  }, []);

  // Apply search, filters and sorting when data or filters change
  useEffect(() => {
    let result = [...payments];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      result = result.filter(payment =>
        payment.paymentNumber?.toLowerCase().includes(query)
      );
    }

    // Apply payment method filter
    if (methodFilter !== 'all') {
      result = result.filter(payment => payment.paymentMethod === methodFilter);
    }

    // Apply reference type filter
    if (referenceFilter !== 'all') {
      result = result.filter(payment => payment.referenceType === referenceFilter);
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      result = result.filter(payment => payment.status === statusFilter);
    }

    // Apply sorting
    result.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      // Handle null/undefined values
      if (aVal == null) aVal = '';
      if (bVal == null) bVal = '';

      // Handle different data types
      if (sortField === 'amount') {
        aVal = Number(aVal) || 0;
        bVal = Number(bVal) || 0;
      } else if (sortField === 'paymentDate') {
        aVal = new Date(aVal).getTime();
        bVal = new Date(bVal).getTime();
      } else if (sortField === 'paymentNumber' || sortField === 'referenceType' || sortField === 'paymentMethod' || sortField === 'status') {
        aVal = String(aVal).toLowerCase();
        bVal = String(bVal).toLowerCase();
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    setFilteredPayments(result);

    // Update pagination
    const totalPages = Math.ceil(result.length / itemsPerPage);
    setPagination(prev => ({
      ...prev,
      currentPage: 1, // Reset to first page on filter change
      totalPages,
      itemsPerPage,
    }));
  }, [payments, searchQuery, methodFilter, referenceFilter, statusFilter, sortField, sortOrder, itemsPerPage]);

  // Paginate filtered payments
  useEffect(() => {
    const startIndex = (pagination.currentPage - 1) * pagination.itemsPerPage;
    const endIndex = startIndex + pagination.itemsPerPage;
    setPaginatedPayments(filteredPayments.slice(startIndex, endIndex));
  }, [filteredPayments, pagination.currentPage, pagination.itemsPerPage]);

  const fetchPayments = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await paymentService.getAllPayments({
        limit: 1000, // Get all payments for client-side filtering
        sortBy: 'createdAt',
        sortOrder: 'desc'
      });

      if (response.success && response.data && response.data.payments) {
        setPayments(response.data.payments);
      } else if (Array.isArray(response)) {
        setPayments(response);
      } else {
        console.error('Unexpected response structure:', response);
        setPayments([]);
      }
    } catch (err) {
      console.error('Error fetching payments:', err);
      setError(err.message || 'Failed to load payments');
      setPayments([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleColumnSort = (field, order) => {
    setSortField(field);
    setSortOrder(order);
  };

  const handleSearch = (query) => {
    setSearchQuery(query);
  };

  const handleSearchChange = (query) => {
    setSearchQuery(query);
  };

  const handleItemsPerPageChange = (value) => {
    setItemsPerPage(value);
  };

  const handleMethodFilterChange = (value) => {
    setMethodFilter(value);
  };

  const handleReferenceFilterChange = (value) => {
    setReferenceFilter(value);
  };

  const handleStatusFilterChange = (value) => {
    setStatusFilter(value);
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({
      ...prev,
      currentPage: newPage
    }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleAddPayment = () => {
    setShowAddModal(true);
  };

  const handleAddSuccess = (response) => {
    console.log('Payment created:', response);
    fetchPayments(); // Refresh the list
    // Optional: Show success toast notification
  };

  const handleUpdateStatus = async (payment, newStatus) => {
    try {
      await paymentService.updatePaymentStatus(payment.id, newStatus);
      fetchPayments(); // Refresh the list
    } catch (err) {
      console.error('Error updating payment status:', err);
      alert(err.response?.data?.error?.message || err.message || 'Failed to update payment status');
    }
  };

  const handleEdit = (payment) => {
    // Only allow editing pending payments
    if (payment.status !== 'pending') {
      alert('Only pending payments can be edited.');
      return;
    }
    setSelectedPayment(payment);
    setShowEditModal(true);
  };

  const handleEditSuccess = () => {
    console.log('Payment updated successfully');
    fetchPayments(); // Refresh the list
    setShowEditModal(false);
    setSelectedPayment(null);
  };

  const handleDelete = async (payment) => {
    // Only allow deleting pending or cancelled payments
    if (!['pending', 'cancelled'].includes(payment.status)) {
      alert('Only pending or cancelled payments can be deleted.');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete payment "${payment.paymentNumber}"?`)) {
      return;
    }

    try {
      await paymentService.deletePayment(payment.id);
      alert('Payment deleted successfully!');
      fetchPayments(); // Refresh the list
    } catch (err) {
      console.error('Error deleting payment:', err);
      alert(err.response?.data?.error?.message || err.message || 'Failed to delete payment');
    }
  };

  const handleRefund = async (payment) => {
    if (payment.status !== 'completed') {
      alert('Only completed payments can be refunded.');
      return;
    }

    const confirmMsg = `Are you sure you want to refund payment "${payment.paymentNumber}"?\n\nAmount: ${new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(payment.amount)}\n\nNote: This only processes the financial refund. Inventory return must be done separately on the Order page.`;

    if (!window.confirm(confirmMsg)) {
      return;
    }

    try {
      await paymentService.refundPayment(payment.id);
      alert('Payment refunded successfully!');
      fetchPayments();
    } catch (err) {
      console.error('Error refunding payment:', err);
      alert(err.response?.data?.error?.message || err.message || 'Failed to refund payment');
    }
  };

  const hasActiveFilters = searchQuery || methodFilter !== 'all' || referenceFilter !== 'all' || statusFilter !== 'all';

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Payment List Header */}
      <PaymentListHeader
        itemsPerPage={itemsPerPage}
        onItemsPerPageChange={handleItemsPerPageChange}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        onSearch={handleSearch}
        onAddPayment={handleAddPayment}
        methodFilter={methodFilter}
        onMethodFilterChange={handleMethodFilterChange}
        referenceFilter={referenceFilter}
        onReferenceFilterChange={handleReferenceFilterChange}
        statusFilter={statusFilter}
        onStatusFilterChange={handleStatusFilterChange}
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
          <p className="font-medium">Error loading payments</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={fetchPayments}
            className="mt-2 text-sm underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Payment List Table */}
      {!isLoading && !error && (
        <>
          <PaymentList
            payments={paginatedPayments}
            onSort={handleColumnSort}
            sortField={sortField}
            sortOrder={sortOrder}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onUpdateStatus={handleUpdateStatus}
            onRefund={handleRefund}
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
          {paginatedPayments.length > 0 && (
            <div className="text-center text-sm text-gray-600 font-['Poppins',sans-serif] mt-4">
              Showing {((pagination.currentPage - 1) * pagination.itemsPerPage) + 1} to{' '}
              {Math.min(pagination.currentPage * pagination.itemsPerPage, filteredPayments.length)} of{' '}
              {filteredPayments.length} payments
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!isLoading && !error && filteredPayments.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 bg-white rounded-lg">
          <p className="text-gray-500 text-sm">No payments found</p>
          {hasActiveFilters && (
            <button
              onClick={() => {
                setSearchQuery('');
                setMethodFilter('all');
                setReferenceFilter('all');
                setStatusFilter('all');
              }}
              className="mt-2 text-sm text-emerald-600 hover:underline"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}

      {/* Add Payment Modal */}
      <AddPaymentModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleAddSuccess}
      />

      {/* Edit Payment Modal */}
      <EditPaymentModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedPayment(null);
        }}
        onSuccess={handleEditSuccess}
        payment={selectedPayment}
      />
    </div>
  );
};

export default Payments;
