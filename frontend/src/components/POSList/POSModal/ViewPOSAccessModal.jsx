import { useEffect } from 'react';

export const ViewPOSAccessModal = ({ isOpen, onClose, employee, maxFailedAttempts = 5 }) => {
  // Close modal on Escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

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

  // Handle backdrop click
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen || !employee) return null;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              POS Access Details
            </h2>
            {employee && (
              <p className="text-[12px] text-gray-500 font-['Poppins',sans-serif] mt-1">
                Employee ID: #{employee.employee?.id}
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
          {/* Employee Information */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
              <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                Employee Information
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Full Name
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {employee?.employee?.fullName || 'N/A'}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Employee ID
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-emerald-600 font-medium">
                  #{employee?.employee?.id}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Email
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900 truncate" title={employee?.employee?.userAccount?.email}>
                  {employee?.employee?.userAccount?.email || 'N/A'}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Role
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {employee?.employee?.userAccount?.role?.roleName || 'N/A'}
                </p>
              </div>
            </div>
          </div>

          {/* POS Access Status */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 2a5 5 0 00-5 5v2a2 2 0 00-2 2v5a2 2 0 002 2h10a2 2 0 002-2v-5a2 2 0 00-2-2H7V7a3 3 0 015.905-.75 1 1 0 001.937-.5A5.002 5.002 0 0010 2z" />
              </svg>
              <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                POS Access Status
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Access Status
                </p>
                <div className="flex items-center gap-2">
                  <span className={`inline-block w-2 h-2 rounded-full ${employee?.canAccessPOS ? 'bg-green-500' : 'bg-red-500'}`}></span>
                  <p className={`text-[14px] font-medium font-['Poppins',sans-serif] ${employee?.canAccessPOS ? 'text-green-700' : 'text-red-700'}`}>
                    {employee?.canAccessPOS ? 'Enabled' : 'Disabled'}
                  </p>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  PIN Lock Status
                </p>
                <div className="flex items-center gap-2">
                  <span className={`inline-block w-2 h-2 rounded-full ${employee?.isPinLocked ? 'bg-red-500' : 'bg-green-500'}`}></span>
                  <p className={`text-[14px] font-medium font-['Poppins',sans-serif] ${employee?.isPinLocked ? 'text-red-700' : 'text-green-700'}`}>
                    {employee?.isPinLocked ? 'Locked' : 'Unlocked'}
                  </p>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  POS Last Login
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {formatDateTime(employee?.posLastLogin)}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Failed Attempts
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {employee?.pinFailedAttempts || 0} / {maxFailedAttempts}
                </p>
              </div>

              {employee?.isPinLocked && employee?.minutesUntilUnlock > 0 && (
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                    Unlocks In
                  </p>
                  <p className="text-[14px] font-['Poppins',sans-serif] text-red-600 font-medium">
                    {employee.minutesUntilUnlock} minute{employee.minutesUntilUnlock !== 1 ? 's' : ''}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* POS Access Warning/Info */}
          {!employee?.canAccessPOS && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-red-800 mb-1">
                    POS Access Disabled
                  </p>
                  <p className="text-[12px] font-['Poppins',sans-serif] text-red-700">
                    This employee currently cannot access the POS system. Enable access in the edit settings to allow POS login.
                  </p>
                </div>
              </div>
            </div>
          )}

          {employee?.isPinLocked && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-red-800 mb-1">
                    PIN Locked
                  </p>
                  <p className="text-[12px] font-['Poppins',sans-serif] text-red-700">
                    This employee's PIN is locked due to {employee.pinFailedAttempts} failed login attempts (max: {maxFailedAttempts}).
                    {employee.minutesUntilUnlock > 0 && ` Unlocks in ${employee.minutesUntilUnlock} minute${employee.minutesUntilUnlock !== 1 ? 's' : ''}.`}
                  </p>
                </div>
              </div>
            </div>
          )}

          {employee?.canAccessPOS && !employee?.isPinLocked && employee?.pinFailedAttempts > 0 && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-yellow-800 mb-1">
                    Failed Login Attempts Detected
                  </p>
                  <p className="text-[12px] font-['Poppins',sans-serif] text-yellow-700">
                    This employee has {employee.pinFailedAttempts} failed PIN attempt{employee.pinFailedAttempts !== 1 ? 's' : ''}.
                    The account will be locked after {maxFailedAttempts} failed attempts.
                  </p>
                </div>
              </div>
            </div>
          )}

          {employee?.canAccessPOS && !employee?.isPinLocked && employee?.pinFailedAttempts === 0 && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-green-800 mb-1">
                    POS Access Active
                  </p>
                  <p className="text-[12px] font-['Poppins',sans-serif] text-green-700">
                    This employee has full access to the POS system with no failed login attempts.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b">
              <svg className="w-5 h-5 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
              </svg>
              <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                Timestamps
              </h3>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Created At
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {formatDateTime(employee?.createdAt)}
                </p>
              </div>

              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-gray-500 uppercase tracking-wide mb-1">
                  Last Updated
                </p>
                <p className="text-[14px] font-['Poppins',sans-serif] text-gray-900">
                  {formatDateTime(employee?.updatedAt)}
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
