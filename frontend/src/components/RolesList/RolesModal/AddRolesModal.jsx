import React, { useEffect, useState } from 'react';
import roleService from '../../../services/roleService';
import permissionService from '../../../services/permissionService';

export const AddRolesModal = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    roleName: '',
    description: '',
    permissions: []
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [availablePermissions, setAvailablePermissions] = useState([]);
  const [loadingPermissions, setLoadingPermissions] = useState(true);

  // Fetch available permissions from backend
  useEffect(() => {
    const fetchPermissions = async () => {
      try {
        setLoadingPermissions(true);
        const response = await permissionService.getPermissions();
        if (response.success) {
          setAvailablePermissions(response.data.permissions || []);
        }
      } catch (error) {
        console.error('Error fetching permissions:', error);
        // Fallback to empty array if backend fails
        setAvailablePermissions([]);
      } finally {
        setLoadingPermissions(false);
      }
    };

    if (isOpen) {
      fetchPermissions();
    }
  }, [isOpen]);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setFormData({
        roleName: '',
        description: '',
        permissions: []
      });
      setError(null);
    }
  }, [isOpen]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handlePermissionToggle = (permission) => {
    setFormData(prev => {
      const currentPermissions = prev.permissions || [];
      const isSelected = currentPermissions.includes(permission);

      return {
        ...prev,
        permissions: isSelected
          ? currentPermissions.filter(p => p !== permission)
          : [...currentPermissions, permission]
      };
    });
  };

  const validateForm = () => {
    // Role name validation
    if (!formData.roleName.trim()) {
      setError('Role name is required');
      return false;
    }
    if (formData.roleName.length < 2 || formData.roleName.length > 50) {
      setError('Role name must be between 2 and 50 characters');
      return false;
    }

    // Description validation (optional)
    if (formData.description && formData.description.length > 200) {
      setError('Description must not exceed 200 characters');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        roleName: formData.roleName.trim(),
        description: formData.description.trim() || null,
        permissions: formData.permissions
      };

      const response = await roleService.createRole(payload);

      if (response.success) {
        if (onSuccess) onSuccess(response.data.role);
        onClose && onClose();
      } else {
        setError(response.error || 'Failed to create role');
      }
    } catch (err) {
      console.error('Error creating role:', err);
      const errorMessage = err.response?.data?.error?.message
        || err.message
        || 'Failed to create role. Please try again.';
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
          <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
            Add Role
          </h2>
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
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
              {error}
            </div>
          )}

          {/* Role Name */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Role Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.roleName}
              onChange={(e) => handleChange('roleName', e.target.value)}
              placeholder="Enter role name (2-50 characters)"
              required
              minLength={2}
              maxLength={50}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
              E.g., Manager, Cashier, Administrator
            </p>
          </div>

          {/* Description */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder="Enter role description (max 200 characters)"
              maxLength={200}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
            />
            <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif] text-right">
              {formData.description.length}/200 characters
            </p>
          </div>

          {/* Permissions */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Permissions
            </label>
            {loadingPermissions ? (
              <div className="border border-gray-300 rounded-lg p-4 flex items-center justify-center">
                <div className="flex items-center gap-2 text-gray-500 text-[13px]">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Loading permissions...
                </div>
              </div>
            ) : (
              <div className="border border-gray-300 rounded-lg p-4 max-h-[300px] overflow-y-auto">
                {availablePermissions.length === 0 ? (
                  <p className="text-center text-gray-500 text-[13px]">No permissions available</p>
                ) : (
                  <div className="grid grid-cols-2 gap-3">
                    {availablePermissions.map((permission) => (
                      <label
                        key={permission}
                        className="flex items-center cursor-pointer hover:bg-gray-50 p-2 rounded transition-colors"
                      >
                        <input
                          type="checkbox"
                          checked={formData.permissions.includes(permission)}
                          onChange={() => handlePermissionToggle(permission)}
                          className="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500"
                        />
                        <span className="ml-2 text-[12px] font-['Poppins',sans-serif] text-gray-700">
                          {permission.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            )}
            <p className="mt-2 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
              Selected: {formData.permissions.length} permission{formData.permissions.length !== 1 ? 's' : ''}
            </p>
          </div>

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
              disabled={loading}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Creating...
                </>
              ) : (
                'Create Role'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
