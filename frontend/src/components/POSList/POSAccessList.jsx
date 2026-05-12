import React, { useState, useRef, useEffect } from 'react';

export const POSAccessList = ({
  posAccess = [],
  onViewDetails,
  onEditSettings,
  onResetPIN,
  onUnlock,
  onRevoke,
  onSort,
  sortField,
  sortOrder,
  maxFailedAttempts = 5
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
      setDropdownPosition({
        top: buttonRect.bottom + 4,
        left: buttonRect.right - 160
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

  // Get status badge
  const getStatusBadge = (access) => {
    if (!access.canAccessPOS) {
      return (
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-gray-500"></span>
          <span className="text-[13px] font-medium font-['Poppins',sans-serif] text-gray-700">Denied</span>
        </div>
      );
    }

    if (access.isPinLocked) {
      return (
        <div className="flex items-center gap-2">
          <span className="inline-block w-2 h-2 rounded-full bg-red-500"></span>
          <span className="text-[13px] font-medium font-['Poppins',sans-serif] text-red-700">Locked</span>
        </div>
      );
    }

    return (
      <div className="flex items-center gap-2">
        <span className="inline-block w-2 h-2 rounded-full bg-green-500"></span>
        <span className="text-[13px] font-medium font-['Poppins',sans-serif] text-green-700">Active</span>
      </div>
    );
  };

  // Format relative time
  const getRelativeTime = (dateString) => {
    if (!dateString) return 'Never';

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="bg-white rounded-lg shadow-sm">
      {/* Scrollable Container */}
      <div className="overflow-x-auto rounded-lg">
        <div className="min-w-[1100px]">
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

            {/* Name Column - Sortable */}
            <div
              className="flex-1 min-w-[180px] px-3 flex items-center cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('fullName')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Name
                {getSortIcon('fullName')}
              </p>
            </div>

            {/* POS Status Column - Sortable */}
            <div
              className="w-[140px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('status')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                POS Status
                {getSortIcon('status')}
              </p>
            </div>

            {/* Last Login Column - Sortable */}
            <div
              className="w-[140px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('posLastLogin')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Last Login
                {getSortIcon('posLastLogin')}
              </p>
            </div>

            {/* Failed Attempts Column - Sortable */}
            <div
              className="w-[130px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('pinFailedAttempts')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                Failed Attempts
                {getSortIcon('pinFailedAttempts')}
              </p>
            </div>

            {/* Lock Status Column */}
            <div className="w-[120px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                Lock Status
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
            {posAccess.map((access, index) => {
              const actionDropdownId = `action-${access.id}`;

              return (
                <div
                  key={access.id}
                  className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== posAccess.length - 1 ? 'border-b border-gray-100' : ''
                    }`}
                >
                  {/* ID */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-emerald-600 leading-[20px]">
                      #{access.employee?.id}
                    </p>
                  </div>

                  {/* Name */}
                  <div className="flex-1 min-w-[180px] px-3 flex items-center">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                      {access.employee?.fullName || 'N/A'}
                    </p>
                  </div>

                  {/* POS Status */}
                  <div className="w-[140px] px-3 flex items-center flex-shrink-0">
                    {getStatusBadge(access)}
                  </div>

                  {/* Last Login */}
                  <div className="w-[140px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                      {getRelativeTime(access.posLastLogin)}
                    </p>
                  </div>

                  {/* Failed Attempts */}
                  <div className="w-[130px] px-3 flex items-center flex-shrink-0">
                    <span className={`text-[13px] font-medium font-['Poppins',sans-serif] ${access.pinFailedAttempts >= Math.floor(maxFailedAttempts * 0.6) ? 'text-red-600' : 'text-gray-600'
                      }`}>
                      {access.pinFailedAttempts} / {maxFailedAttempts}
                    </span>
                  </div>

                  {/* Lock Status */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    {access.isPinLocked ? (
                      <span className="text-[13px] font-medium font-['Poppins',sans-serif] text-red-600">
                        {access.minutesUntilUnlock}m left
                      </span>
                    ) : (
                      <span className="text-[13px] font-normal font-['Poppins',sans-serif] text-gray-500">
                        -
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
          {posAccess.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No POS access records found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menu */}
      {activeDropdown && (() => {
        const access = posAccess.find(a => activeDropdown === `action-${a.id}`);

        if (!access) return null;

        return (
          <div
            ref={dropdownRef}
            className="fixed min-w-[160px] bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-[9999]"
            style={{
              top: `${dropdownPosition.top}px`,
              left: `${dropdownPosition.left}px`
            }}
          >
            <button
              onClick={() => {
                onViewDetails && onViewDetails(access);
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
                onEditSettings && onEditSettings(access);
                setActiveDropdown(null);
              }}
              className="w-full px-4 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 10C9.65685 10 11 8.65685 11 7C11 5.34315 9.65685 4 8 4C6.34315 4 5 5.34315 5 7C5 8.65685 6.34315 10 8 10Z" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M8 1V2M8 14V15M3.93 3.93L4.64 4.64M11.36 11.36L12.07 12.07M1 8H2M14 8H15M3.93 12.07L4.64 11.36M11.36 4.64L12.07 3.93" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className="text-[12px] font-['Poppins',sans-serif] text-[#212529]">
                Edit Settings
              </span>
            </button>

            {access.isPinLocked && (
              <button
                onClick={() => {
                  onUnlock && onUnlock(access);
                  setActiveDropdown(null);
                }}
                className="w-full px-4 py-2 text-left hover:bg-emerald-50 transition-colors flex items-center gap-2"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12.6667 7.33333H3.33333C2.59695 7.33333 2 7.93029 2 8.66667V13.3333C2 14.0697 2.59695 14.6667 3.33333 14.6667H12.6667C13.403 14.6667 14 14.0697 14 13.3333V8.66667C14 7.93029 13.403 7.33333 12.6667 7.33333Z" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M4.66666 7.33333V4.66667C4.66666 3.78261 5.01785 2.93476 5.643 2.30964C6.26814 1.68452 7.11594 1.33333 7.99999 1.33333C8.88405 1.33333 9.73189 1.68452 10.357 2.30964C10.9821 2.93476 11.3333 3.78261 11.3333 4.66667" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span className="text-[12px] font-['Poppins',sans-serif] text-emerald-600">
                  Unlock Account
                </span>
              </button>
            )}

            <div className="border-t border-gray-200 my-1"></div>

            <button
              onClick={() => {
                const isActive = access.canAccessPOS && !access.isPinLocked;
                if (!isActive) {
                  alert('Can only revoke access for active POS accounts');
                  setActiveDropdown(null);
                  return;
                }
                if (window.confirm(`Are you sure you want to revoke POS access for ${access.employee?.fullName}?`)) {
                  onRevoke && onRevoke(access.id);
                }
                setActiveDropdown(null);
              }}
              disabled={!access.canAccessPOS || access.isPinLocked}
              className={`w-full px-4 py-2 text-left transition-colors flex items-center gap-2 ${!access.canAccessPOS || access.isPinLocked
                ? 'opacity-50 cursor-not-allowed bg-gray-50'
                : 'hover:bg-red-50 cursor-pointer'
                }`}
              title={!access.canAccessPOS || access.isPinLocked ? 'Can only revoke access for active POS accounts' : 'Revoke POS access'}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10 6V12.6667C10 13.0203 9.85953 13.3594 9.60948 13.6095C9.35943 13.8595 9.02029 14 8.66667 14H3.33333C2.97971 14 2.64057 13.8595 2.39052 13.6095C2.14048 13.3594 2 13.0203 2 12.6667V6M12.6667 6V12.6667C12.6667 13.0203 12.5262 13.3594 12.2761 13.6095C12.0261 13.8595 11.687 14 11.3333 14H10.6667M4.66667 6V3.33333C4.66667 2.97971 4.80714 2.64057 5.05719 2.39052C5.30724 2.14048 5.64638 2 6 2H10C10.3536 2 10.6928 2.14048 10.9428 2.39052C11.1929 2.64057 11.3333 2.97971 11.3333 3.33333V6" stroke={!access.canAccessPOS || access.isPinLocked ? "#9CA3AF" : "#EF4444"} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <span className={`text-[12px] font-['Poppins',sans-serif] ${!access.canAccessPOS || access.isPinLocked ? 'text-gray-400' : 'text-red-600'
                }`}>
                Revoke Access
              </span>
            </button>
          </div>
        );
      })()}
    </div>
  );
};
