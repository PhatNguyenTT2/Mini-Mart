import React, { useState, useEffect, useCallback, useMemo } from 'react';
import posDataService from '../../services/posDataService';

export const POSEmployeeOrdersModal = ({ isOpen, onClose, currentEmployee, onLoadDraftOrder, initialSearch = '' }) => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState({});
  const [error, setError] = useState(null);

  // Filters & Pagination States
  const [activeTab, setActiveTab] = useState('all'); // all, draft, confirmed, paid, cancelled
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  useEffect(() => {
    if (isOpen && currentEmployee?.id) {
      fetchEmployeeOrders();
      if (initialSearch) {
        setSearchQuery(initialSearch);
      }
    }
    if (!isOpen) {
      setSearchQuery('');
    }
  }, [isOpen, currentEmployee?.id, initialSearch]);

  const fetchEmployeeOrders = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await posDataService.getEmployeeOrders(currentEmployee.id, { include: 'details' });

      if (result.status === 'success' || result.success) {
        const orderList = result.data?.orders || result.data || [];
        setOrders(orderList);
      } else {
        throw new Error(result.error?.message || 'Failed to fetch items');
      }
    } catch (err) {
      console.error('Error fetching employee order history:', err);
      setError(err.message || 'Failed to fetch employee order history');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteDraft = async (e, orderId, orderNumber) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete draft order ${orderNumber}?`)) {
      return;
    }

    try {
      setDeleteLoading(prev => ({ ...prev, [orderId]: true }));
      await posDataService.deleteOrder(orderId);
      setOrders(prev => prev.filter(o => o.id !== orderId));
    } catch (err) {
      alert(err.message || 'Failed to delete draft order');
    } finally {
      setDeleteLoading(prev => ({ ...prev, [orderId]: false }));
    }
  };

  const handleLoadDraft = (order) => {
    onLoadDraftOrder(order);
    onClose();
  };

  // Filtered & Searched Orders
  const processedOrders = useMemo(() => {
    return orders.filter(order => {
      // 1. Status Filter Tab
      if (activeTab !== 'all' && (order.status || '').toLowerCase() !== activeTab) {
        return false;
      }

      // 2. Search Query Filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const matchNumber = (order.orderNumber || '').toLowerCase().includes(query);
        const matchCustomer = order.customerName && (order.customerName).toLowerCase().includes(query);
        return matchNumber || matchCustomer;
      }

      return true;
    });
  }, [orders, activeTab, searchQuery]);

  // Reset to page 1 when criteria changes
  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab, searchQuery]);

  // Paginated chunk
  const paginatedOrders = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    return processedOrders.slice(start, end);
  }, [processedOrders, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(processedOrders.length / itemsPerPage);

  const formatVND = (amount) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    switch (s) {
      case 'draft':
        return <span className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded font-semibold text-xs uppercase font-['Poppins',sans-serif]">Draft</span>;
      case 'confirmed':
        return <span className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded font-semibold text-xs uppercase font-['Poppins',sans-serif]">Confirmed</span>;
      case 'paid':
      case 'completed':
        return <span className="px-2 py-0.5 bg-green-100 text-green-800 rounded font-semibold text-xs uppercase font-['Poppins',sans-serif]">Paid</span>;
      case 'cancelled':
        return <span className="px-2 py-0.5 bg-red-100 text-red-800 rounded font-semibold text-xs uppercase font-['Poppins',sans-serif]">Cancelled</span>;
      default:
        return <span className="px-2 py-0.5 bg-gray-100 text-gray-800 rounded font-semibold text-xs uppercase font-['Poppins',sans-serif]">{status}</span>;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999] animate-fade-in">
      <div className="bg-white rounded-xl shadow-2xl max-w-5xl w-full mx-4 max-h-[92vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-emerald-50">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-bold text-gray-900 font-['Poppins',sans-serif] flex items-center gap-2">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="text-emerald-600">
                  <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>My Order History</span>
              </h2>
              <p className="text-xs text-gray-500 mt-1 font-['Poppins',sans-serif]">
                Manage all orders created by <strong>{currentEmployee?.fullName || 'you'}</strong>
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-200 rounded-full transition-colors text-gray-500"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        </div>

        {/* Toolbar & Filter Tabs */}
        <div className="bg-gray-50 border-b border-gray-200 px-6 py-3 flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Status Tabs */}
          <div className="flex flex-wrap gap-1">
            {['all', 'draft', 'confirmed', 'paid', 'cancelled'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold uppercase transition-all font-['Poppins',sans-serif] ${activeTab === tab
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-250 hover:bg-gray-200'
                  }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div className="relative max-w-xs w-full">
            <input
              type="text"
              placeholder="Search by Order # or Customer..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full text-xs p-2 pl-8 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-['Poppins',sans-serif]"
            />
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="absolute left-2.5 top-2.5 text-gray-400">
              <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2.5 text-gray-450 hover:text-gray-700 text-xs font-bold font-sans"
              >
                ×
              </button>
            )}
          </div>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-gray-50/50">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mb-3"></div>
              <p className="text-sm text-gray-500 font-['Poppins',sans-serif]">Loading order logs...</p>
            </div>
          ) : error ? (
            <div className="text-center py-16">
              <svg className="w-16 h-16 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-red-600 font-bold mb-2 font-['Poppins',sans-serif]">Failed to Load History</p>
              <p className="text-gray-500 text-sm mb-4 font-['Poppins',sans-serif]">{error}</p>
              <button
                onClick={fetchEmployeeOrders}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition font-['Poppins',sans-serif]"
              >
                Reload Context
              </button>
            </div>
          ) : paginatedOrders.length === 0 ? (
            <div className="text-center py-20 bg-white rounded-xl border border-dashed border-gray-300">
              <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-gray-500 font-semibold font-['Poppins',sans-serif]">No orders matched criteria</p>
              <p className="text-xs text-gray-400 mt-2 font-['Poppins',sans-serif]">Try changing filter tabs or check spelling</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {paginatedOrders.map((order) => {
                const isDraft = (order.status || '').toLowerCase() === 'draft';
                return (
                  <div
                    key={order.id || order._id}
                    className={`bg-white rounded-lg border p-4 shadow-sm transition-all flex flex-col justify-between ${isDraft
                      ? 'border-amber-200 hover:border-amber-400 hover:shadow-md'
                      : 'border-gray-200 hover:border-emerald-300 hover:shadow-md'
                      }`}
                  >
                    <div>
                      {/* Top Info line */}
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <p className="font-bold text-[15px] font-['Poppins',sans-serif] text-gray-900">{order.orderNumber}</p>
                          <p className="text-[11px] text-gray-400 mt-0.5 font-['Poppins',sans-serif]">{formatDate(order.orderDate)}</p>
                        </div>
                        {getStatusBadge(order.status)}
                      </div>

                      {/* Customer Info */}
                      <div className="mt-2 text-xs text-gray-600 font-['Poppins',sans-serif] space-y-1">
                        <div className="flex items-center gap-1.5">
                          <span className="text-gray-400 w-16">Customer:</span>
                          <span className="font-semibold text-gray-800">
                            {order.customerName
                              ? `${order.customerName} (${order.customerType || 'retail'})`
                              : !order.customerId
                                ? 'Guest Customer'
                                : `Customer #${order.customerId}`}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-gray-400 w-16">Details:</span>
                          <span className="font-medium text-gray-800">{order.details?.length || 0} item(s)</span>
                        </div>
                      </div>

                      {/* Render preview items */}
                      {order.details && order.details.length > 0 && (
                        <div className="mt-3 bg-gray-50 rounded p-2 text-[11px] text-gray-700 font-['Poppins',sans-serif] space-y-1">
                          {order.details.slice(0, 2).map((item, idx) => (
                            <div key={idx} className="flex justify-between">
                              <span className="truncate flex-1">• {item.productName || `Product #${item.productId}`}</span>
                              <span className="font-bold ml-2">x{item.quantity}</span>
                            </div>
                          ))}
                          {order.details.length > 2 && (
                            <p className="text-[10px] text-gray-400 italic">+{order.details.length - 2} more items</p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Bottom Action Footer */}
                    <div className="mt-4 pt-3 border-t border-gray-150 flex items-center justify-between">
                      <span className="text-base font-bold text-emerald-600 font-['Poppins',sans-serif]">
                        {formatVND(order.total)}
                      </span>

                      {/* Context actions */}
                      <div className="flex gap-2">
                        {isDraft ? (
                          <>
                            <button
                              onClick={(e) => handleDeleteDraft(e, order.id, order.orderNumber)}
                              disabled={deleteLoading[order.id]}
                              className="p-1 px-2.5 bg-red-50 text-red-650 text-red-650 text-red-600 border border-red-100 rounded-md text-[11px] font-semibold hover:bg-red-100 disabled:opacity-50 transition font-['Poppins',sans-serif]"
                              title="Delete Draft"
                            >
                              {deleteLoading[order.id] ? 'Deleting...' : 'Delete'}
                            </button>
                            <button
                              onClick={() => handleLoadDraft(order)}
                              className="p-1 px-3 bg-amber-500 text-white rounded-md text-[11px] font-semibold hover:bg-amber-600 transition font-['Poppins',sans-serif]"
                            >
                              Load Cart
                            </button>
                          </>
                        ) : (
                          <span className="text-[10px] text-gray-400 italic font-['Poppins',sans-serif]">
                            read-only order
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer with Pagination Control and Summary */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-100 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-xs text-gray-500 font-['Poppins',sans-serif]">
            Showing {(currentPage - 1) * itemsPerPage + 1} - {Math.min(currentPage * itemsPerPage, processedOrders.length)} of {processedOrders.length} orders
          </div>

          {/* Simple and elegant Web UI Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="px-2.5 py-1 text-xs border border-gray-300 rounded bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition font-['Poppins',sans-serif]"
              >
                ‹ Prev
              </button>
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter(page => Math.abs(page - currentPage) <= 2 || page === 1 || page === totalPages)
                .map((page, idx, arr) => {
                  const showingEllipsis = idx > 0 && page - arr[idx - 1] > 1;
                  return (
                    <React.Fragment key={page}>
                      {showingEllipsis && <span className="text-gray-400 text-xs px-1">...</span>}
                      <button
                        onClick={() => setCurrentPage(page)}
                        className={`px-2.5 py-1 text-xs border rounded transition font-['Poppins',sans-serif] ${currentPage === page
                          ? 'bg-emerald-600 text-white border-emerald-600 font-bold'
                          : 'bg-white border-gray-300 hover:bg-gray-50'
                          }`}
                      >
                        {page}
                      </button>
                    </React.Fragment>
                  );
                })}
              <button
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="px-2.5 py-1 text-xs border border-gray-300 rounded bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition font-['Poppins',sans-serif]"
              >
                Next ›
              </button>
            </div>
          )}

          <button
            onClick={onClose}
            className="px-5 py-1.5 border border-gray-300 text-gray-650 bg-white rounded-lg text-xs font-semibold hover:bg-gray-50 transition font-['Poppins',sans-serif]"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
