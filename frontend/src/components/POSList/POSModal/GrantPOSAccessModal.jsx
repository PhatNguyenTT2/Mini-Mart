import React, { useEffect, useState, useRef } from 'react';
import posAuthService from '../../../services/posAuthService';

export const GrantPOSAccessModal = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    employeeId: '',
    pin: '',
    confirmPin: ''
  });

  const [availableEmployees, setAvailableEmployees] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const searchTimeoutRef = useRef(null);
  const isInitialLoadRef = useRef(false);

  // Load available employees when modal opens (initial load only)
  useEffect(() => {
    if (isOpen) {
      // Reset form and state
      setFormData({
        employeeId: '',
        pin: '',
        confirmPin: ''
      });
      setSearchQuery('');
      setError(null);
      setAvailableEmployees([]);

      // Mark as initial load
      isInitialLoadRef.current = true;

      // Initial load
      loadAvailableEmployees('');
    } else {
      // Reset initial load flag when modal closes
      isInitialLoadRef.current = false;
    }
  }, [isOpen]);

  // Debounced search effect (skip initial load)
  useEffect(() => {
    if (!isOpen) return;

    // Skip if this is the initial load (already handled in first useEffect)
    if (isInitialLoadRef.current) {
      isInitialLoadRef.current = false;
      return;
    }

    // Clear previous timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    // Set new timeout
    searchTimeoutRef.current = setTimeout(() => {
      loadAvailableEmployees(searchQuery);
    }, 300);

    // Cleanup
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [searchQuery, isOpen]);

  const loadAvailableEmployees = async (search = '') => {
    try {
      setLoadingData(true);
      const response = await posAuthService.getAvailableEmployees({ search });

      if (response.success) {
        setAvailableEmployees(response.data || []);
      } else {
        setError(response.error || 'Failed to load available employees');
      }
    } catch (err) {
      console.error('Error loading available employees:', err);
      setError('Failed to load available employees');
    } finally {
      setLoadingData(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (error) setError(null);
  };

  const handleSearchChange = (value) => {
    setSearchQuery(value);
  };

  const validateForm = () => {
    // Employee selection validation
    if (!formData.employeeId) {
      setError('Please select an employee');
      return false;
    }

    // PIN validation
    if (!formData.pin) {
      setError('PIN is required');
      return false;
    }

    // PIN format validation (4-6 digits)
    if (!/^\d{4,6}$/.test(formData.pin)) {
      setError('PIN must be 4-6 digits only');
      return false;
    }

    // Check for weak PINs
    const weakPins = [
      '1234', '0000', '1111', '2222', '3333', '4444',
      '5555', '6666', '7777', '8888', '9999',
      '1212', '2323', '4321'
    ];
    if (weakPins.includes(formData.pin)) {
      setError('This PIN is too common. Please choose a more secure PIN');
      return false;
    }

    // Confirm PIN validation
    if (!formData.confirmPin) {
      setError('Please confirm PIN');
      return false;
    }

    if (formData.pin !== formData.confirmPin) {
      setError('PINs do not match');
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
      const response = await posAuthService.grantPOSAccess(
        formData.employeeId,
        formData.pin
      );

      if (response.success) {
        if (onSuccess) onSuccess(response.data);
        onClose && onClose();
      } else {
        setError(response.error || 'Failed to grant POS access');
      }
    } catch (err) {
      console.error('Error granting POS access:', err);
      const errorMessage = err.response?.data?.error?.message
        || err.message
        || 'Failed to grant POS access. Please try again.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Get selected employee details
  const selectedEmployee = availableEmployees.find(
    emp => Number(emp.id) === Number(formData.employeeId)
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Grant POS Access
            </h2>
            <p className="text-[13px] text-gray-500 font-['Poppins',sans-serif] mt-1">
              Assign POS access and PIN to an employee
            </p>
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
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px] font-['Poppins',sans-serif]">
              {error}
            </div>
          )}

          {/* Loading State */}
          {loadingData && (
            <div className="text-center py-4">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mx-auto"></div>
              <p className="mt-2 text-[13px] text-gray-500 font-['Poppins',sans-serif]">
                Loading employees...
              </p>
            </div>
          )}

          {!loadingData && (
            <>
              {/* Section: Select Employee */}
              <div className="space-y-4">
                <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700 border-b pb-2">
                  Select Employee
                </h3>

                {/* Search Employee */}
                <div>
                  <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                    Search Employee
                  </label>
                  <div className="relative">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => handleSearchChange(e.target.value)}
                      placeholder="Search by name..."
                      className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                    <svg
                      className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                </div>

                {/* Employee List */}
                <div>
                  <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                    Employee <span className="text-red-500">*</span>
                  </label>

                  {availableEmployees.length === 0 ? (
                    <div className="border border-gray-200 rounded-lg p-8 text-center">
                      <svg
                        className="w-12 h-12 text-gray-300 mx-auto mb-3"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                      </svg>
                      <p className="text-[13px] text-gray-500 font-['Poppins',sans-serif]">
                        No eligible employees available
                      </p>
                      <p className="text-[11px] text-gray-400 font-['Poppins',sans-serif] mt-1">
                        Only employees with a role that has <strong>pos_access</strong> permission can be granted POS access
                      </p>
                    </div>
                  ) : (
                    <div className="border border-gray-200 rounded-lg max-h-[200px] overflow-y-auto">
                      {availableEmployees.map((employee) => (
                        <label
                          key={employee.id}
                          className={`flex items-center p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0 ${String(formData.employeeId) === String(employee.id) ? 'bg-emerald-50' : ''
                            }`}
                        >
                          <input
                            type="radio"
                            name="employee"
                            value={employee.id}
                            checked={String(formData.employeeId) === String(employee.id)}
                            onChange={(e) => handleChange('employeeId', e.target.value)}
                            className="w-4 h-4 text-emerald-600 border-gray-300 focus:ring-emerald-500"
                          />
                          <div className="ml-3 flex-1">
                            <div className="flex items-center justify-between">
                              <span className="text-[13px] font-medium font-['Poppins',sans-serif] text-gray-900">
                                {employee.fullName}
                              </span>
                              <span className="text-[11px] font-['Poppins',sans-serif] text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                                {employee.userAccount?.role?.roleName || 'No Role'}
                              </span>
                            </div>
                            <div className="text-[11px] text-gray-500 font-['Poppins',sans-serif] mt-0.5">
                              #{employee.id} • {employee.userAccount?.email}
                            </div>
                          </div>
                        </label>
                      ))}
                    </div>
                  )}

                  <p className="mt-2 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                    {availableEmployees.length} employee(s) available
                  </p>
                </div>

                {/* Selected Employee Preview */}
                {selectedEmployee && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                    <div className="flex items-start gap-3">
                      <div className="w-10 h-10 bg-emerald-600 rounded-full flex items-center justify-center text-white font-semibold text-[14px]">
                        {selectedEmployee.fullName.charAt(0).toUpperCase()}
                      </div>
                      <div className="flex-1">
                        <div className="text-[13px] font-semibold font-['Poppins',sans-serif] text-gray-900">
                          {selectedEmployee.fullName}
                        </div>
                        <div className="text-[11px] text-gray-600 font-['Poppins',sans-serif] mt-0.5">
                          #{selectedEmployee.id} • {selectedEmployee.userAccount?.email}
                        </div>
                        <div className="text-[11px] text-emerald-700 font-['Poppins',sans-serif] mt-1">
                          Role: {selectedEmployee.userAccount?.role?.roleName}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Section: Set POS PIN */}
              <div className="space-y-4">
                <h3 className="text-[15px] font-semibold font-['Poppins',sans-serif] text-gray-700 border-b pb-2">
                  Set POS PIN
                </h3>

                {/* PIN Fields */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                      PIN <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.pin}
                      onChange={(e) => handleChange('pin', e.target.value)}
                      placeholder="Enter 4-6 digit PIN"
                      maxLength={6}
                      pattern="[0-9]*"
                      inputMode="numeric"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                  <div>
                    <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                      Confirm PIN <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={formData.confirmPin}
                      onChange={(e) => handleChange('confirmPin', e.target.value)}
                      placeholder="Re-enter PIN"
                      maxLength={6}
                      pattern="[0-9]*"
                      inputMode="numeric"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                  </div>
                </div>

                {/* PIN Requirements Info */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <svg className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <div className="flex-1">
                      <div className="text-[12px] font-semibold font-['Poppins',sans-serif] text-blue-800 mb-1">
                        PIN Requirements:
                      </div>
                      <ul className="text-[11px] text-blue-700 font-['Poppins',sans-serif] space-y-0.5 list-disc list-inside">
                        <li>Must be 4-6 digits</li>
                        <li>Only numbers allowed (0-9)</li>
                        <li>Avoid common patterns: 1234, 0000, 1111, etc.</li>
                        <li>Choose a unique and memorable PIN</li>
                      </ul>
                    </div>
                  </div>
                </div>

                {/* Security Notice */}
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <svg className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <div className="flex-1">
                      <div className="text-[12px] font-semibold font-['Poppins',sans-serif] text-yellow-800">
                        Security Notice
                      </div>
                      <p className="text-[11px] text-yellow-700 font-['Poppins',sans-serif] mt-0.5">
                        This PIN will be used for POS authentication. Keep it secure and do not share with others.
                      </p>
                    </div>
                  </div>
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
              disabled={loading || loadingData || availableEmployees.length === 0}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Granting Access...
                </>
              ) : (
                'Grant POS Access'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
