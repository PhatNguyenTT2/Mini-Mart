import React, { useState, useRef, useEffect } from 'react';

export const DetailInventoryList = ({
  detailInventory = [],
  onSort,
  sortField,
  sortOrder,
  onViewHistory,
  onStockOut,
  onAdjust,
  onUpdateLocation
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

  // Toggle dropdown with auto-position adjustment
  const toggleDropdown = (dropdownId, event) => {
    if (activeDropdown === dropdownId) {
      setActiveDropdown(null);
    } else {
      const buttonRect = event.currentTarget.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      const viewportWidth = window.innerWidth;

      // Dropdown dimensions
      const dropdownHeight = 130; // Height for 3 menu items
      const dropdownWidth = 192; // w-48 = 12rem = 192px

      // Check if dropdown fits below button
      const spaceBelow = viewportHeight - buttonRect.bottom;
      const spaceAbove = buttonRect.top;
      const fitsBelow = spaceBelow >= dropdownHeight;

      // Check if dropdown fits on the right side
      const spaceRight = viewportWidth - buttonRect.right;
      const fitsRight = spaceRight >= dropdownWidth;

      // Calculate vertical position
      let topPosition;
      if (fitsBelow) {
        topPosition = buttonRect.bottom + 8;
      } else if (spaceAbove >= dropdownHeight) {
        topPosition = buttonRect.top - dropdownHeight - 8;
      } else {
        // Not enough space either way, position with max visibility
        topPosition = Math.max(10, Math.min(buttonRect.bottom + 8, viewportHeight - dropdownHeight - 10));
      }

      // Calculate horizontal position
      let leftPosition;
      if (fitsRight) {
        leftPosition = buttonRect.right - dropdownWidth;
      } else {
        // Align to right edge with padding
        leftPosition = Math.max(10, viewportWidth - dropdownWidth - 10);
      }

      setDropdownPosition({
        top: topPosition,
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

  // Get stock status badge
  const getStockStatusBadge = (item) => {
    // Out of Stock: available = 0
    if (item.quantityAvailable === 0) {
      return (
        <span className="bg-red-100 text-red-700 px-2 py-1 rounded text-[9px] font-bold font-['Poppins',sans-serif] uppercase">
          Out of Stock
        </span>
      );
    }
    // In Stock
    return (
      <span className="bg-green-100 text-green-700 px-2 py-1 rounded text-[9px] font-bold font-['Poppins',sans-serif] uppercase">
        In Stock
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

  return (
    <div className="bg-white rounded-lg shadow-sm">
      {/* Scrollable Container */}
      <div className="overflow-x-auto rounded-lg">
        <div className="min-w-[1100px]">
          {/* Table Header */}
          <div className="flex items-center h-[34px] bg-gray-50 border-b border-gray-200">
            {/* Batch Code Column - Sortable */}
            <div
              className="w-[140px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('batchCode')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Batch Code
                {getSortIcon('batchCode')}
              </p>
            </div>

            {/* Expiry Date Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('expiryDate')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Expiry Date
                {getSortIcon('expiryDate')}
              </p>
            </div>

            {/* On Hand Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('quantityOnHand')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                On Hand
                {getSortIcon('quantityOnHand')}
              </p>
            </div>

            {/* On Shelf Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('quantityOnShelf')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                On Shelf
                {getSortIcon('quantityOnShelf')}
              </p>
            </div>

            {/* Reserved Column */}
            <div className="w-[110px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Reserved
              </p>
            </div>

            {/* Available Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('quantityAvailable')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Available
                {getSortIcon('quantityAvailable')}
              </p>
            </div>

            {/* Batch Quantity Column */}
            <div className="w-[110px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Batch Qty
              </p>
            </div>

            {/* Location Column */}
            <div className="flex-1 min-w-[100px] px-3 flex items-center">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Location
              </p>
            </div>

            {/* Status Column */}
            <div className="w-[120px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Status
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
            {detailInventory.map((item, index) => {
              const expiryDate = item.batchId?.expiryDate ? new Date(item.batchId.expiryDate) : null;
              const isExpiringSoon = expiryDate && (expiryDate - new Date()) < (30 * 24 * 60 * 60 * 1000);

              return (
                <div
                  key={item.id || item._id}
                  className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== detailInventory.length - 1 ? 'border-b border-gray-100' : ''
                    }`}
                >
                  {/* Batch Code */}
                  <div className="w-[140px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-emerald-600 leading-[20px]">
                      {item.batchId?.batchCode || 'N/A'}
                    </p>
                  </div>

                  {/* Expiry Date */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className={`text-[13px] font-normal font-['Poppins',sans-serif] leading-[20px] ${isExpiringSoon ? 'text-orange-600 font-semibold' : 'text-[#212529]'
                      }`}>
                      {formatDate(item.batchId?.expiryDate)}
                    </p>
                  </div>

                  {/* On Hand */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                      {item.quantityOnHand}
                    </p>
                  </div>

                  {/* On Shelf */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                      {item.quantityOnShelf}
                    </p>
                  </div>

                  {/* Reserved */}
                  <div className="w-[110px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-gray-600 leading-[20px]">
                      {item.quantityReserved}
                    </p>
                  </div>

                  {/* Available */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className={`text-[13px] font-semibold font-['Poppins',sans-serif] leading-[20px] ${item.quantityAvailable === 0 ? 'text-red-600' : 'text-green-600'
                      }`}>
                      {item.quantityAvailable}
                    </p>
                  </div>

                  {/* Batch Quantity */}
                  <div className="w-[110px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-gray-600 leading-[20px]">
                      {item.batchId?.quantity || 0}
                    </p>
                  </div>

                  {/* Location */}
                  <div className="flex-1 min-w-[100px] px-3 flex items-center">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                      {item.location?.name || item.location || 'N/A'}
                    </p>
                  </div>

                  {/* Status Badge */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    {getStockStatusBadge(item)}
                  </div>

                  {/* Actions */}
                  <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                    <button
                      onClick={(e) => {
                        const itemId = item.id || item._id;
                        toggleDropdown(`action-${itemId}`, e);
                      }}
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
              );
            })}
          </div>

          {/* Empty State */}
          {detailInventory.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No batch inventory items found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menus */}
      {activeDropdown && (() => {
        const itemId = activeDropdown.replace('action-', '');
        const item = detailInventory.find(i => (i.id || i._id) === itemId);

        if (!item) return null;

        return (
          <div
            ref={dropdownRef}
            className="fixed w-48 bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-[9999]"
            style={{
              top: `${dropdownPosition.top}px`,
              left: `${dropdownPosition.left}px`
            }}
          >
            {/* Movement History */}
            <button
              onClick={() => {
                if (onViewHistory) {
                  onViewHistory(item);
                }
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-purple-50 hover:text-purple-600 transition-colors flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 4V8L10.5 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M14 8C14 11.3137 11.3137 14 8 14C4.68629 14 2 11.3137 2 8C2 4.68629 4.68629 2 8 2C9.8 2 11.4 2.8 12.5 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Movement History
            </button>

            <div className="border-t border-gray-200 my-1"></div>

            {/* Adjust Stock */}
            <button
              onClick={() => {
                if (onAdjust) {
                  onAdjust(item);
                }
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-orange-50 hover:text-orange-600 transition-colors flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M11.333 2C11.5081 1.82489 11.716 1.686 11.9447 1.59124C12.1735 1.49647 12.4187 1.4477 12.6663 1.4477C12.914 1.4477 13.1592 1.49647 13.3879 1.59124C13.6167 1.686 13.8246 1.82489 13.9997 2C14.1748 2.17511 14.3137 2.38298 14.4084 2.61176C14.5032 2.84053 14.552 3.08574 14.552 3.33336C14.552 3.58098 14.5032 3.82619 14.4084 4.05496C14.3137 4.28374 14.1748 4.49161 13.9997 4.66672L5.33301 13.3334L1.33301 14.6667L2.66634 10.6667L11.333 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Adjust Stock
            </button>
            <div className="border-t border-gray-200 my-1"></div>

            {/* Update Location */}
            <button
              onClick={() => {
                if (onUpdateLocation) {
                  onUpdateLocation(item);
                }
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 14C11.3137 14 14 11.3137 14 8C14 4.68629 11.3137 2 8 2C4.68629 2 2 4.68629 2 8C2 11.3137 4.68629 14 8 14Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M8 5V8L10 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Update Location
            </button>
          </div>
        );
      })()}
    </div>
  );
};
