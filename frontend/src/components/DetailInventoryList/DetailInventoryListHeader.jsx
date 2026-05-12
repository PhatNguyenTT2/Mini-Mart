import React from 'react';

export const DetailInventoryListHeader = ({
  itemsPerPage,
  onItemsPerPageChange,
  searchQuery,
  onSearchChange,
  filterView,
  onFilterViewChange
}) => {
  return (
    <div className="bg-white rounded-lg shadow-sm">
      <div className="p-4">
        {/* Top Row - Title and Action Buttons */}
        <div className="mb-4">
          <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
            Batch Inventory Management
          </h2>
          <p className="text-[13px] text-gray-600 font-['Poppins',sans-serif] mt-1">
            Manage inventory by batch. Use actions menu for each batch to adjust stock, release stock, or view movement history.
          </p>
        </div>

        {/* Bottom Row - Search and Filters */}
        <div className="flex items-center justify-between gap-4">
          {/* Left side - Items per page and Search */}
          <div className="flex items-center gap-4 flex-1">
            {/* Items per page */}
            <div className="flex items-center gap-2">
              <label className="text-[13px] font-['Poppins',sans-serif] text-[#7e7e7e] whitespace-nowrap">
                Show
              </label>
              <select
                value={itemsPerPage}
                onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              <span className="text-[13px] font-['Poppins',sans-serif] text-[#7e7e7e] whitespace-nowrap">
                entries
              </span>
            </div>

            {/* Search */}
            <div className="flex-1 max-w-md">
              <div className="relative">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => onSearchChange && onSearchChange(e.target.value)}
                  placeholder="Search by batch code or product name..."
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
                <svg
                  className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none"
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M7.33333 12.6667C10.2789 12.6667 12.6667 10.2789 12.6667 7.33333C12.6667 4.38781 10.2789 2 7.33333 2C4.38781 2 2 4.38781 2 7.33333C2 10.2789 4.38781 12.6667 7.33333 12.6667Z"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M14 14L11.1 11.1"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
            </div>
          </div>

          {/* Right side - View Filters */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => onFilterViewChange('in-stock')}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-['Poppins',sans-serif] font-medium transition-colors ${filterView === 'in-stock'
                ? 'bg-emerald-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
              In Stock
            </button>
            <button
              onClick={() => onFilterViewChange('out-of-stock')}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-['Poppins',sans-serif] font-medium transition-colors ${filterView === 'out-of-stock'
                ? 'bg-red-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
              Out of Stock
            </button>
            <button
              onClick={() => onFilterViewChange('has-warehouse')}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-['Poppins',sans-serif] font-medium transition-colors ${filterView === 'has-warehouse'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
              In Warehouse
            </button>
            <button
              onClick={() => onFilterViewChange('has-shelf')}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-['Poppins',sans-serif] font-medium transition-colors ${filterView === 'has-shelf'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
              On Shelf
            </button>
            <button
              onClick={() => onFilterViewChange('expiring-soon')}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-['Poppins',sans-serif] font-medium transition-colors ${filterView === 'expiring-soon'
                ? 'bg-orange-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
              Expiring Soon
            </button>
            <button
              onClick={() => onFilterViewChange('expired')}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-['Poppins',sans-serif] font-medium transition-colors ${filterView === 'expired'
                ? 'bg-gray-700 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
            >
              Expired
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
