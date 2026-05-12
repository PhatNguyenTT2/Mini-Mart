import React, { useState, useRef, useEffect } from 'react';
import { EditProductBatchModal } from './EditProductBatchModal';

// Helper function to format VND currency
const formatVND = (amount) => {
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND'
  }).format(amount);
};

// Helper function to format date
const formatDate = (dateString) => {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString('vi-VN');
};

export const ProductBatchList = ({
  batches = [],
  onSort,
  sortField,
  sortOrder,
  onEdit,
  onDelete,
  onUpdateStatus,
  addModalOpen,
  onCloseAddModal,
  onAddSuccess,
  editModalOpen,
  editBatch,
  onCloseEditModal,
  onEditSuccess,
  productId
}) => {
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

  // Toggle dropdown
  const toggleDropdown = (batchId, type, event) => {
    const dropdownKey = `${type}-${batchId}`;
    if (activeDropdown === dropdownKey) {
      setActiveDropdown(null);
    } else {
      const buttonRect = event.currentTarget.getBoundingClientRect();

      // Determine position based on dropdown type
      let leftPosition;
      if (type === 'status') {
        // For Status: show dropdown to the right of button
        leftPosition = buttonRect.left;
      } else {
        // For Actions: show dropdown aligned to the right
        leftPosition = buttonRect.right - 140; // 140px is dropdown width
      }

      setDropdownPosition({
        top: buttonRect.bottom + 4,
        left: leftPosition
      });
      setActiveDropdown(dropdownKey);
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

  // Get status badge color
  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return 'bg-[#10b981]';
      case 'expired':
        return 'bg-[#ef4444]';
      default:
        return 'bg-[#6b7280]';
    }
  };

  return (
    <>
      <div className="bg-white rounded-lg shadow-sm">
        {/* Scrollable Container */}
        <div className="overflow-x-auto rounded-lg">
          <div className="min-w-[900px]">
            {/* Table Header */}
            <div className="flex items-center h-[34px] bg-gray-50 border-b border-gray-200">
              {/* Batch Code Column - Sortable */}
              <div
                className="w-[180px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSortClick('batchCode')}
              >
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center gap-1">
                  Batch Code
                  {getSortIcon('batchCode')}
                </p>
              </div>

              {/* Cost Price Column */}
              <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                  Cost Price
                </p>
              </div>

              {/* Unit Price Column */}
              <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                  Unit Price
                </p>
              </div>

              {/* Quantity Column */}
              <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                  Quantity
                </p>
              </div>

              {/* MFG Date Column */}
              <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                  MFG Date
                </p>
              </div>

              {/* Expiry Date Column */}
              <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                  Expiry Date
                </p>
              </div>

              {/* Promotion Column */}
              <div className="flex-1 min-w-[140px] px-3 flex items-center justify-center">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                  Promotion
                </p>
              </div>

              {/* Status Column - Sortable */}
              <div
                className="w-[100px] px-3 flex items-center justify-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
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
              {batches.map((batch, index) => (
                <div
                  key={batch.id}
                  className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== batches.length - 1 ? 'border-b border-gray-100' : ''
                    }`}
                >
                  {/* Batch Code */}
                  <div className="w-[180px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[12px] font-medium font-['Poppins',sans-serif] text-gray-600 leading-[20px] truncate">
                      {batch.batchCode || '-'}
                    </p>
                  </div>

                  {/* Cost Price */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                      {formatVND(batch.costPrice || 0)}
                    </p>
                  </div>

                  {/* Unit Price */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-emerald-600 leading-[20px]">
                      {formatVND(batch.unitPrice || 0)}
                    </p>
                  </div>

                  {/* Quantity */}
                  <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                    <p className={`text-[13px] font-medium font-['Poppins',sans-serif] leading-[20px] ${(batch.quantity || 0) > 10 ? 'text-emerald-600' : 'text-red-600'
                      }`}>
                      {batch.quantity || 0}
                    </p>
                  </div>

                  {/* MFG Date */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                      {formatDate(batch.mfgDate)}
                    </p>
                  </div>

                  {/* Expiry Date */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className={`text-[13px] font-normal font-['Poppins',sans-serif] leading-[20px] ${batch.isNearExpiry ? 'text-orange-600 font-medium' :
                      batch.isExpired ? 'text-red-600 font-medium' : 'text-[#212529]'
                      }`}>
                      {formatDate(batch.expiryDate)}
                      {batch.isNearExpiry && (
                        <span className="ml-1 text-[10px]">!</span>
                      )}
                    </p>
                  </div>

                  {/* Promotion */}
                  <div className="flex-1 min-w-[140px] px-3 flex items-center justify-center">
                    <span className={`text-[11px] font-medium font-['Poppins',sans-serif] leading-[18px] px-2 py-0.5 rounded ${batch.promotionApplied === 'none' || !batch.promotionApplied
                      ? 'text-gray-400'
                      : 'bg-orange-100 text-orange-700'
                      }`}>
                      {batch.promotionApplied === 'none' || !batch.promotionApplied ? '-' :
                        batch.promotionApplied === 'discount' ? `${batch.discountPercentage}%` :
                          batch.promotionApplied}
                    </span>
                  </div>

                  {/* Status - Dropdown */}
                  <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                    <button
                      onClick={(e) => toggleDropdown(batch.id, 'status', e)}
                      className={`${getStatusColor(batch.status)} px-2 py-1 rounded inline-flex items-center gap-1 cursor-pointer hover:opacity-90 transition-opacity`}
                    >
                      <span className="text-[9px] font-bold font-['Poppins',sans-serif] text-white leading-[10px] uppercase">
                        {batch.status}
                      </span>
                      <svg width="8" height="5" viewBox="0 0 8 5" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M1 1L4 4L7 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>

                  {/* Actions */}
                  <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                    <button
                      onClick={(e) => toggleDropdown(batch.id, 'action', e)}
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
            {batches.length === 0 && (
              <div className="py-16 text-center">
                <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                  No batches found
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Fixed Position Dropdown Menu */}
        {activeDropdown && (() => {
          const batch = batches.find(b =>
            `action-${b.id}` === activeDropdown || `status-${b.id}` === activeDropdown
          );
          if (!batch) return null;

          const isStatusDropdown = activeDropdown === `status-${batch.id}`;
          const isActionDropdown = activeDropdown === `action-${batch.id}`;

          // Render Status Dropdown
          if (isStatusDropdown) {
            const statusOptions = [
              { value: 'active', label: 'Active', color: 'bg-[#10b981]' },
              { value: 'expired', label: 'Expired', color: 'bg-[#ef4444]' }
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
                {statusOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => {
                      onUpdateStatus && onUpdateStatus(batch, option.value);
                      setActiveDropdown(null);
                    }}
                    className="w-full px-3 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2"
                    disabled={batch.status === option.value}
                  >
                    <span className={`${option.color} w-2 h-2 rounded-full`}></span>
                    <span className={`text-[12px] font-['Poppins',sans-serif] ${batch.status === option.value ? 'text-emerald-600 font-medium' : 'text-[#212529]'
                      }`}>
                      {option.label}
                    </span>
                    {batch.status === option.value && (
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
                    onEdit && onEdit(batch);
                    setActiveDropdown(null);
                  }}
                  className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors flex items-center gap-2"
                >
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M11.3333 2.00004C11.5084 1.82494 11.7163 1.68605 11.9451 1.59129C12.1739 1.49653 12.4191 1.44775 12.6666 1.44775C12.9142 1.44775 13.1594 1.49653 13.3882 1.59129C13.617 1.68605 13.8249 1.82494 14 2.00004C14.1751 2.17513 14.314 2.383 14.4088 2.61178C14.5035 2.84055 14.5523 3.08575 14.5523 3.33337C14.5523 3.58099 14.5035 3.82619 14.4088 4.05497C14.314 4.28374 14.1751 4.49161 14 4.66671L5.00001 13.6667L1.33334 14.6667L2.33334 11L11.3333 2.00004Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Edit
                </button>

                <div className="border-t border-gray-200 my-1"></div>

                <button
                  onClick={() => {
                    onDelete && onDelete(batch);
                    setActiveDropdown(null);
                  }}
                  className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-red-50 hover:text-red-600 transition-colors flex items-center gap-2"
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
      {/* Edit Batch Modal */}
      <EditProductBatchModal
        isOpen={editModalOpen}
        onClose={onCloseEditModal}
        onSuccess={onEditSuccess}
        batch={editBatch}
      />
    </>
  );
};
