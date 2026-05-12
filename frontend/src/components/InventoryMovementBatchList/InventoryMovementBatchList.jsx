import React, { useState, useRef, useEffect } from 'react';

export const InventoryMovementBatchList = ({
  movements = [],
  onSort,
  sortField,
  sortOrder,
  onEdit,
  onDelete,
  onViewDetails
}) => {
  const [activeDropdown, setActiveDropdown] = useState(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const dropdownRef = useRef(null);

  // Handle sort click
  const handleSortClick = (field) => {
    if (onSort) {
      onSort(field);
    }
  };

  // Get sort icon with color
  const getSortIcon = (field) => {
    if (sortField !== field) {
      return (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="ml-1">
          <path d="M6 3V9M6 3L4 5M6 3L8 5" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    }

    if (sortOrder === 'asc') {
      return (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="ml-1">
          <path d="M6 9V3M6 3L4 5M6 3L8 5" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    } else {
      return (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="ml-1">
          <path d="M6 3V9M6 9L4 7M6 9L8 7" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    }
  };

  // Toggle dropdown
  const toggleDropdown = (dropdownId, event) => {
    if (activeDropdown === dropdownId) {
      setActiveDropdown(null);
    } else {
      const buttonRect = event.currentTarget.getBoundingClientRect();
      const leftPosition = buttonRect.right - 160;

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

  // Get movement type badge
  const getMovementTypeBadge = (type) => {
    const badges = {
      'in': { bg: 'bg-green-100', text: 'text-green-700', label: 'Stock In' },
      'out': { bg: 'bg-red-100', text: 'text-red-700', label: 'Stock Out' },
      'adjustment': { bg: 'bg-orange-100', text: 'text-orange-700', label: 'Adjustment' },
      'transfer': { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Transfer' },
      'audit': { bg: 'bg-purple-100', text: 'text-purple-700', label: 'Audit' }
    };

    const badge = badges[type] || badges['adjustment'];

    return (
      <span className={`${badge.bg} ${badge.text} px-2 py-1 rounded text-[9px] font-bold font-['Poppins',sans-serif] uppercase`}>
        {badge.label}
      </span>
    );
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  // Format datetime
  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Format quantity with +/- sign
  const formatQuantity = (movement) => {
    const quantity = movement.quantity;
    const type = movement.movementType;

    if (type === 'in') {
      return `+${Math.abs(quantity)}`;
    } else if (type === 'out') {
      return `-${Math.abs(quantity)}`;
    } else if (type === 'adjustment' || type === 'audit') {
      return quantity > 0 ? `+${quantity}` : `${quantity}`;
    } else if (type === 'transfer') {
      return quantity > 0 ? `+${quantity} (to shelf)` : `${quantity} (to warehouse)`;
    }
    return quantity;
  };

  return (
    <div className="bg-white rounded-lg shadow-sm">
      {/* Scrollable Container */}
      <div className="overflow-x-auto rounded-lg">
        <div className="min-w-[1600px]">
          {/* Table Header */}
          <div className="flex items-center h-[34px] bg-gray-50 border-b border-gray-200">
            {/* Movement Number Column - Sortable */}
            <div
              className="w-[140px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('movementNumber')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Movement #
                {getSortIcon('movementNumber')}
              </p>
            </div>

            {/* Date Column - Sortable */}
            <div
              className="w-[150px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('date')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Date
                {getSortIcon('date')}
              </p>
            </div>

            {/* Type Column */}
            <div className="w-[120px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Type
              </p>
            </div>

            {/* Batch Code Column - Sortable */}
            <div
              className="w-[130px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('batchCode')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Batch Code
                {getSortIcon('batchCode')}
              </p>
            </div>

            {/* Product Name Column - Sortable */}
            <div
              className="flex-1 min-w-[180px] px-3 flex items-center cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('productName')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Product Name
                {getSortIcon('productName')}
              </p>
            </div>

            {/* Quantity Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('quantity')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Quantity
                {getSortIcon('quantity')}
              </p>
            </div>

            {/* Reason Column */}
            <div className="w-[200px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Reason
              </p>
            </div>

            {/* Performed By Column */}
            <div className="w-[150px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Performed By
              </p>
            </div>

            {/* Purchase Order Column */}
            <div className="w-[140px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                PO Reference
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
            {movements.map((item, index) => (
              <div
                key={item._id || item.id}
                className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== movements.length - 1 ? 'border-b border-gray-100' : ''
                  }`}
              >
                {/* Movement Number */}
                <div className="w-[140px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-emerald-600 leading-[20px]">
                    {item.movementNumber || 'N/A'}
                  </p>
                </div>

                {/* Date */}
                <div className="w-[150px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                    {formatDateTime(item.date)}
                  </p>
                </div>

                {/* Type Badge */}
                <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                  {getMovementTypeBadge(item.movementType)}
                </div>

                {/* Batch Code */}
                <div className="w-[130px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-blue-600 leading-[20px]">
                    {item.batchId?.batchCode || 'N/A'}
                  </p>
                </div>

                {/* Product Name */}
                <div className="flex-1 min-w-[180px] px-3 flex items-center">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                    {item.batchId?.product?.name || 'N/A'}
                  </p>
                </div>

                {/* Quantity */}
                <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                  <p className={`text-[13px] font-semibold font-['Poppins',sans-serif] leading-[20px] ${item.movementType === 'in' || (item.movementType === 'adjustment' && item.quantity > 0)
                    ? 'text-green-600'
                    : item.movementType === 'out' || (item.movementType === 'adjustment' && item.quantity < 0)
                      ? 'text-red-600'
                      : 'text-blue-600'
                    }`}>
                    {formatQuantity(item)}
                  </p>
                </div>

                {/* Reason */}
                <div className="w-[200px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-gray-600 leading-[20px] truncate" title={item.reason}>
                    {item.reason || 'N/A'}
                  </p>
                </div>

                {/* Performed By */}
                <div className="w-[150px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                    {(() => {
                      // Debug: Log the performedBy data
                      if (index === 0) console.log('Movement item:', item, 'PerformedBy:', item.performedBy);
                      return item.performedBy
                        ? item.performedBy.fullName || item.performedBy.employeeCode || 'N/A'
                        : 'System';
                    })()}
                  </p>
                </div>

                {/* Purchase Order Reference */}
                <div className="w-[140px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-gray-600 leading-[20px] truncate">
                    {item.purchaseOrderId?.purchaseOrderCode || 'N/A'}
                  </p>
                </div>

                {/* Actions */}
                <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                  <button
                    onClick={(e) => toggleDropdown(`action-${item._id || item.id}`, e)}
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
          {movements.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No inventory movements found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menus */}
      {activeDropdown && (() => {
        const item = movements.find(i => activeDropdown === `action-${i._id || i.id}`);
        if (!item) return null;

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
                if (onViewDetails) {
                  onViewDetails(item);
                }
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M1 8C1 8 3.5 3 8 3C12.5 3 15 8 15 8C15 8 12.5 13 8 13C3.5 13 1 8 1 8Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              View Details
            </button>

            <div className="border-t border-gray-200 my-1"></div>

            <button
              onClick={() => {
                if (onEdit) {
                  onEdit(item);
                }
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-emerald-50 hover:text-emerald-600 transition-colors flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M11.333 2C11.5081 1.82489 11.716 1.686 11.9447 1.59124C12.1735 1.49647 12.4187 1.4477 12.6663 1.4477C12.914 1.4477 13.1592 1.49647 13.3879 1.59124C13.6167 1.686 13.8246 1.82489 13.9997 2C14.1748 2.17511 14.3137 2.38298 14.4084 2.61176C14.5032 2.84053 14.552 3.08574 14.552 3.33336C14.552 3.58098 14.5032 3.82619 14.4084 4.05496C14.3137 4.28374 14.1748 4.49161 13.9997 4.66672L5.33301 13.3334L1.33301 14.6667L2.66634 10.6667L11.333 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Edit Notes
            </button>

            <button
              onClick={() => {
                if (onDelete) {
                  if (window.confirm('Are you sure you want to delete this movement? This will reverse its effect on inventory.')) {
                    onDelete(item);
                  }
                }
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-red-50 hover:text-red-600 transition-colors flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M2 4H14M12.6667 4V13.3333C12.6667 14 12 14.6667 11.3333 14.6667H4.66667C4 14.6667 3.33333 14 3.33333 13.3333V4M5.33333 4V2.66667C5.33333 2 6 1.33333 6.66667 1.33333H9.33333C10 1.33333 10.6667 2 10.6667 2.66667V4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Delete Movement
            </button>
          </div>
        );
      })()}
    </div>
  );
};
