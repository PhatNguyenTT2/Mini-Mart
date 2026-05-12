import React from 'react';

export const InventoryMovementBatchListHeader = ({
  itemsPerPage,
  onItemsPerPageChange,
  searchQuery,
  onSearchChange,
  filterView,
  onFilterViewChange
}) => {
  const viewOptions = [
    { value: 'all', label: 'All Movements' },
    { value: 'in', label: 'Stock In' },
    { value: 'out', label: 'Stock Out' },
    { value: 'adjustment', label: 'Adjustments' },
    { value: 'transfer', label: 'Transfers' },
    { value: 'audit', label: 'Audits' }
  ];

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 bg-white border-b border-gray-200">
      {/* View Filter Buttons */}
      <div className="flex flex-wrap items-center gap-2">
        {viewOptions.map((option) => (
          <button
            key={option.value}
            onClick={() => onFilterViewChange(option.value)}
            className={`px-3 py-1.5 rounded-lg text-[12px] font-['Poppins',sans-serif] font-medium transition-colors ${filterView === option.value
                ? 'bg-emerald-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      {/* Search and Items Per Page */}
      <div className="flex items-center gap-3">
        {/* Search Input */}
        <div className="relative">
          <input
            type="text"
            placeholder="Search by movement number, batch, reason..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-64 h-9 pl-9 pr-3 text-[13px] font-['Poppins',sans-serif] border border-gray-300 rounded-lg focus:outline-none focus:border-emerald-500"
          />
          <svg
            className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        {/* Items Per Page Selector */}
        <div className="flex items-center gap-2">
          <span className="text-[12px] font-['Poppins',sans-serif] text-gray-600">
            Show:
          </span>
          <select
            value={itemsPerPage}
            onChange={(e) => onItemsPerPageChange(Number(e.target.value))}
            className="h-9 px-3 text-[13px] font-['Poppins',sans-serif] border border-gray-300 rounded-lg focus:outline-none focus:border-emerald-500"
          >
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
        </div>
      </div>
    </div>
  );
};
