import React, { useState, useRef, useEffect } from 'react';

export const InventoryList = ({
  inventory = [],
  onSort,
  sortField,
  sortOrder,
  onViewDetail,
  onUpdateLocation,
  onViewMovementHistory
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
    // Low Stock: available <= reorder point AND available > 0
    if (item.quantityAvailable > 0 && item.quantityAvailable <= item.reorderPoint) {
      return (
        <span className="bg-yellow-100 text-yellow-700 px-2 py-1 rounded text-[9px] font-bold font-['Poppins',sans-serif] uppercase">
          Low Stock
        </span>
      );
    }
    // In Stock: available > reorder point
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
        <div className="min-w-[1200px]">
          {/* Table Header */}
          <div className="flex items-center h-[34px] bg-gray-50 border-b border-gray-200">
            {/* Product ID Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('productId')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Product ID
                {getSortIcon('productId')}
              </p>
            </div>

            {/* Product Name Column - Sortable */}
            <div
              className="flex-1 min-w-[200px] px-3 flex items-center cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('productName')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Product Name
                {getSortIcon('productName')}
              </p>
            </div>

            {/* On Hand Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('quantityOnHand')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                On Hand
                {getSortIcon('quantityOnHand')}
              </p>
            </div>

            {/* On Shelf Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('quantityOnShelf')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                On Shelf
                {getSortIcon('quantityOnShelf')}
              </p>
            </div>

            {/* Reserved Column */}
            <div className="w-[120px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Reserved
              </p>
            </div>

            {/* Available Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('quantityAvailable')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Available
                {getSortIcon('quantityAvailable')}
              </p>
            </div>

            {/* Reorder Point Column */}
            <div className="w-[120px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Reorder At
              </p>
            </div>

            {/* Status Column */}
            <div className="w-[120px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Status
              </p>
            </div>

            {/* Actions Column */}
            <div className="w-[120px] px-3 flex items-center justify-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Actions
              </p>
            </div>
          </div>

          {/* Table Body */}
          <div className="flex flex-col">
            {inventory.map((item, index) => {
              return (
                <div
                  key={item.id || item._id}
                  className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== inventory.length - 1 ? 'border-b border-gray-100' : ''
                    }`}
                >
                  {/* Product ID */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-emerald-600 leading-[20px]">
                      #{item.productId}
                    </p>
                  </div>

                  {/* Product Name */}
                  <div className="flex-1 min-w-[200px] px-3 flex items-center">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                      {item.product?.name || 'N/A'}
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
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-gray-600 leading-[20px]">
                      {item.quantityReserved}
                    </p>
                  </div>

                  {/* Available */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className={`text-[13px] font-semibold font-['Poppins',sans-serif] leading-[20px] ${item.quantityAvailable === 0 ? 'text-red-600' :
                      item.quantityAvailable <= item.reorderPoint ? 'text-yellow-600' :
                        'text-green-600'
                      }`}>
                      {item.quantityAvailable}
                    </p>
                  </div>

                  {/* Reorder Point */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-gray-600 leading-[20px]">
                      {item.reorderPoint}
                    </p>
                  </div>

                  {/* Status Badge */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    {getStockStatusBadge(item)}
                  </div>

                  {/* Actions */}
                  <div className="w-[120px] px-3 flex items-center justify-center flex-shrink-0">
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
          {inventory.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No inventory items found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menus */}
      {activeDropdown && (() => {
        const itemId = activeDropdown.replace('action-', '');
        const item = inventory.find(i => String(i.id || i._id) === String(itemId));

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
                if (onViewDetail) {
                  const productId = item.productId || item.product?.id || item.product?._id;
                  onViewDetail(productId);
                }
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-emerald-50 hover:text-emerald-600 transition-colors flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M1 8C1 8 3.54545 3 8 3C12.4545 3 15 8 15 8C15 8 12.4545 13 8 13C3.54545 13 1 8 1 8Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <circle cx="8" cy="8" r="2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              View Detail
            </button>

            <button
              onClick={() => {
                if (onViewMovementHistory) {
                  onViewMovementHistory(item);
                }
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-emerald-50 hover:text-emerald-600 transition-colors flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 4V8L10.5 10.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M14 8C14 11.3137 11.3137 14 8 14C4.68629 14 2 11.3137 2 8C2 4.68629 4.68629 2 8 2C9.8 2 11.4 2.8 12.5 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Movement History
            </button>
          </div>
        );
      })()}
    </div>
  );
};