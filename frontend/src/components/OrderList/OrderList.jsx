import React, { useState, useRef, useEffect } from 'react';
import { ViewOrderPaymentsModal } from './ViewOrderPaymentsModal';

export const OrderList = ({ orders = [], onSort, sortField, sortOrder, onView, onEdit, onDelete, onUpdateStatus, onUpdatePayment, onViewInvoice, onReturnItems, onRefresh }) => {
  const [activeDropdown, setActiveDropdown] = useState(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const dropdownRef = useRef(null);
  const [viewPaymentsModalOpen, setViewPaymentsModalOpen] = useState(false);
  const [viewingPaymentsOrder, setViewingPaymentsOrder] = useState(null);

  const getSortIcon = (field) => {
    if (sortField !== field) {
      return (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M6 3V9M6 3L4 5M6 3L8 5" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    }

    if (sortOrder === 'asc') {
      return (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M6 9V3M6 3L4 5M6 3L8 5" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    } else {
      return (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M6 3V9M6 9L4 7M6 9L8 7" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    }
  };

  const handleSortClick = (field) => {
    if (onSort) {
      const newOrder = sortField === field && sortOrder === 'asc' ? 'desc' : 'asc';
      onSort(field, newOrder);
    }
  };

  // Get status badge color
  const getStatusColor = (status) => {
    const colors = {
      draft: 'bg-gray-100 text-gray-800',
      pending: 'bg-yellow-100 text-yellow-800',
      processing: 'bg-blue-100 text-blue-800',
      shipping: 'bg-purple-100 text-purple-800',
      delivered: 'bg-emerald-100 text-emerald-800',
      cancelled: 'bg-red-100 text-red-800',
      refunded: 'bg-orange-100 text-orange-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  // Get payment status badge color
  const getPaymentColor = (paymentStatus) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      paid: 'bg-emerald-100 text-emerald-800',
      failed: 'bg-red-100 text-red-800',
      partial_refund: 'bg-amber-100 text-amber-800',
      refunded: 'bg-gray-100 text-gray-800'
    };
    return colors[paymentStatus] || 'bg-gray-100 text-gray-800';
  };

  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount || 0);
  };

  // Format date
  const formatDate = (date) => {
    if (!date) return '-';
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Toggle dropdown
  const toggleDropdown = (orderId, type, event) => {
    const dropdownId = `${type}-${orderId}`;

    if (activeDropdown === dropdownId) {
      setActiveDropdown(null);
    } else {
      const buttonRect = event.currentTarget.getBoundingClientRect();
      const leftPosition = type === 'action' ? buttonRect.right - 160 : buttonRect.left;

      setDropdownPosition({
        top: buttonRect.bottom + 4,
        left: leftPosition
      });
      setActiveDropdown(dropdownId);
    }
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setActiveDropdown(null);
      }
    };

    if (activeDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [activeDropdown]);

  return (
    <div className="bg-white rounded-lg shadow-sm">
      {/* Scrollable Container */}
      <div className="overflow-x-auto rounded-lg">
        <div className="min-w-[1000px]">
          {/* Table Header */}
          <div className="flex items-center h-[34px] bg-gray-50 border-b border-gray-200">
            {/* Order Number Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('orderNumber')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Order
                {getSortIcon('orderNumber')}
              </p>
            </div>

            {/* Customer Column */}
            <div className="flex-1 min-w-[140px] px-3 flex items-center">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Customer
              </p>
            </div>

            {/* Order Date Column - Sortable */}
            <div
              className="w-[140px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('orderDate')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Date
                {getSortIcon('orderDate')}
              </p>
            </div>

            {/* Total Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('total')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Total
                {getSortIcon('total')}
              </p>
            </div>

            {/* Status Column - Sortable */}
            <div
              className="w-[110px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('status')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Status
                {getSortIcon('status')}
              </p>
            </div>

            {/* Payment Status Column - Sortable */}
            <div
              className="w-[110px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('paymentStatus')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Payment
                {getSortIcon('paymentStatus')}
              </p>
            </div>

            {/* Delivery Type Column */}
            <div className="w-[90px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Delivery
              </p>
            </div>

            {/* Actions Column */}
            <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Actions
              </p>
            </div>
          </div>

          {/* Table Body */}
          <div className="flex flex-col">
            {orders.map((order, index) => (
              <div
                key={order.id}
                className={`flex items-center min-h-[60px] hover:bg-gray-50 transition-colors ${index !== orders.length - 1 ? 'border-b border-gray-100' : ''
                  }`}
              >
                {/* Order Number */}
                <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[12px] font-medium font-['Poppins',sans-serif] text-[#3bb77e] leading-[20px] truncate">
                    {order.orderNumber || '-'}
                  </p>
                </div>

                {/* Customer */}
                <div className="flex-1 min-w-[140px] px-3 flex flex-col justify-center py-2">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                    {order._customerName || '-'}
                  </p>
                  {order._customerPhone && (
                    <p className="text-[11px] text-gray-500 truncate">{order._customerPhone}</p>
                  )}
                </div>

                {/* Order Date */}
                <div className="w-[140px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[12px] font-normal font-['Poppins',sans-serif] text-gray-600 leading-[20px]">
                    {formatDate(order.orderDate)}
                  </p>
                </div>

                <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                    {formatCurrency(order.totalAmount || order.total)}
                  </p>
                </div>

                {/* Status - Dropdown */}
                <div className="w-[110px] px-3 flex items-center flex-shrink-0">
                  {['delivered', 'cancelled', 'refunded'].includes(order.status) ? (
                    <span
                      className={`${getStatusColor(order.status)} px-2 py-1 rounded inline-flex items-center gap-1`}
                      title="Final status - cannot be changed"
                    >
                      <span className="text-[9px] font-bold font-['Poppins',sans-serif] leading-[10px] uppercase truncate">
                        {order.status}
                      </span>
                    </span>
                  ) : (
                    <button
                      onClick={(e) => toggleDropdown(order.id, 'status', e)}
                      className={`${getStatusColor(order.status)} px-2 py-1 rounded inline-flex items-center gap-1 cursor-pointer hover:opacity-90 transition-opacity`}
                    >
                      <span className="text-[9px] font-bold font-['Poppins',sans-serif] leading-[10px] uppercase truncate">
                        {order.status || 'pending'}
                      </span>
                      <svg width="8" height="5" viewBox="0 0 8 5" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M1 1L4 4L7 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  )}
                </div>

                {/* Payment Status - Read Only (synced from Payment model) */}
                <div className="w-[110px] px-3 flex items-center flex-shrink-0">
                  <span
                    className={`${getPaymentColor(order.paymentStatus)} px-2 py-1 rounded inline-flex items-center gap-1`}
                    title="Payment status is automatically synced from payments. Cannot edit directly."
                  >
                    <span className="text-[9px] font-bold font-['Poppins',sans-serif] leading-[10px] uppercase truncate">
                      {order.paymentStatus || 'pending'}
                    </span>
                  </span>
                </div>

                {/* Delivery Type */}
                <div className="w-[90px] px-3 flex items-center flex-shrink-0">
                  <span className={`text-[10px] font-medium font-['Poppins',sans-serif] px-2 py-0.5 rounded ${order.deliveryType === 'delivery'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-orange-100 text-orange-800'
                    }`}>
                    {order.deliveryType === 'delivery' ? 'Delivery' : 'Pickup'}
                  </span>
                </div>

                {/* Actions */}
                <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                  <button
                    onClick={(e) => toggleDropdown(order.id, 'action', e)}
                    className="p-2 hover:bg-gray-200 rounded-full transition-colors"
                    title="Actions"
                  >
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <circle cx="3" cy="8" r="1.5" fill="#6B7280" />
                      <circle cx="8" cy="8" r="1.5" fill="#6B7280" />
                      <circle cx="13" cy="8" r="1.5" fill="#6B7280" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Empty State */}
          {orders.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No orders found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menu */}
      {activeDropdown && (() => {
        const order = orders.find(o =>
          activeDropdown.includes(o.id)
        );
        if (!order) return null;

        const isStatusDropdown = activeDropdown === `status-${order.id}`;
        const isActionDropdown = activeDropdown === `action-${order.id}`;

        // Render Status Dropdown with context-aware options
        if (isStatusDropdown) {
          const allStatuses = [
            { value: 'draft', label: 'Draft', color: 'bg-gray-100 text-gray-800' },
            { value: 'pending', label: 'Pending', color: 'bg-yellow-100 text-yellow-800' },
            { value: 'shipping', label: 'Shipping', color: 'bg-purple-100 text-purple-800' },
            { value: 'delivered', label: 'Delivered', color: 'bg-emerald-100 text-emerald-800' },
            { value: 'cancelled', label: 'Cancelled', color: 'bg-red-100 text-red-800' },
          ];

          // Context-aware: only show valid transitions
          let allowedValues = [];
          switch (order.status) {
            case 'draft':
              allowedValues = ['draft', 'cancelled'];
              break;
            case 'pending':
              allowedValues = ['pending', 'cancelled'];
              break;
            case 'shipping':
              allowedValues = ['shipping', 'delivered', 'cancelled'];
              break;
            default:
              allowedValues = [order.status];
          }
          const statusOptions = allStatuses.filter(s => allowedValues.includes(s.value));

          return (
            <div
              ref={dropdownRef}
              className="fixed min-w-[140px] bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-[9999]"
              style={{
                top: `${dropdownPosition.top}px`,
                left: `${dropdownPosition.left}px`
              }}
            >
              {statusOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => {
                    if (onUpdateStatus) {
                      onUpdateStatus(order, option.value);
                    }
                    setActiveDropdown(null);
                  }}
                  className="w-full px-3 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2"
                  disabled={order.status === option.value}
                >
                  <span className={`${option.color} px-2 py-0.5 rounded text-[10px] font-bold uppercase`}>
                    {option.label}
                  </span>
                  {order.status === option.value && (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="ml-auto">
                      <path d="M10 3L4.5 8.5L2 6" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </button>
              ))}
            </div>
          );
        }

        // Render Actions Dropdown
        if (isActionDropdown) {
          const canEdit = !['delivered', 'cancelled', 'refunded', 'shipping'].includes(order.status);
          const canDelete = ['draft', 'pending'].includes(order.status) && order.paymentStatus === 'pending';
          const canReturnItems = ['delivered', 'refunded'].includes(order.status) && order.paymentStatus === 'refunded';

          return (
            <div
              ref={dropdownRef}
              className="fixed w-40 bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-[9999]"
              style={{
                top: `${dropdownPosition.top}px`,
                left: `${dropdownPosition.left}px`
              }}
            >
              <button
                onClick={() => {
                  onViewInvoice && onViewInvoice(order);
                  setActiveDropdown(null);
                }}
                className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-purple-50 hover:text-purple-600 transition-colors flex items-center gap-2"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="3" y="2" width="10" height="12" rx="1" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M5 5H11M5 8H11M5 11H9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                View Invoice
              </button>

              {/* View Payments */}
              <button
                onClick={() => {
                  setViewingPaymentsOrder(order);
                  setViewPaymentsModalOpen(true);
                  setActiveDropdown(null);
                }}
                className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors flex items-center gap-2"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M14 4H2C1.44772 4 1 4.44772 1 5V13C1 13.5523 1.44772 14 2 14H14C14.5523 14 15 13.5523 15 13V5C15 4.44772 14.5523 4 14 4Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M1 7H15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M8 2L6 4H10L8 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                View Payments
              </button>

              <button
                onClick={() => {
                  onEdit && onEdit(order);
                  setActiveDropdown(null);
                }}
                disabled={!canEdit}
                className={`w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] transition-colors flex items-center gap-2 ${!canEdit
                  ? 'text-gray-400 cursor-not-allowed opacity-50'
                  : 'text-gray-700 hover:bg-emerald-50 hover:text-emerald-600'
                  }`}
                title={!canEdit ? 'Cannot edit delivered or cancelled orders' : 'Edit order'}
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M11.333 2.00004C11.5081 1.82494 11.716 1.68605 11.9447 1.59129C12.1735 1.49653 12.4187 1.44775 12.6663 1.44775C12.914 1.44775 13.1592 1.49653 13.3879 1.59129C13.6167 1.68605 13.8246 1.82494 13.9997 2.00004C14.1748 2.17513 14.3137 2.383 14.4084 2.61178C14.5032 2.84055 14.552 3.08575 14.552 3.33337C14.552 3.58099 14.5032 3.82619 14.4084 4.05497C14.3137 4.28374 14.1748 4.49161 13.9997 4.66671L5.33301 13.3334L1.33301 14.6667L2.66634 10.6667L11.333 2.00004Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Edit
              </button>

              <div className="border-t border-gray-200 my-1"></div>

              <button
                onClick={() => {
                  if (onReturnItems) {
                    onReturnItems(order);
                  }
                  setActiveDropdown(null);
                }}
                disabled={!canReturnItems}
                className={`w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] transition-colors flex items-center gap-2 ${!canReturnItems
                  ? 'text-gray-400 cursor-not-allowed opacity-50'
                  : 'text-gray-700 hover:bg-teal-50 hover:text-teal-600'
                  }`}
                title={
                  !canReturnItems
                    ? 'Refund all payments and mark order as refunded first'
                    : 'Return items to warehouse inventory'
                }
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M6 3L2 7L6 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M2 7H10C12.2091 7 14 8.79086 14 11V13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Return Items
              </button>

              <button
                onClick={() => {
                  onDelete && onDelete(order);
                  setActiveDropdown(null);
                }}
                disabled={!canDelete}
                className={`w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] transition-colors flex items-center gap-2 ${!canDelete
                  ? 'text-gray-400 cursor-not-allowed opacity-50'
                  : 'text-gray-700 hover:bg-red-50 hover:text-red-600'
                  }`}
                title={
                  !canDelete
                    ? 'Can only delete draft or pending orders with pending payment'
                    : 'Delete order'
                }
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M2 4H3.33333H14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M5.33301 4.00004V2.66671C5.33301 2.31309 5.47348 1.97395 5.72353 1.7239C5.97358 1.47385 6.31272 1.33337 6.66634 1.33337H9.33301C9.68663 1.33337 10.0258 1.47385 10.2758 1.7239C10.5259 1.97395 10.6663 2.31309 10.6663 2.66671V4.00004M12.6663 4.00004V13.3334C12.6663 13.687 12.5259 14.0261 12.2758 14.2762C12.0258 14.5262 11.6866 14.6667 11.333 14.6667H4.66634C4.31272 14.6667 3.97358 14.5262 3.72353 14.2762C3.47348 14.0261 3.33301 13.687 3.33301 13.3334V4.00004H12.6663Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Delete
              </button>
            </div>
          );
        }

        return null;
      })()}

      {/* View Payments Modal */}
      <ViewOrderPaymentsModal
        order={viewingPaymentsOrder}
        onClose={() => {
          setViewPaymentsModalOpen(false);
          setViewingPaymentsOrder(null);
        }}
        onPaymentCreated={() => {
          if (onRefresh) onRefresh();
        }}
      />
    </div>
  );
};
