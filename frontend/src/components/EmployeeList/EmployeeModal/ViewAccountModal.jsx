import React from 'react';

export const ViewAccountModal = ({ isOpen, onClose, employee }) => {
  if (!isOpen) return null;

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });
  };

  // Format datetime
  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Employee Details
            </h2>
            {employee && (
              <p className="text-[12px] text-gray-500 font-['Poppins',sans-serif] mt-1">
                Employee ID: #{employee.id}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* User Account Information */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
              <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                User Account Information
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Username
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {employee?.userAccount?.username || 'N/A'}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Employee ID
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-emerald-600 font-medium">
                  #{employee?.id}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Email
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900 truncate" title={employee?.userAccount?.email}>
                  {employee?.userAccount?.email || 'N/A'}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Role
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {employee?.userAccount?.role?.roleName || 'N/A'}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Account Status
                </p>
                <div className="flex items-center gap-2">
                  <span className={`inline-block w-2 h-2 rounded-full ${employee?.userAccount?.isActive ? 'bg-green-500' : 'bg-red-500'}`}></span>
                  <p className={`text-[14px] font-medium font-['Poppins',sans-serif] ${employee?.userAccount?.isActive ? 'text-green-700' : 'text-red-700'}`}>
                    {employee?.userAccount?.isActive ? 'Active' : 'Inactive'}
                  </p>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Account Created
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {formatDateTime(employee?.userAccount?.createdAt)}
                </p>
              </div>

            </div>
          </div>

          {/* Personal Information */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-6-3a2 2 0 11-4 0 2 2 0 014 0zm-2 4a5 5 0 00-4.546 2.916A5.986 5.986 0 0010 16a5.986 5.986 0 004.546-2.084A5 5 0 0010 11z" clipRule="evenodd" />
              </svg>
              <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                Personal Information
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Full Name
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {employee?.fullName || 'N/A'}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Date of Birth
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {formatDate(employee?.dateOfBirth)}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Phone Number
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {employee?.phone || 'N/A'}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Employee ID
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-emerald-600 font-medium">
                  {employee?.id || 'N/A'}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 col-span-2">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Address
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {employee?.address || 'N/A'}
                </p>
              </div>
            </div>
          </div>

          {/* Role Permissions (if available) */}
          {employee?.userAccount?.role?.permissions && employee.userAccount.role.permissions.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b">
                <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                </svg>
                <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                  Role Permissions
                </h3>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="text-[12px] font-semibold font-['Poppins',sans-serif] text-blue-800 mb-3">
                  {employee.userAccount.role.roleName} - Permissions:
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {employee.userAccount.role.permissions.map((permission, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-[12px] font-['Poppins',sans-serif] text-blue-700">
                        {permission}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Additional Information */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
              </svg>
              <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                Additional Information
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Account Last Updated
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {formatDateTime(employee?.userAccount?.updatedAt)}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Last Login
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {formatDateTime(employee?.userAccount?.lastLogin)}
                </p>
              </div>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
