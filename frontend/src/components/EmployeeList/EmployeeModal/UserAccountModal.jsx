import React, { useEffect, useState } from 'react';
import userAccountService from '../../../services/userAccountService';
import roleService from '../../../services/roleService';

export const UserAccountModal = ({ isOpen, onClose, onSuccess, employee }) => {
  const [formData, setFormData] = useState({
    role: '',
    isActive: true
  });

  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  const [error, setError] = useState(null);
  const [isEditingSelf, setIsEditingSelf] = useState(false);
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [filteredRoles, setFilteredRoles] = useState([]);

  // Check if user is editing their own account
  useEffect(() => {
    if (isOpen && employee) {
      // Get current logged-in user from localStorage
      const currentUser = JSON.parse(localStorage.getItem('user') || '{}');
      const currentUserId = currentUser.id || currentUser._id;
      const targetUserId = employee.userAccount?.id || employee.userAccount?._id;

      setIsEditingSelf(currentUserId === targetUserId);

      // Check if current user is super admin
      const userRole = currentUser.role || {};
      const permissions = userRole.permissions || [];
      setIsSuperAdmin(permissions.includes('all'));
    }
  }, [isOpen, employee]);

  // Load roles and user account data when modal opens
  useEffect(() => {
    if (isOpen && employee) {
      loadRoles();
      // Load user account data
      setFormData({
        role: employee.userAccount?.role?.id || employee.userAccount?.role || '',
        isActive: employee.userAccount?.isActive ?? true
      });
      setError(null);
    }
  }, [isOpen, employee, isSuperAdmin]);

  const loadRoles = async () => {
    try {
      setLoadingData(true);
      const response = await roleService.getAllRoles();
      const allRoles = response.data?.roles || [];
      setRoles(allRoles);

      // Filter roles based on current user permissions
      // Only super admin can assign super admin role
      if (!isSuperAdmin) {
        const nonSuperAdminRoles = allRoles.filter(role =>
          !role.permissions || !role.permissions.includes('all')
        );
        setFilteredRoles(nonSuperAdminRoles);
      } else {
        setFilteredRoles(allRoles);
      }
    } catch (err) {
      console.error('Error loading roles:', err);
      setError('Failed to load roles');
    } finally {
      setLoadingData(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const validateForm = () => {
    // Role validation
    if (!formData.role) {
      setError('Role is required');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    if (!employee || !employee.userAccount?.id) {
      setError('User Account ID is missing');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        role: formData.role,
        isActive: formData.isActive
      };

      const response = await userAccountService.updateUser(employee.userAccount.id, payload);

      if (response.success) {
        if (onSuccess) onSuccess(response.data.userAccount);
        onClose && onClose();
      } else {
        setError(response.error || 'Failed to update account');
      }
    } catch (err) {
      console.error('Error updating account:', err);
      const errorMessage = err.response?.data?.error?.message
        || err.message
        || 'Failed to update account. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Manage User Account
            </h2>
            {employee && (
              <p className="text-[12px] text-gray-500 font-['Poppins',sans-serif] mt-1">
                User: {employee.userAccount?.username || 'N/A'} (#{employee.id})
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
              {error}
            </div>
          )}

          {/* Loading State */}
          {loadingData && (
            <div className="text-center py-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto"></div>
              <p className="mt-2 text-[13px] text-gray-500 font-['Poppins',sans-serif]">
                Loading...
              </p>
            </div>
          )}

          {!loadingData && (
            <>
              {/* Account Information (Read-only) */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 space-y-3">
                <h3 className="text-[14px] font-semibold font-['Poppins',sans-serif] text-gray-700">
                  Account Information
                </h3>

                <div className="grid grid-cols-2 gap-4 text-[13px]">
                  <div>
                    <span className="text-gray-600 font-['Poppins',sans-serif]">Username:</span>
                    <p className="font-medium font-['Poppins',sans-serif] text-gray-900 mt-1">
                      {employee?.userAccount?.username || 'N/A'}
                    </p>
                  </div>

                  <div>
                    <span className="text-gray-600 font-['Poppins',sans-serif]">Email:</span>
                    <p className="font-medium font-['Poppins',sans-serif] text-gray-900 mt-1">
                      {employee?.userAccount?.email || 'N/A'}
                    </p>
                  </div>

                  <div>
                    <span className="text-gray-600 font-['Poppins',sans-serif]">Employee:</span>
                    <p className="font-medium font-['Poppins',sans-serif] text-gray-900 mt-1">
                      {employee?.fullName || 'N/A'}
                    </p>
                  </div>

                  <div>
                    <span className="text-gray-600 font-['Poppins',sans-serif]">Current Role:</span>
                    <p className="font-medium font-['Poppins',sans-serif] text-gray-900 mt-1">
                      {employee?.userAccount?.role?.roleName || 'N/A'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Warning Message */}
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <svg className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <div>
                    <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-amber-800 mb-1">
                      Security Notice
                    </p>
                    <p className="text-[12px] font-['Poppins',sans-serif] text-amber-700">
                      Changing the role or account status will affect the user's access permissions and login ability.
                      Please ensure you have the necessary authorization to make these changes.
                    </p>
                  </div>
                </div>
              </div>

              {/* Self-Edit Warning */}
              {isEditingSelf && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <div>
                      <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-red-800 mb-1">
                        Self-Modification Restricted
                      </p>
                      <p className="text-[12px] font-['Poppins',sans-serif] text-red-700">
                        You cannot modify your own role or account status for security reasons.
                        Please contact another administrator to make changes to your account.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Account Settings */}
              <div className="space-y-4">
                <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700 border-b pb-2">
                  Account Settings
                </h3>

                {/* Role Selection */}
                <div>
                  <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                    User Role <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.role}
                    onChange={(e) => handleChange('role', e.target.value)}
                    required
                    disabled={isEditingSelf}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    <option value="">Select a role</option>
                    {filteredRoles.map((role) => (
                      <option key={role.id} value={role.id}>
                        {role.roleName} - {role.description}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                    {isEditingSelf
                      ? 'You cannot change your own role'
                      : !isSuperAdmin
                        ? 'Only Super Admin can assign Super Admin role'
                        : 'Select the role that defines this user\'s permissions'}
                  </p>
                </div>

                {/* Account Status */}
                <div>
                  <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-3">
                    Account Status
                  </label>

                  <div className="space-y-3">
                    {/* Active Option */}
                    <label className="flex items-start cursor-pointer group">
                      <input
                        type="radio"
                        name="accountStatus"
                        checked={formData.isActive === true}
                        onChange={() => handleChange('isActive', true)}
                        disabled={isEditingSelf}
                        className="mt-1 w-4 h-4 text-emerald-600 border-gray-300 focus:ring-emerald-500 disabled:cursor-not-allowed"
                      />
                      <div className="ml-3">
                        <span className="text-[13px] font-medium font-['Poppins',sans-serif] text-gray-900">
                          Active
                        </span>
                        <p className="text-[11px] text-gray-500 font-['Poppins',sans-serif] mt-0.5">
                          User can log in and access the system
                        </p>
                      </div>
                    </label>

                    {/* Inactive Option */}
                    <label className="flex items-start cursor-pointer group">
                      <input
                        type="radio"
                        name="accountStatus"
                        checked={formData.isActive === false}
                        onChange={() => handleChange('isActive', false)}
                        disabled={isEditingSelf}
                        className="mt-1 w-4 h-4 text-red-600 border-gray-300 focus:ring-red-500 disabled:cursor-not-allowed"
                      />
                      <div className="ml-3">
                        <span className="text-[13px] font-medium font-['Poppins',sans-serif] text-gray-900">
                          Inactive
                        </span>
                        <p className="text-[11px] text-gray-500 font-['Poppins',sans-serif] mt-0.5">
                          User cannot log in or access the system
                        </p>
                      </div>
                    </label>
                  </div>
                  {isEditingSelf && (
                    <p className="mt-2 text-[11px] text-red-600 font-['Poppins',sans-serif]">
                      You cannot deactivate your own account
                    </p>
                  )}
                </div>

                {/* Change Summary */}
                {employee && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-[12px] font-semibold font-['Poppins',sans-serif] text-blue-800 mb-2">
                      Change Summary:
                    </p>
                    <div className="space-y-1 text-[12px] font-['Poppins',sans-serif] text-blue-700">
                      {formData.role !== (employee.userAccount?.role?.id || employee.userAccount?.role) && (
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          <span>
                            Role will change from "{employee.userAccount?.role?.roleName}" to "{roles.find(r => r.id === formData.role)?.roleName}"
                          </span>
                        </div>
                      )}
                      {formData.isActive !== (employee.userAccount?.isActive ?? true) && (
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                          <span>
                            Status will change to {formData.isActive ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                      )}
                      {formData.role === (employee.userAccount?.role?.id || employee.userAccount?.role)
                        && formData.isActive === (employee.userAccount?.isActive ?? true) && (
                          <div className="flex items-center gap-2 text-gray-600">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                            <span>No changes detected</span>
                          </div>
                        )}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Footer Buttons */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || loadingData || isEditingSelf}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Updating...
                </>
              ) : isEditingSelf ? (
                <>
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                  </svg>
                  Cannot Modify Own Account
                </>
              ) : (
                'Update Account'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
