import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// Helper function to format VND currency
const formatVND = (amount) => {
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND'
  }).format(amount);
};

export const ProductList = ({ products = [], onSort, sortField, sortOrder, onEdit, onDelete, onToggleActive }) => {
  const navigate = useNavigate();
  const [activeDropdown, setActiveDropdown] = useState(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const dropdownRef = useRef(null);
  const buttonRefs = useRef({});

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

  const truncateText = (text, maxLength = 50) => {
    if (!text) return '-';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // Toggle dropdown
  const toggleDropdown = (productId, event) => {
    if (activeDropdown === productId) {
      setActiveDropdown(null);
    } else {
      const buttonRect = event.currentTarget.getBoundingClientRect();

      // Determine position based on dropdown type
      let leftPosition;
      if (productId.startsWith('active-')) {
        // For Active Status: show dropdown to the right of button
        leftPosition = buttonRect.left;
      } else {
        // For Actions: show dropdown aligned to the right
        leftPosition = buttonRect.right - 160; // 160px is dropdown width
      }

      setDropdownPosition({
        top: buttonRect.bottom + 4,
        left: leftPosition
      });
      setActiveDropdown(productId);
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

            {/* Image Column */}
            <div className="w-[80px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Image
              </p>
            </div>

            {/* Name Column - Sortable */}
            <div
              className="flex-1 min-w-[140px] px-3 flex items-center cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('name')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Name
                {getSortIcon('name')}
              </p>
            </div>

            {/* Category Column - Sortable */}
            <div
              className="w-[240px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('category')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Category
                {getSortIcon('category')}
              </p>
            </div>

            {/* Unit Price Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('unitPrice')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Unit Price
                {getSortIcon('unitPrice')}
              </p>
            </div>

            {/* Vendor Column */}
            <div className="w-[130px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Vendor
              </p>
            </div>



            {/* Active Status Column - Sortable */}
            <div
              className="w-[100px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('isActive')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                Active
                {getSortIcon('isActive')}
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
            {products.map((product, index) => (
              <div
                key={product.id}
                className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== products.length - 1 ? 'border-b border-gray-100' : ''
                  }`}
              >
                {/* ID */}
                <div className="w-[80px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[12px] font-medium font-['Poppins',sans-serif] text-gray-600 leading-[20px] truncate">
                    {product.id}
                  </p>
                </div>

                {/* Image */}
                <div className="w-[80px] px-3 flex items-center flex-shrink-0">
                  {product.image ? (
                    <img
                      src={product.image}
                      alt={product.name}
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

                {/* Name */}
                <div className="flex-1 min-w-[140px] px-3 flex items-center">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate" title={product.name}>
                    {truncateText(product.name, 40)}
                  </p>
                </div>

                {/* Category */}
                <div className="w-[240px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                    {product.category?.name || product.categoryName || '-'}
                  </p>
                </div>

                {/* Unit Price */}
                <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-emerald-600 leading-[20px]">
                    {formatVND(product.unitPrice || 0)}
                  </p>
                </div>

                {/* Vendor */}
                <div className="w-[130px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                    {product.vendor || '-'}
                  </p>
                </div>



                {/* Active Status - Dropdown */}
                <div className="w-[100px] px-3 flex items-center flex-shrink-0">
                  <button
                    onClick={(e) => toggleDropdown(`active-${product.id}`, e)}
                    className={`${product.isActive !== false ? 'bg-[#10b981]' : 'bg-[#6b7280]'
                      } px-2 py-1 rounded inline-flex items-center gap-1 cursor-pointer hover:opacity-90 transition-opacity`}
                  >
                    <span className="text-[9px] font-bold font-['Poppins',sans-serif] text-white leading-[10px] uppercase">
                      {product.isActive !== false ? 'Active' : 'Inactive'}
                    </span>
                    <svg width="8" height="5" viewBox="0 0 8 5" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M1 1L4 4L7 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>
                </div>

                {/* Actions */}
                <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                  <button
                    onClick={(e) => toggleDropdown(`action-${product.id}`, e)}
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
          {products.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No products found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menu */}
      {activeDropdown && (() => {
        const product = products.find(p =>
          `action-${p.id}` === activeDropdown || `active-${p.id}` === activeDropdown
        );
        if (!product) return null;

        const isActiveDropdown = activeDropdown === `active-${product.id}`;
        const isActionDropdown = activeDropdown === `action-${product.id}`;

        // Render Active Status Dropdown
        if (isActiveDropdown) {
          const activeStatusOptions = [
            { value: true, label: 'Active', color: 'bg-[#10b981]' },
            { value: false, label: 'Inactive', color: 'bg-[#6b7280]' }
          ];

          return (
            <div
              ref={dropdownRef}
              className="fixed min-w-[120px] bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-[9999]"
              style={{
                top: `${dropdownPosition.top}px`,
                left: `${dropdownPosition.left}px`
              }}
            >
              {activeStatusOptions.map((option) => (
                <button
                  key={option.label}
                  onClick={() => {
                    if (onToggleActive) {
                      onToggleActive(product, option.value);
                    }
                    setActiveDropdown(null);
                  }}
                  className="w-full px-3 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2"
                  disabled={(product.isActive !== false) === option.value}
                >
                  <span className={`${option.color} w-2 h-2 rounded-full`}></span>
                  <span className={`text-[12px] font-['Poppins',sans-serif] ${(product.isActive !== false) === option.value
                    ? 'text-emerald-600 font-medium'
                    : 'text-[#212529]'
                    }`}>
                    {option.label}
                  </span>
                  {(product.isActive !== false) === option.value && (
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
                  navigate(`/products/${product.id}/batches`);
                  setActiveDropdown(null);
                }}
                className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-emerald-50 hover:text-emerald-600 transition-colors flex items-center gap-2"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M2 6.66667H14M2 6.66667V12.6667C2 13.0203 2.14048 13.3594 2.39052 13.6095C2.64057 13.8595 2.97971 14 3.33333 14H12.6667C13.0203 14 13.3594 13.8595 13.6095 13.6095C13.8595 13.3594 14 13.0203 14 12.6667V6.66667M2 6.66667V4.66667C2 4.31304 2.14048 3.97391 2.39052 3.72386C2.64057 3.47381 2.97971 3.33333 3.33333 3.33333H5.33333M14 6.66667V4.66667C14 4.31304 13.8595 3.97391 13.6095 3.72386C13.3594 3.47381 13.0203 3.33333 12.6667 3.33333H10.6667M5.33333 3.33333V2M5.33333 3.33333H10.6667M10.6667 3.33333V2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                View Batches
              </button>

              <button
                onClick={() => {
                  onEdit && onEdit(product);
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
                  onDelete && onDelete(product);
                  setActiveDropdown(null);
                }}
                disabled={product.isActive !== false}
                className={`w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] transition-colors flex items-center gap-2 ${product.isActive !== false
                  ? 'text-gray-400 cursor-not-allowed opacity-50'
                  : 'text-gray-700 hover:bg-red-50 hover:text-red-600'
                  }`}
                title={
                  product.isActive !== false
                    ? 'Product must be deactivated before deletion'
                    : 'Delete product'
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
