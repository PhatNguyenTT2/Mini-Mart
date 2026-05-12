import React from 'react';

export const ViewRolesModal = ({ isOpen, onClose, role }) => {
  if (!isOpen) return null;

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
              Role Details
            </h2>
            {role && (
              <p className="text-[12px] text-gray-500 font-['Poppins',sans-serif] mt-1">
                Role ID: #{role.id || 'N/A'}
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
          {/* Role Information */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
              </svg>
              <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                Role Information
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Role ID
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-emerald-600 font-medium">
                  #{role?.id || 'N/A'}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Role Name
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {role?.roleName || 'N/A'}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 col-span-2">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Description
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {role?.description || 'No description provided'}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Total Employees
                </p>
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
                  </svg>
                  <p className="text-[18px] font-semibold font-['Poppins',sans-serif] text-emerald-600">
                    {role?.employeeCount ?? 0}
                  </p>
                  <span className="text-[13px] font-['Poppins',sans-serif] text-gray-500">
                    employee{role?.employeeCount !== 1 ? 's' : ''}
                  </span>
                </div>
              </div>

            </div>
          </div>

          {/* Permissions */}
          {role?.permissions && role.permissions.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b">
                <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                  Permissions
                </h3>
                <span className="ml-auto text-[12px] font-medium font-['Poppins',sans-serif] text-emerald-600 bg-emerald-50 px-2 py-1 rounded">
                  {role.permissions.length} permission{role.permissions.length !== 1 ? 's' : ''}
                </span>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-2">
                  {role.permissions.map((permission, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-[12px] font-['Poppins',sans-serif] text-blue-700">
                        {permission.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* No Permissions State */}
          {(!role?.permissions || role.permissions.length === 0) && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 pb-2 border-b">
                <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                  Permissions
                </h3>
              </div>

              <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
                <svg className="w-12 h-12 text-gray-400 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <p className="text-[13px] font-['Poppins',sans-serif] text-gray-500">
                  No permissions assigned to this role
                </p>
              </div>
            </div>
          )}


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
