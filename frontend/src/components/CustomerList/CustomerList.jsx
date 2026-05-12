import React, { useState, useRef, useEffect } from 'react';
import { AddCustomerModal } from './AddCustomerModal';
import { EditCustomerModal } from './EditCustomerModal';
import { ViewOrdersModal } from './ViewOrdersModal';

export const CustomerList = ({ customers = [], onSort, sortField, sortOrder, addModalOpen = false, onCloseAddModal, onAddSuccess, editModalOpen = false, editCustomer = null, onCloseEditModal, onEditSuccess, onEdit, onDelete, onToggleActive }) => {
  const [activeDropdown, setActiveDropdown] = useState(null); // Format: 'action-{customerId}' or 'active-{customerId}'
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const dropdownRef = useRef(null);
  const [viewOrdersModalOpen, setViewOrdersModalOpen] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);

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

  // Format currency VND
  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₫0';
    return `₫${Number(amount).toLocaleString('vi-VN')}`;
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  };

  // Format customer type
  const formatCustomerType = (type) => {
    const typeMap = {
      'guest': 'Guest',
      'retail': 'Retail',
      'wholesale': 'Wholesale',
      'vip': 'VIP'
    };
    return typeMap[type] || type;
  };

  return (
    <div className="bg-white rounded-lg shadow-sm">
      {/* Scrollable Container */}
      <div className="overflow-x-auto rounded-lg">
        <div className="min-w-[1200px]">
          {/* Table Header */}
          <div className="flex items-center h-[34px] bg-gray-50 border-b border-gray-200">
            {/* ID Column */}
            <div
              className="w-[80px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('id')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                ID
                {getSortIcon('id')}
              </p>
            </div>

            {/* Name Column */}
            <div
              className="flex-1 min-w-[150px] px-3 flex items-center cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('fullName')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Name
                {getSortIcon('fullName')}
              </p>
            </div>



            {/* Phone Column */}
            <div className="w-[120px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Phone
              </p>
            </div>

            {/* Address Column */}
            <div className="w-[360px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Address
              </p>
            </div>

            {/* Gender Column */}
            <div
              className="w-[90px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('gender')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Gender
                {getSortIcon('gender')}
              </p>
            </div>

            {/* Type Column */}
            <div
              className="w-[100px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('customerType')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Type
                {getSortIcon('customerType')}
              </p>
            </div>

            {/* Total Spent Column */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('totalSpent')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Total Spent
                {getSortIcon('totalSpent')}
              </p>
            </div>

            {/* Active Column */}
            <div
              className="w-[100px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
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
            {customers.map((customer, index) => (
              <div
                key={customer.id}
                className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== customers.length - 1 ? 'border-b border-gray-100' : ''}`}
              >
                {/* ID */}
                <div className="w-[80px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-emerald-600 leading-[20px]">
                    #{customer.id}
                  </p>
                </div>

                {/* Name */}
                <div className="flex-1 min-w-[150px] px-3 flex items-center">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                    {customer.fullName}
                  </p>
                </div>



                {/* Phone */}
                <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                    {customer.phone || 'N/A'}
                  </p>
                </div>

                {/* Address */}
                <div className="w-[360px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                    {customer.address || 'N/A'}
                  </p>
                </div>

                {/* Gender */}
                <div className="w-[90px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] capitalize">
                    {customer.gender || 'N/A'}
                  </p>
                </div>

                {/* Type */}
                <div className="w-[100px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                    {formatCustomerType(customer.customerType)}
                  </p>
                </div>

                {/* Total Spent */}
                <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                  <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                    {formatCurrency(customer.totalSpent)}
                  </p>
                </div>

                {/* Active Status */}
                <div className="w-[100px] px-3 flex items-center flex-shrink-0">
                  <button
                    onClick={(e) => toggleDropdown(`active-${customer.id}`, e)}
                    className={`${customer.isActive !== false ? 'bg-[#10b981]' : 'bg-[#6b7280]'} px-2 py-1 rounded inline-flex items-center gap-1 cursor-pointer hover:opacity-90 transition-opacity`}
                  >
                    <span className="text-[9px] font-bold font-['Poppins',sans-serif] text-white leading-[10px] uppercase">
                      {customer.isActive !== false ? 'Active' : 'Inactive'}
                    </span>
                    <svg width="8" height="5" viewBox="0 0 8 5" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M1 1L4 4L7 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </button>
                </div>

                {/* Actions */}
                <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                  <button
                    onClick={(e) => toggleDropdown(`action-${customer.id}`, e)}
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
          {customers.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No customers found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menus */}
      {activeDropdown && (() => {
        const customer = customers.find(c => activeDropdown === `action-${c.id}` || activeDropdown === `active-${c.id}`);
        if (!customer) return null;

        const isActiveDropdown = activeDropdown === `active-${customer.id}`;
        const isActionDropdown = activeDropdown === `action-${customer.id}`;

        // Active Status Dropdown
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
                    if (onToggleActive && (customer.isActive !== false) !== option.value) {
                      onToggleActive(customer);
                    }
                    setActiveDropdown(null);
                  }}
                  className="w-full px-3 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2"
                  disabled={(customer.isActive !== false) === option.value}
                >
                  <span className={`${option.color} w-2 h-2 rounded-full`}></span>
                  <span className={`text-[12px] font-['Poppins',sans-serif] ${(customer.isActive !== false) === option.value ? 'text-emerald-600 font-medium' : 'text-[#212529]'}`}>
                    {option.label}
                  </span>
                  {(customer.isActive !== false) === option.value && (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="ml-auto">
                      <path d="M10 3L4.5 8.5L2 6" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </button>
              ))}
            </div>
          );
        }

        // Actions Dropdown
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
                  onEdit ? onEdit(customer) : console.log('Edit customer:', customer.id);
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
                  setSelectedCustomer(customer);
                  setViewOrdersModalOpen(true);
                  setActiveDropdown(null);
                }}
                className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-purple-50 hover:text-purple-600 transition-colors flex items-center gap-2"
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M1.33301 1.33337H3.33301L4.66634 9.33337H12.6663L14.6663 3.33337H5.33301" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  <circle cx="5.33301" cy="12.6667" r="1" stroke="currentColor" strokeWidth="1.5" />
                  <circle cx="12" cy="12.6667" r="1" stroke="currentColor" strokeWidth="1.5" />
                </svg>
                View Orders
              </button>

              <div className="border-t border-gray-200 my-1"></div>

              <button
                onClick={() => {
                  onDelete ? onDelete(customer) : console.log('Delete customer:', customer.id);
                  setActiveDropdown(null);
                }}
                className="w-full px-4 py-2 text-left text-[12px] font-['Poppins',sans-serif] text-gray-700 hover:bg-red-50 hover:text-red-600 transition-colors flex items-center gap-2"
                title="Delete customer permanently"
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

      {/* Add Customer Modal */}
      <AddCustomerModal
        isOpen={addModalOpen}
        onClose={onCloseAddModal}
        onSuccess={onAddSuccess}
      />

      {/* Edit Customer Modal */}
      <EditCustomerModal
        isOpen={editModalOpen}
        onClose={onCloseEditModal}
        onSuccess={onEditSuccess}
        customer={editCustomer}
      />

      {/* View Orders Modal */}
      {viewOrdersModalOpen && (
        <ViewOrdersModal
          customer={selectedCustomer}
          onClose={() => {
            setViewOrdersModalOpen(false);
            setSelectedCustomer(null);
          }}
        />
      )}
    </div>
  );
};
