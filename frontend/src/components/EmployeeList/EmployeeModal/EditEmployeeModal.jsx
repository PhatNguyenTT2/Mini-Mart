import React, { useEffect, useState } from 'react';
import employeeService from '../../../services/employeeService';
import roleService from '../../../services/roleService';

export const EditEmployeeModal = ({ isOpen, onClose, onSuccess, employee }) => {
  const [formData, setFormData] = useState({
    // User Account Data
    username: '',
    email: '',
    role: '',
    isActive: true,

    // Employee Data
    fullName: '',
    phone: '',
    address: '',
    dateOfBirth: ''
  });

  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  const [error, setError] = useState(null);

  // Load roles and employee data when modal opens
  useEffect(() => {
    if (isOpen && employee) {
      loadRoles();
      // Load employee data
      setFormData({
        username: employee.userAccount?.username || '',
        email: employee.userAccount?.email || '',
        role: employee.userAccount?.role?.id || employee.userAccount?.role || '',
        isActive: employee.userAccount?.isActive ?? true,
        fullName: employee.fullName || '',
        phone: employee.phone || '',
        address: employee.address || '',
        dateOfBirth: employee.dateOfBirth ? employee.dateOfBirth.split('T')[0] : ''
      });
      setError(null);
    }
  }, [isOpen, employee]);

  const loadRoles = async () => {
    try {
      setLoadingData(true);
      const response = await roleService.getAllRoles();
      setRoles(response.data?.roles || []);
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
    // Username validation (read-only in edit mode, but validate anyway)
    if (!formData.username.trim()) {
      setError('Username is required');
      return false;
    }

    // Email validation (read-only in edit mode)
    if (!formData.email.trim()) {
      setError('Email is required');
      return false;
    }

    // Role validation
    if (!formData.role) {
      setError('Role is required');
      return false;
    }

    // Full name validation
    if (!formData.fullName.trim()) {
      setError('Full name is required');
      return false;
    }
    if (formData.fullName.length < 3 || formData.fullName.length > 100) {
      setError('Full name must be between 3 and 100 characters');
      return false;
    }

    // Phone validation (optional, but validate format if provided)
    if (formData.phone && !/^[0-9]{10,15}$/.test(formData.phone)) {
      setError('Phone number must be 10-15 digits');
      return false;
    }

    // Address validation (optional)
    if (formData.address && formData.address.length > 200) {
      setError('Address must not exceed 200 characters');
      return false;
    }

    // Date of birth validation (optional, but validate if provided)
    if (formData.dateOfBirth) {
      const birthDate = new Date(formData.dateOfBirth);
      const today = new Date();
      const age = today.getFullYear() - birthDate.getFullYear();

      if (birthDate > today) {
        setError('Date of birth cannot be in the future');
        return false;
      }
      if (age < 16 || age > 100) {
        setError('Employee must be between 16 and 100 years old');
        return false;
      }
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    if (!employee || !employee.id) {
      setError('Employee ID is missing');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Update employee profile data
      const profilePayload = {
        fullName: formData.fullName.trim()
      };

      // Add optional fields
      if (formData.phone) {
        profilePayload.phone = formData.phone.trim();
      } else {
        profilePayload.phone = '';
      }

      if (formData.address) {
        profilePayload.address = formData.address.trim();
      } else {
        profilePayload.address = '';
      }

      if (formData.dateOfBirth) {
        profilePayload.dateOfBirth = formData.dateOfBirth;
      } else {
        profilePayload.dateOfBirth = null;
      }

      const response = await employeeService.updateEmployee(employee.id, profilePayload);

      if (response.success) {
        if (onSuccess) onSuccess(response.data.employee);
        onClose && onClose();
      } else {
        setError(response.error || 'Failed to update employee');
      }
    } catch (err) {
      console.error('Error updating employee:', err);
      const errorMessage = err.response?.data?.error?.message
        || err.message
        || 'Failed to update employee. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Edit Employee
            </h2>
            {employee && (
              <p className="text-[12px] text-gray-500 font-['Poppins',sans-serif] mt-1">
                Employee ID: #{employee.id}
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
              {/* Section: User Account Information (Read-only) */}
              <div className="space-y-4">
                <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700 border-b pb-2">
                  User Account Information
                </h3>

                {/* Username & Email (Read-only) */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                      Username
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      disabled
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] bg-gray-50 text-gray-500 cursor-not-allowed"
                    />
                    <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                      Username cannot be changed
                    </p>
                  </div>

                  <div>
                    <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                      Email
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      disabled
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] bg-gray-50 text-gray-500 cursor-not-allowed"
                    />
                    <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                      Email cannot be changed
                    </p>
                  </div>
                </div>

                {/* Role & Status (Read-only for now) */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                      Role
                    </label>
                    <select
                      value={formData.role}
                      disabled
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] bg-gray-50 text-gray-500 cursor-not-allowed"
                    >
                      <option value="">Select role</option>
                      {roles.map((role) => (
                        <option key={role.id} value={role.id}>
                          {role.roleName}
                        </option>
                      ))}
                    </select>
                    <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                      Role cannot be changed here
                    </p>
                  </div>

                  <div>
                    <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                      Account Status
                    </label>
                    <div className="flex items-center h-[42px]">
                      <label className="flex items-center cursor-not-allowed">
                        <input
                          type="checkbox"
                          checked={formData.isActive}
                          disabled
                          className="w-4 h-4 text-emerald-600 border-gray-300 rounded cursor-not-allowed"
                        />
                        <span className="ml-2 text-[13px] font-['Poppins',sans-serif] text-gray-500">
                          {formData.isActive ? 'Active' : 'Inactive'}
                        </span>
                      </label>
                    </div>
                    <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                      Status cannot be changed here
                    </p>
                  </div>
                </div>
              </div>

              {/* Section: Employee Personal Information (Editable) */}
              <div className="space-y-4">
                <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700 border-b pb-2">
                  Personal Information
                </h3>

                {/* Full Name */}
                <div>
                  <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                    Full Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.fullName}
                    onChange={(e) => handleChange('fullName', e.target.value)}
                    placeholder="Enter full name (3-100 characters)"
                    required
                    minLength={3}
                    maxLength={100}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                </div>

                {/* Phone & Date of Birth */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                      Phone Number
                    </label>
                    <input
                      type="tel"
                      value={formData.phone}
                      onChange={(e) => handleChange('phone', e.target.value)}
                      placeholder="10-15 digits"
                      pattern="[0-9]{10,15}"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                    <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                      Optional - Numbers only
                    </p>
                  </div>

                  <div>
                    <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                      Date of Birth
                    </label>
                    <input
                      type="date"
                      value={formData.dateOfBirth}
                      onChange={(e) => handleChange('dateOfBirth', e.target.value)}
                      max={new Date().toISOString().split('T')[0]}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                    <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                      Optional
                    </p>
                  </div>
                </div>

                {/* Address */}
                <div>
                  <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                    Address
                  </label>
                  <textarea
                    value={formData.address}
                    onChange={(e) => handleChange('address', e.target.value)}
                    placeholder="Enter address (max 200 characters)"
                    maxLength={200}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
                  />
                  <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif] text-right">
                    {formData.address.length}/200 characters
                  </p>
                </div>
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
              disabled={loading || loadingData}
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
              ) : (
                'Update Employee'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
