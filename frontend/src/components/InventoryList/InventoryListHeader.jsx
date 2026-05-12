import React, { useState, useRef, useEffect } from 'react';

export const InventoryListHeader = ({
  itemsPerPage,
  onItemsPerPageChange,
  searchQuery,
  onSearchChange,
  filterView,
  onFilterViewChange,
  onBulkTransfer
}) => {
  const [showFiltersDropdown, setShowFiltersDropdown] = useState(false);
  const filtersDropdownRef = useRef(null);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (filtersDropdownRef.current && !filtersDropdownRef.current.contains(event.target)) {
        setShowFiltersDropdown(false);
      }
    };

    if (showFiltersDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showFiltersDropdown]);

  const statusOptions = [
    { value: 'all', label: 'All Items' },
    { value: 'low-stock', label: 'Low Stock' },
    { value: 'out-of-stock', label: 'Out of Stock' },
    { value: 'needs-reorder', label: 'Needs Reorder' }
  ];

  const hasActiveFilters = filterView !== 'all';

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm">
      <div className="flex items-center justify-between gap-3">
        {/* Title */}
        <div className="flex items-center">
          <h2 className="text-[13px] font-normal font-['Poppins',sans-serif] text-black leading-[20px] whitespace-nowrap">
            All Inventories
          </h2>
        </div>

        {/* Controls Container */}
        <div className="flex items-center gap-2 flex-1 ml-4">
          {/* Items Per Page Dropdown */}
          <div className="relative w-[80px]">
            <select
              value={itemsPerPage}
              onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
              className="w-full h-[36px] bg-white border border-[#ced4da] rounded-lg px-3 py-2 text-[12px] font-['Poppins',sans-serif] text-[#212529] appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
              <svg width="10" height="10" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M3 4.5L6 7.5L9 4.5" stroke="#212529" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
          </div>

          {/* Filters Button */}
          <div className="relative" ref={filtersDropdownRef}>
            <button
              onClick={() => setShowFiltersDropdown(!showFiltersDropdown)}
              className={`h-[36px] px-4 border rounded-lg text-[12px] font-['Poppins',sans-serif] leading-[20px] flex items-center justify-center gap-1.5 transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 whitespace-nowrap ${hasActiveFilters
                ? 'bg-emerald-50 border-emerald-500 text-emerald-700'
                : 'bg-white border-[#ced4da] text-[#212529] hover:bg-gray-50'
                }`}
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M13 2H1L5.8 7.46V11.5L8.2 12.5V7.46L13 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span>Filters</span>
              {hasActiveFilters && (
                <span className="w-2 h-2 bg-emerald-600 rounded-full"></span>
              )}
            </button>

            {/* Filters Dropdown */}
            {showFiltersDropdown && (
              <div className="absolute left-0 mt-2 w-64 bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-50">
                <div className="px-4 py-2 border-b border-gray-200">
                  <h3 className="text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-900">
                    Filter Inventory
                  </h3>
                </div>

                {/* Status Filter */}
                <div className="px-4 py-3">
                  <label className="text-[11px] font-['Poppins',sans-serif] text-gray-600 mb-1.5 block">
                    Stock Status
                  </label>
                  <select
                    value={filterView}
                    onChange={(e) => {
                      onFilterViewChange(e.target.value);
                    }}
                    className="w-full h-[32px] bg-white border border-[#ced4da] rounded-lg px-2 py-1 text-[12px] font-['Poppins',sans-serif] text-[#212529] appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                  >
                    {statusOptions.map(option => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Clear Filters */}
                {hasActiveFilters && (
                  <div className="px-4 py-2 border-t border-gray-200">
                    <button
                      onClick={() => {
                        onFilterViewChange('all');
                        setShowFiltersDropdown(false);
                      }}
                      className="w-full h-[32px] text-[12px] font-['Poppins',sans-serif] text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors"
                    >
                      Clear All Filters
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Search Input */}
          <div className="flex-1 max-w-[300px]">
            <div className="flex h-[36px] gap-1">
              <input
                type="text"
                placeholder="Search by Product Name..."
                value={searchQuery}
                onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
                className="flex-1 bg-white border border-[#ced4da] rounded-lg px-3 py-2 text-[12px] font-['Poppins',sans-serif] text-gray-900 placeholder:text-[#6c757d] focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              />
              <button
                className="w-[40px] bg-white border border-[#ced4da] rounded-lg flex items-center justify-center hover:bg-gray-50 transition-colors flex-shrink-0"
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M6.5 11.5C9.26142 11.5 11.5 9.26142 11.5 6.5C11.5 3.73858 9.26142 1.5 6.5 1.5C3.73858 1.5 1.5 3.73858 1.5 6.5C1.5 9.26142 3.73858 11.5 6.5 11.5Z"
                    stroke="#6B7280"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M12.5 12.5L10.5 10.5"
                    stroke="#6B7280"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Direct Bulk Transfer Button */}
        {onBulkTransfer && (
          <button
            onClick={onBulkTransfer}
            className="h-[36px] px-4 bg-emerald-600 hover:bg-emerald-700 border border-emerald-600 rounded-lg text-white text-[12px] font-['Poppins',sans-serif] leading-[20px] flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 whitespace-nowrap"
          >
            Bulk Transfer Stock
          </button>
        )}
      </div>
    </div>
  );
};

export default InventoryListHeader;
