import React, { useState, useRef, useEffect } from 'react';

export const CategoryList = ({ categories = [], onSort, sortField, sortOrder, onEdit, onDelete }) => {
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

  const truncateText = (text, maxLength = 100) => {
    if (!text) return '-';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const toggleDropdown = (categoryId, event) => {
    if (activeDropdown === categoryId) {
      setActiveDropdown(null);
    } else {
      const buttonRect = event.currentTarget.getBoundingClientRect();
      setDropdownPosition({
        top: buttonRect.bottom + 4,
        left: buttonRect.right - 160
      });
      setActiveDropdown(categoryId);
    }
  };

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
      <div className="overflow-x-auto rounded-lg">
        <div className="min-w-[800px]">
          {/* Table Header */}
          <div className="flex items-center h-[34px] bg-gray-50 border-b border-gray-200">
            {/* ID Column - Sortable */}
            <div
              className="w-[80px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('id')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                ID
                {getSortIcon('id')}
              </p>
            </div>

            {/* Name Column - Sortable */}
            <div
              className="flex-1 min-w-[160px] px-3 flex items-center cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('name')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Name
                {getSortIcon('name')}
              </p>
            </div>

            {/* Parent Column - Sortable */}
            <div
              className="w-[180px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('parentName')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Parent
                {getSortIcon('parentName')}
              </p>
            </div>

            {/* Image Column */}
            <div className="w-[80px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Image
              </p>
            </div>

            {/* Description Column */}
            <div className="flex-1 min-w-[180px] px-3 flex items-center">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Description
              </p>
            </div>

            {/* Product Count Column - Sortable */}
            <div
              className="w-[100px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('productCount')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Products
                {getSortIcon('productCount')}
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
            {categories.map((category, index) => (
              <div
                key={category.id}
                className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== categories.length - 1 ? 'border-b border-gray-100' : ''
                  }`}
              >

                {/* ID */}
                <div className="w-[80px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[12px] font-medium font-['Poppins',sans-serif] text-gray-600 leading-[20px] truncate">
                    {category.id}
                  </p>
                </div>

                {/* Name */}
                <div className="flex-1 min-w-[160px] px-3 flex items-center">
                  <div className="flex items-center gap-1.5">
                    {category.parentId && (
                      <span className="text-gray-400">└</span>
                    )}
                    <p className={`text-[13px] font-['Poppins',sans-serif] leading-[20px] truncate ${
                      category.parentId ? 'font-normal text-[#212529]' : 'font-semibold text-[#212529]'
                    }`}>
                      {category.name || '-'}
                    </p>
                    {category.isPerishable && (
                      <span className="bg-amber-100 text-amber-700 text-[9px] font-semibold font-['Poppins',sans-serif] px-1.5 py-0.5 rounded flex-shrink-0">
                        Perishable
                      </span>
                    )}
                  </div>
                </div>

                {/* Parent */}
                <div className="w-[180px] px-3 flex items-center flex-shrink-0">
                  {category.parentName ? (
                    <p className="text-[12px] font-normal font-['Poppins',sans-serif] text-blue-600 leading-[20px] truncate">
                      {category.parentName}
                    </p>
                  ) : (
                    <span className="bg-emerald-100 text-emerald-700 text-[10px] font-semibold font-['Poppins',sans-serif] px-2 py-0.5 rounded uppercase">
                      Root
                    </span>
                  )}
                </div>

                {/* Image */}
                <div className="w-[80px] px-3 flex items-center flex-shrink-0">
                  {category.image ? (
                    <img
                      src={category.image}
                      alt={category.name}
                      className="w-10 h-10 object-cover rounded border border-gray-200"
                      onError={(e) => {
                        e.target.onerror = null;
                        e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"%3E%3Crect width="48" height="48" fill="%23f3f4f6"/%3E%3Ctext x="24" y="24" text-anchor="middle" dy=".3em" fill="%236b7280" font-family="sans-serif" font-size="12"%3ENo Image%3C/text%3E%3C/svg%3E';
                      }}
                    />
                  ) : (
                    <div className="w-10 h-10 bg-gray-100 rounded border border-gray-200 flex items-center justify-center">
                      <span className="text-[9px] text-gray-400">No Image</span>
                    </div>
                  )}
                </div>

                {/* Description */}
                <div className="flex-1 min-w-[180px] px-3 flex items-center">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] line-clamp-2">
                    {truncateText(category.description, 150)}
                  </p>
                </div>

                {/* Product Count */}
                <div className="w-[100px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                    {category.productCount ?? 0}
                  </p>
                </div>

                {/* Actions */}
                <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                  <button
                    onClick={(e) => toggleDropdown(`action-${category.id}`, e)}
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
          {categories.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No categories found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menu — Actions only */}
      {activeDropdown && (() => {
        const category = categories.find(c =>
          `action-${c.id}` === activeDropdown
        );
        if (!category) return null;

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
                onEdit && onEdit(category);
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors flex items-center gap-2"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M11.333 2.00004C11.5081 1.82494 11.716 1.68605 11.9447 1.59129C12.1735 1.49653 12.4187 1.44775 12.6663 1.44775C12.914 1.44775 13.1592 1.49653 13.3879 1.59129C13.6167 1.68605 13.8246 1.82494 13.9997 2.00004C14.1748 2.17513 14.3137 2.383 14.4084 2.61178C14.5032 2.84055 14.552 3.08575 14.552 3.33337C14.552 3.58099 14.5032 3.82619 14.4084 4.05497C14.3137 4.28374 14.1748 4.49161 13.9997 4.66671L5.33301 13.3334L1.33301 14.6667L2.66634 10.6667L11.333 2.00004Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Edit
            </button>

            <div className="border-t border-gray-200 my-1"></div>

            <button
              onClick={() => {
                onDelete && onDelete(category);
                setActiveDropdown(null);
              }}
              disabled={category.productCount > 0}
              className={`w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] transition-colors flex items-center gap-2 ${category.productCount > 0
                ? 'text-gray-400 cursor-not-allowed opacity-50'
                : 'text-gray-700 hover:bg-red-50 hover:text-red-600'
                }`}
              title={
                category.productCount > 0
                  ? 'Category must have no products before deletion'
                  : 'Delete category'
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
      })()}
    </div>
  );
};
