import React, { useState, useRef, useEffect } from 'react';

export const PaymentList = ({ payments = [], onSort, sortField, sortOrder, onEdit, onDelete, onUpdateStatus, onRefund }) => {
  const [activeDropdown, setActiveDropdown] = useState(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const dropdownRef = useRef(null);

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

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  const formatAmount = (amount) => {
    if (amount == null) return '-';
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
    }).format(amount);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-[#10b981]';
      case 'pending':
        return 'bg-[#f59e0b]';
      case 'cancelled':
        return 'bg-[#ef4444]';
      case 'refunded':
        return 'bg-[#8b5cf6]';
      default:
        return 'bg-[#6b7280]';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'pending':
        return 'Pending';
      case 'cancelled':
        return 'Cancelled';
      case 'refunded':
        return 'Refunded';
      default:
        return status || '-';
    }
  };

  const getPaymentMethodLabel = (method) => {
    switch (method) {
      case 'bank_transfer':
        return 'Bank Transfer';
      case 'cash':
        return 'Cash';
      default:
        return method || '-';
    }
  };

  const getReferenceTypeLabel = (type) => {
    switch (type) {
      case 'Order':
        return 'Order';
      case 'PurchaseOrder':
        return 'Purchase Order';
      default:
        return type || '-';
    }
  };

  const getReferenceTypeColor = (type) => {
    switch (type) {
      case 'Order':
        return 'text-blue-600 bg-blue-50';
      case 'PurchaseOrder':
        return 'text-purple-600 bg-purple-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const truncateText = (text, maxLength = 50) => {
    if (!text) return '-';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // Toggle dropdown
  const toggleDropdown = (paymentId, event) => {
    if (activeDropdown === paymentId) {
      setActiveDropdown(null);
    } else {
      const buttonRect = event.currentTarget.getBoundingClientRect();

      // Determine position based on dropdown type
      let leftPosition;
      if (paymentId.startsWith('status-')) {
        // For Status: show dropdown to the right of button
        leftPosition = buttonRect.left;
      } else {
        // For Actions: show dropdown aligned to the right
        leftPosition = buttonRect.right - 160; // 160px is dropdown width
      }

      setDropdownPosition({
        top: buttonRect.bottom + 4,
        left: leftPosition
      });
      setActiveDropdown(paymentId);
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
        <div className="min-w-[1200px]">
          {/* Table Header */}
          <div className="flex items-center h-[34px] bg-gray-50 border-b border-gray-200">
            {/* Payment Number Column - Sortable */}
            <div
              className="w-[140px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('paymentNumber')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Payment ID
                {getSortIcon('paymentNumber')}
              </p>
            </div>

            {/* Amount Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('amount')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Amount
                {getSortIcon('amount')}
              </p>
            </div>

            {/* Payment Method Column - Sortable */}
            <div
              className="w-[130px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('paymentMethod')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Method
                {getSortIcon('paymentMethod')}
              </p>
            </div>

            {/* Payment Date Column - Sortable */}
            <div
              className="w-[110px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('paymentDate')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Date
                {getSortIcon('paymentDate')}
              </p>
            </div>

            {/* Reference Type Column - Sortable */}
            <div
              className="w-[130px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('referenceType')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Reference
                {getSortIcon('referenceType')}
              </p>
            </div>

            {/* Notes Column */}
            <div className="flex-1 min-w-[150px] px-3 flex items-center">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Notes
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

            {/* Actions Column */}
            <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Actions
              </p>
            </div>
          </div>

          {/* Table Body */}
          <div className="flex flex-col">
            {payments.map((payment, index) => (
              <div
                key={payment.id}
                className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== payments.length - 1 ? 'border-b border-gray-100' : ''
                  }`}
              >
                {/* Payment Number */}
                <div className="w-[140px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[12px] font-medium font-['Poppins',sans-serif] text-gray-600 leading-[20px] truncate">
                    {payment.paymentNumber || '-'}
                  </p>
                </div>

                {/* Amount */}
                <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                    {formatAmount(payment.amount)}
                  </p>
                </div>

                {/* Payment Method */}
                <div className="w-[130px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                    {getPaymentMethodLabel(payment.paymentMethod)}
                  </p>
                </div>

                {/* Payment Date */}
                <div className="w-[110px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                    {formatDate(payment.paymentDate)}
                  </p>
                </div>

                {/* Reference Type */}
                <div className="w-[130px] px-3 flex items-center flex-shrink-0">
                  <span className={`px-2 py-1 rounded text-[10px] font-medium font-['Poppins',sans-serif] ${getReferenceTypeColor(payment.referenceType)}`}>
                    {getReferenceTypeLabel(payment.referenceType)}
                  </span>
                </div>

                {/* Notes */}
                <div className="flex-1 min-w-[150px] px-3 flex items-center">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                    {truncateText(payment.notes)}
                  </p>
                </div>

                {/* Status - Dropdown only for pending, static badge for final statuses */}
                <div className="w-[110px] px-3 flex items-center flex-shrink-0">
                  {payment.status === 'pending' ? (
                    <button
                      onClick={(e) => toggleDropdown(`status-${payment.id}`, e)}
                      className={`${getStatusColor(payment.status)} px-2 py-1 rounded inline-flex items-center gap-1 cursor-pointer hover:opacity-90 transition-opacity`}
                    >
                      <span className="text-[9px] font-bold font-['Poppins',sans-serif] text-white leading-[10px] uppercase">
                        {getStatusLabel(payment.status)}
                      </span>
                      <svg width="8" height="5" viewBox="0 0 8 5" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M1 1L4 4L7 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  ) : (
                    <div className={`${getStatusColor(payment.status)} px-2 py-1 rounded inline-flex items-center`}>
                      <span className="text-[9px] font-bold font-['Poppins',sans-serif] text-white leading-[10px] uppercase">
                        {getStatusLabel(payment.status)}
                      </span>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                  <button
                    onClick={(e) => toggleDropdown(`action-${payment.id}`, e)}
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
          {payments.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No payments found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menu */}
      {activeDropdown && (() => {
        const payment = payments.find(p =>
          `action-${p.id}` === activeDropdown || `status-${p.id}` === activeDropdown
        );
        if (!payment) return null;

        const isStatusDropdown = activeDropdown === `status-${payment.id}`;
        const isActionDropdown = activeDropdown === `action-${payment.id}`;

        // Render Status Dropdown (only shown for pending payments)
        if (isStatusDropdown) {
          const statusOptions = [
            { value: 'pending', label: 'Pending', color: 'bg-[#f59e0b]' },
            { value: 'completed', label: 'Completed', color: 'bg-[#10b981]' },
            { value: 'cancelled', label: 'Cancelled', color: 'bg-[#ef4444]' }
          ];

          return (
            <div
              ref={dropdownRef}
              className="fixed min-w-[160px] bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-[9999]"
              style={{
                top: `${dropdownPosition.top}px`,
                left: `${dropdownPosition.left}px`
              }}
            >
              {statusOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => {
                    if (onUpdateStatus && payment.status !== option.value) {
                      if (option.value === 'completed') {
                        const confirmed = window.confirm(
                          'Complete this payment?\n\nThis will trigger order fulfillment:\n• Pickup orders → Status changes to "Delivered" + Stock deducted\n• Delivery orders → Status changes to "Shipping" + Stock reserved\n\nThis action cannot be undone.'
                        );
                        if (!confirmed) {
                          setActiveDropdown(null);
                          return;
                        }
                      }
                      onUpdateStatus(payment, option.value);
                    }
                    setActiveDropdown(null);
                  }}
                  className={`w-full px-3 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2 ${payment.status === option.value ? 'cursor-default' : ''}`}
                  disabled={payment.status === option.value}
                >
                  <span className={`${option.color} w-2 h-2 rounded-full`}></span>
                  <span className={`text-[12px] font-['Poppins',sans-serif] ${payment.status === option.value ? 'text-emerald-600 font-medium' : 'text-[#212529]'}`}>
                    {option.label}
                  </span>
                  {payment.status === option.value && (
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
          // Check if refund is available (any completed payment can be refunded)
          const canRefund = payment.status === 'completed';

          return (
            <div
              ref={dropdownRef}
              className="fixed w-44 bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-[9999]"
              style={{
                top: `${dropdownPosition.top}px`,
                left: `${dropdownPosition.left}px`
              }}
            >
              <button
                onClick={() => {
                  onEdit && onEdit(payment);
                  setActiveDropdown(null);
                }}
                className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors flex items-center gap-2"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M11.333 2.00004C11.5081 1.82494 11.716 1.68605 11.9447 1.59129C12.1735 1.49653 12.4187 1.44775 12.6663 1.44775C12.914 1.44775 13.1592 1.49653 13.3879 1.59129C13.6167 1.68605 13.8246 1.82494 13.9997 2.00004C14.1748 2.17513 14.3137 2.383 14.4084 2.61178C14.5032 2.84055 14.552 3.08575 14.552 3.33337C14.552 3.58099 14.5032 3.82619 14.4084 4.05497C14.3137 4.28374 14.1748 4.49161 13.9997 4.66671L5.33301 13.3334L1.33301 14.6667L2.66634 10.6667L11.333 2.00004Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Edit
              </button>

              {/* Refund button - only for PurchaseOrder completed payments */}
              {canRefund && (
                <>
                  <div className="border-t border-gray-200 my-1"></div>
                  <button
                    onClick={() => {
                      onRefund && onRefund(payment);
                      setActiveDropdown(null);
                    }}
                    className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-purple-50 hover:text-purple-600 transition-colors flex items-center gap-2"
                  >
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M1.33301 6.66667H10.6663C12.1391 6.66667 13.333 7.86057 13.333 9.33333V10.6667C13.333 12.1394 12.1391 13.3333 10.6663 13.3333H5.33301" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      <path d="M4.66699 3.33333L1.33366 6.66667L4.66699 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    Refund Payment
                  </button>
                </>
              )}

              <div className="border-t border-gray-200 my-1"></div>

              <button
                onClick={() => {
                  onDelete && onDelete(payment);
                  setActiveDropdown(null);
                }}
                disabled={!['pending', 'cancelled'].includes(payment.status)}
                className={`w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] transition-colors flex items-center gap-2 ${!['pending', 'cancelled'].includes(payment.status)
                  ? 'text-gray-400 cursor-not-allowed opacity-50'
                  : 'text-gray-700 hover:bg-red-50 hover:text-red-600'
                  }`}
                title={
                  !['pending', 'cancelled'].includes(payment.status)
                    ? 'Only pending or cancelled payments can be deleted'
                    : 'Delete payment'
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
    </div>
  );
};
