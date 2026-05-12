import React, { useState, useRef, useEffect } from 'react';

export const EmployeeList = ({ employees = [], onEdit, onDelete, onManageAccount, onViewDetails, onResetPassword, onSort, sortField, sortOrder }) => {
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

      setDropdownPosition({
        top: buttonRect.bottom + 4,
        left: buttonRect.right - 150
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
        <div className="min-w-[1000px]">
          {/* Table Header */}
          <div className="flex items-center h-[34px] bg-gray-50 border-b border-gray-200">
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('id')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                ID
                {getSortIcon('id')}
              </p>
            </div>

            {/* Full Name Column - Sortable */}
            <div
              className="flex-1 min-w-[180px] px-3 flex items-center cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('fullName')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Full Name
                {getSortIcon('fullName')}
              </p>
            </div>

            {/* Phone Column */}
            <div className="w-[140px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Phone
              </p>
            </div>

            {/* Address Column */}
            <div className="flex-1 min-w-[200px] px-3 flex items-center">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Address
              </p>
            </div>

            {/* Date of Birth Column */}
            <div className="w-[120px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Birth Date
              </p>
            </div>

            {/* Role Column */}
            <div className="w-[120px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Role
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
            {employees.map((employee, index) => {
              const actionDropdownId = `action-${employee.id}`;

              return (
                <div
                  key={employee.id}
                  className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== employees.length - 1 ? 'border-b border-gray-100' : ''
                    }`}
                >
                  {/* ID */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-emerald-600 leading-[20px]">
                      #{employee.id}
                    </p>
                  </div>

                  {/* Full Name */}
                  <div className="flex-1 min-w-[180px] px-3 flex items-center">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                      {employee.fullName}
                    </p>
                  </div>

                  {/* Phone */}
                  <div className="w-[140px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                      {employee.phone || 'N/A'}
                    </p>
                  </div>

                  {/* Address */}
                  <div className="flex-1 min-w-[200px] px-3 flex items-center">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate" title={employee.address}>
                      {employee.address || 'N/A'}
                    </p>
                  </div>

                  {/* Date of Birth */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                      {formatDate(employee.dateOfBirth)}
                    </p>
                  </div>

                  {/* Role */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    {employee.userAccount?.role?.roleName ? (
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-indigo-100 text-indigo-800">
                        {employee.userAccount.role.roleName}
                      </span>
                    ) : (
                      <span className="text-[13px] font-normal font-['Poppins',sans-serif] text-gray-400 leading-[20px]">
                        N/A
                      </span>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                    <button
                      onClick={(e) => toggleDropdown(actionDropdownId, e)}
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
          {employees.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No employees found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menu */}
      {activeDropdown && (() => {
        const employee = employees.find(e => activeDropdown === `action-${e.id}`);

        if (!employee) return null;

        return (
          <div
            ref={dropdownRef}
            className="fixed min-w-[150px] bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-[9999]"
            style={{
              top: `${dropdownPosition.top}px`,
              left: `${dropdownPosition.left}px`
            }}
          >
            <button
              onClick={() => {
                onViewDetails && onViewDetails(employee);
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M1 8C1 8 3.5 3 8 3C12.5 3 15 8 15 8C15 8 12.5 13 8 13C3.5 13 1 8 1 8Z" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M8 10C9.10457 10 10 9.10457 10 8C10 6.89543 9.10457 6 8 6C6.89543 6 6 6.89543 6 8C6 9.10457 6.89543 10 8 10Z" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="text-[12px] font-['Poppins',sans-serif] text-[#212529]">
                View Details
              </span>
            </button>

            <div className="border-t border-gray-200 my-1"></div>

            <button
              onClick={() => {
                onEdit && onEdit(employee);
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M11.3333 2.00004C11.5084 1.82494 11.7163 1.68605 11.9451 1.59129C12.1739 1.49653 12.4191 1.44775 12.6666 1.44775C12.9142 1.44775 13.1594 1.49653 13.3882 1.59129C13.617 1.68605 13.8249 1.82494 14 2.00004C14.1751 2.17513 14.314 2.383 14.4087 2.61178C14.5035 2.84055 14.5523 3.08575 14.5523 3.33337C14.5523 3.58099 14.5035 3.82619 14.4087 4.05497C14.314 4.28374 14.1751 4.49161 14 4.66671L5.00001 13.6667L1.33334 14.6667L2.33334 11L11.3333 2.00004Z" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="text-[12px] font-['Poppins',sans-serif] text-[#212529]">
                Edit Personal Info
              </span>
            </button>

            <button
              onClick={() => {
                onManageAccount && onManageAccount(employee);
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 10C9.65685 10 11 8.65685 11 7C11 5.34315 9.65685 4 8 4C6.34315 4 5 5.34315 5 7C5 8.65685 6.34315 10 8 10Z" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M8 1V2M8 14V15M3.93 3.93L4.64 4.64M11.36 11.36L12.07 12.07M1 8H2M14 8H15M3.93 12.07L4.64 11.36M11.36 4.64L12.07 3.93" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="text-[12px] font-['Poppins',sans-serif] text-[#212529]">
                Manage Account
              </span>
            </button>

            <button
              onClick={() => {
                onResetPassword && onResetPassword(employee);
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M11.3333 7.33333H4.66667C3.93029 7.33333 3.33334 7.93029 3.33334 8.66667V12.6667C3.33334 13.403 3.93029 14 4.66667 14H11.3333C12.0697 14 12.6667 13.403 12.6667 12.6667V8.66667C12.6667 7.93029 12.0697 7.33333 11.3333 7.33333Z" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M5.33334 7.33333V4.66667C5.33334 3.95942 5.61429 3.28115 6.11438 2.78105C6.61448 2.28095 7.29276 2 8.00001 2C8.70725 2 9.38553 2.28095 9.88563 2.78105C10.3857 3.28115 10.6667 3.95942 10.6667 4.66667V7.33333" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="text-[12px] font-['Poppins',sans-serif] text-[#212529]">
                Reset Password
              </span>
            </button>

            <div className="border-t border-gray-200 my-1"></div>

            <button
              onClick={() => {
                if (employee.isActive) {
                  alert('Cannot delete an active employee. Please deactivate the account first.');
                  setActiveDropdown(null);
                  return;
                }
                if (window.confirm(`Are you sure you want to delete ${employee.fullName}?`)) {
                  onDelete && onDelete(employee.id);
                }
                setActiveDropdown(null);
              }}
              disabled={employee.isActive}
              className={`w-full px-4 py-2 text-left transition-colors flex items-center gap-2 ${employee.isActive
                ? 'opacity-50 cursor-not-allowed bg-gray-50'
                : 'hover:bg-red-50 cursor-pointer'
                }`}
              title={employee.isActive ? 'Employee must be inactive before deletion' : 'Delete employee'}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M2 4H3.33333H14" stroke={employee.isActive ? "#9CA3AF" : "#EF4444"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M5.33334 4.00001V2.66668C5.33334 2.31305 5.47381 1.97392 5.72386 1.72387C5.97391 1.47382 6.31305 1.33334 6.66668 1.33334H9.33334C9.68697 1.33334 10.0261 1.47382 10.2761 1.72387C10.5262 1.97392 10.6667 2.31305 10.6667 2.66668V4.00001M12.6667 4.00001V13.3333C12.6667 13.687 12.5262 14.0261 12.2761 14.2761C12.0261 14.5262 11.687 14.6667 11.3333 14.6667H4.66668C4.31305 14.6667 3.97391 14.5262 3.72386 14.2761C3.47381 14.0261 3.33334 13.687 3.33334 13.3333V4.00001H12.6667Z" stroke={employee.isActive ? "#9CA3AF" : "#EF4444"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className={`text-[12px] font-['Poppins',sans-serif] ${employee.isActive ? 'text-gray-400' : 'text-red-600'}`}>
                Delete
              </span>
            </button>
          </div>
        );
      })()}
    </div>
  );
};
