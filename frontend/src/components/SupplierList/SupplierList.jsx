import React, { useState, useRef, useEffect } from 'react';
import { AddSupplierModal } from './AddSupplierModal';
import { EditSupplierModal } from './EditSupplierModal';
import { ViewPurchaseOrdersModal } from './ViewPurchaseOrdersModal';

export const SupplierList = ({ suppliers = [], onSort, sortField, sortOrder, addModalOpen = false, onCloseAddModal, onAddSuccess, editModalOpen = false, editSupplier = null, onCloseEditModal, onEditSuccess, onEdit, onDelete, onToggleActive }) => {
  const [activeDropdown, setActiveDropdown] = useState(null); // Format: 'action-{supplierId}' or 'active-{supplierId}'
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const [selectedSupplierForPO, setSelectedSupplierForPO] = useState(null);
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
      // Position: for Active dropdown show near button's left; for Actions align right
      const leftPosition = dropdownId.startsWith('active-') ? buttonRect.left : (buttonRect.right - 160);

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

  // Format currency VND - always show no decimals
  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₫0';
    return `₫${Number(amount).toLocaleString('vi-VN')}`;
  };

  // Get debt status color
  const getDebtStatusColor = (currentDebt, creditLimit) => {
    if (!currentDebt || currentDebt === 0) return 'text-gray-600';

    const debtRatio = currentDebt / creditLimit;
    if (debtRatio >= 0.8) return 'text-red-600 font-semibold';
    if (debtRatio >= 0.5) return 'text-orange-600';
    return 'text-blue-600';
  };

  // Format payment terms
  const formatPaymentTerms = (terms) => {
    const termsMap = {
      'cod': 'COD',
      'net15': 'Net 15',
      'net30': 'Net 30',
      'net60': 'Net 60',
      'net90': 'Net 90'
    };
    return termsMap[terms] || terms;
  };

  return (
    <div className="bg-white rounded-lg shadow-sm">
      {/* Scrollable Container - overflow-x-auto allows horizontal scroll */}
      <div className="overflow-x-auto rounded-lg">
        <div className="min-w-[1200px]">
          {/* Table Header */}
          <div className="flex items-center h-[34px] bg-gray-50 border-b border-gray-200">
            {/* ID Column - Sortable */}
            <div
              className="w-[140px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('id')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                ID
                {getSortIcon('id')}
              </p>
            </div>

            {/* Company Name Column - Sortable - Flex */}
            <div
              className="flex-1 min-w-[200px] px-3 flex items-center cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('companyName')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Company Name
                {getSortIcon('companyName')}
              </p>
            </div>

            {/* Phone Column - Sortable */}
            <div
              className="w-[140px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('phone')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Phone
                {getSortIcon('phone')}
              </p>
            </div>

            {/* Address Column */}
            <div className="w-[200px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Address
              </p>
            </div>

            {/* Payment Terms Column - Sortable */}
            <div
              className="w-[100px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('paymentTerms')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Terms
                {getSortIcon('paymentTerms')}
              </p>
            </div>

            {/* Credit Limit Column - Sortable */}
            <div
              className="w-[130px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('creditLimit')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Credit Limit
                {getSortIcon('creditLimit')}
              </p>
            </div>

            {/* Current Debt Column - Sortable */}
            <div
              className="w-[130px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('currentDebt')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Current Debt
                {getSortIcon('currentDebt')}
              </p>
            </div>

            {/* Active Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('isActive')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
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
            {suppliers.map((supplier, index) => {
              return (
                <div
                  key={supplier.id}
                  className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== suppliers.length - 1 ? 'border-b border-gray-100' : ''
                    }`}
                >
                  {/* ID - Display #id */}
                  <div className="w-[140px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-emerald-600 leading-[20px]">
                      #{supplier.id}
                    </p>
                  </div>

                  {/* Company Name - Flex */}
                  <div className="flex-1 min-w-[200px] px-3 flex items-center">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                      {supplier.companyName}
                    </p>
                  </div>

                  {/* Phone */}
                  <div className="w-[140px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                      {supplier.phone || 'N/A'}
                    </p>
                  </div>

                  {/* Address */}
                  <div className="w-[200px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                      {supplier.address || 'N/A'}
                    </p>
                  </div>

                  {/* Payment Terms */}
                  <div className="w-[100px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                      {formatPaymentTerms(supplier.paymentTerms)}
                    </p>
                  </div>

                  {/* Credit Limit */}
                  <div className="w-[130px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                      {formatCurrency(supplier.creditLimit)}
                    </p>
                  </div>

                  {/* Current Debt */}
                  <div className="w-[130px] px-3 flex items-center flex-shrink-0">
                    <p className={`text-[13px] font-normal font-['Poppins',sans-serif] leading-[20px] ${getDebtStatusColor(supplier.currentDebt, supplier.creditLimit)}`}>
                      {formatCurrency(supplier.currentDebt)}
                    </p>
                  </div>

                  {/* Active Status - Dropdown */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <button
                      onClick={(e) => toggleDropdown(`active-${supplier.id}`, e)}
                      className={`${supplier.isActive !== false ? 'bg-[#10b981]' : 'bg-[#6b7280]'} px-2 py-1 rounded inline-flex items-center gap-1 cursor-pointer hover:opacity-90 transition-opacity`}
                    >
                      <span className="text-[9px] font-bold font-['Poppins',sans-serif] text-white leading-[10px] uppercase">
                        {supplier.isActive !== false ? 'Active' : 'Inactive'}
                      </span>
                      <svg width="8" height="5" viewBox="0 0 8 5" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M1 1L4 4L7 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </div>

                  {/* Actions */}
                  <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                    <button
                      onClick={(e) => toggleDropdown(`action-${supplier.id}`, e)}
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
          {suppliers.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No suppliers found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menus - Rendered outside table container */}
      {activeDropdown && (() => {
        // Find the supplier based on activeDropdown ID
        const supplier = suppliers.find(s => activeDropdown === `action-${s.id}` || activeDropdown === `active-${s.id}`);

        if (!supplier) return null;

        const isActiveDropdown = activeDropdown === `active-${supplier.id}`;
        const isActionDropdown = activeDropdown === `action-${supplier.id}`;

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
                      onToggleActive(supplier);
                    }
                    setActiveDropdown(null);
                  }}
                  className="w-full px-3 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2"
                  disabled={(supplier.isActive !== false) === option.value}
                >
                  <span className={`${option.color} w-2 h-2 rounded-full`}></span>
                  <span className={`text-[12px] font-['Poppins',sans-serif] ${(supplier.isActive !== false) === option.value ? 'text-emerald-600 font-medium' : 'text-[#212529]'}`}>
                    {option.label}
                  </span>
                  {(supplier.isActive !== false) === option.value && (
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
                  onEdit ? onEdit(supplier) : console.log('Edit supplier:', supplier.id);
                  setActiveDropdown(null);
                }}
                className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-blue-50 hover:text-blue-600 transition-colors flex items-center gap-2"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M11.333 2.00004C11.5081 1.82494 11.716 1.68605 11.9447 1.59129C12.1735 1.49653 12.4187 1.44775 12.6663 1.44775C12.914 1.44775 13.1592 1.49653 13.3879 1.59129C13.6167 1.68605 13.8246 1.82494 13.9997 2.00004C14.1748 2.17513 14.3137 2.383 14.4084 2.61178C14.5032 2.84055 14.552 3.08575 14.552 3.33337C14.552 3.58099 14.5032 3.82619 14.4084 4.05497C14.3137 4.28374 14.1748 4.49161 13.9997 4.66671L5.33301 13.3334L1.33301 14.6667L2.66634 10.6667L11.333 2.00004Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Edit
              </button>

              <button
                onClick={() => {
                  setSelectedSupplierForPO(supplier);
                  setActiveDropdown(null);
                }}
                className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-purple-50 hover:text-purple-600 transition-colors flex items-center gap-2"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M2.66699 1.33337H4.00033L5.12033 7.99337C5.18105 8.32968 5.35349 8.63481 5.60772 8.85568C5.86195 9.07655 6.18293 9.19866 6.51366 9.20004H11.667C11.9977 9.19866 12.3187 9.07655 12.5729 8.85568C12.8272 8.63481 12.9996 8.32968 13.0603 7.99337L13.9337 3.33337H4.66699M6.00033 12.6667C6.00033 13.0349 5.70185 13.3334 5.33366 13.3334C4.96547 13.3334 4.66699 13.0349 4.66699 12.6667C4.66699 12.2985 4.96547 12 5.33366 12C5.70185 12 6.00033 12.2985 6.00033 12.6667ZM12.667 12.6667C12.667 13.0349 12.3685 13.3334 12.0003 13.3334C11.6321 13.3334 11.3337 13.0349 11.3337 12.6667C11.3337 12.2985 11.6321 12 12.0003 12C12.3685 12 12.667 12.2985 12.667 12.6667Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                View Purchase Orders
              </button>

              <div className="border-t border-gray-200 my-1"></div>

              <button
                onClick={() => {
                  onDelete ? onDelete(supplier) : console.log('Delete supplier:', supplier.id);
                  setActiveDropdown(null);
                }}
                className={`w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] transition-colors flex items-center gap-2 ${supplier.isActive !== false ? 'text-gray-400 cursor-not-allowed opacity-50' : 'text-gray-700 hover:bg-red-50 hover:text-red-600'}`}
                title={supplier.isActive !== false ? 'Supplier must be deactivated before deletion' : 'Delete supplier'}
                disabled={supplier.isActive !== false}
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

      {/* Add Supplier Modal (controlled by parent) */}
      <AddSupplierModal
        isOpen={addModalOpen}
        onClose={onCloseAddModal}
        onSuccess={onAddSuccess}
      />

      {/* Edit Supplier Modal (controlled by parent) */}
      <EditSupplierModal
        isOpen={editModalOpen}
        onClose={onCloseEditModal}
        onSuccess={onEditSuccess}
        supplier={editSupplier}
      />

      {/* View Purchase Orders Modal */}
      {selectedSupplierForPO && (
        <ViewPurchaseOrdersModal
          supplier={selectedSupplierForPO}
          onClose={() => setSelectedSupplierForPO(null)}
        />
      )}
    </div>
  );
};