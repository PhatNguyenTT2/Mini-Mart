import { useState, useEffect } from 'react';

export const EditPOSAccessModal = ({ isOpen, onClose, employee, onSuccess }) => {
  const [formData, setFormData] = useState({
    canAccessPOS: true,
    requirePINReset: false,
    newPIN: '',
    confirmPIN: ''
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset form when modal opens/closes or employee changes
  useEffect(() => {
    if (isOpen && employee) {
      setFormData({
        canAccessPOS: employee.canAccessPOS ?? true,
        requirePINReset: false,
        newPIN: '',
        confirmPIN: ''
      });
      setErrors({});
    }
  }, [isOpen, employee]);

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

  // Validate form
  const validateForm = () => {
    const newErrors = {};

    // If require PIN reset, validate PIN
    if (formData.requirePINReset) {
      if (!formData.newPIN) {
        newErrors.newPIN = 'PIN is required';
      } else if (!/^\d{4,6}$/.test(formData.newPIN)) {
        newErrors.newPIN = 'PIN must be 4-6 digits';
      } else {
        // Check for weak PINs
        const weakPins = [
          '1234', '0000', '1111', '2222', '3333', '4444',
          '5555', '6666', '7777', '8888', '9999',
          '1212', '2323', '4321'
        ];
        if (weakPins.includes(formData.newPIN)) {
          newErrors.newPIN = 'This PIN is too common. Please choose a more secure PIN';
        }
      }

      if (!formData.confirmPIN) {
        newErrors.confirmPIN = 'Please confirm PIN';
      } else if (formData.newPIN !== formData.confirmPIN) {
        newErrors.confirmPIN = 'PINs do not match';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle input change
  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));

    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  // Handle submit
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // Prepare update data
      const updates = {
        canAccessPOS: formData.canAccessPOS,
        requirePINReset: formData.requirePINReset,
        newPIN: formData.requirePINReset ? formData.newPIN : undefined
      };

      // Call onSuccess callback with updates
      if (onSuccess) {
        await onSuccess(updates);
      }

      // Close modal
      onClose();
    } catch (error) {
      console.error('Error updating POS access:', error);
      setErrors({ submit: error.message || 'Failed to update POS access' });
    } finally {
      setIsSubmitting(false);
    }
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
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-[16px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
            Edit POS Access Settings
          </h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="px-6 py-4">
          {/* Employee Info */}
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                <span className="text-[14px] font-semibold font-['Poppins',sans-serif] text-emerald-600">
                  {employee.employee?.fullName?.charAt(0) || 'E'}
                </span>
              </div>
              <div>
                <p className="text-[14px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
                  {employee.employee?.fullName || 'N/A'}
                </p>
                <p className="text-[12px] font-normal font-['Poppins',sans-serif] text-gray-600">
                  #{employee.employee?.id}
                </p>
              </div>
            </div>
          </div>

          {/* POS Access Status */}
          <div className="mb-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                name="canAccessPOS"
                checked={formData.canAccessPOS}
                onChange={handleChange}
                className="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500"
              />
              <span className="text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529]">
                Allow POS Access
              </span>
            </label>
            <p className="text-[11px] font-normal font-['Poppins',sans-serif] text-gray-500 mt-1 ml-6">
              Enable or disable this employee's access to the POS system
            </p>
          </div>

          {/* PIN Reset Section */}
          <div className="mb-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                name="requirePINReset"
                checked={formData.requirePINReset}
                onChange={handleChange}
                className="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500"
              />
              <span className="text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529]">
                Reset PIN
              </span>
            </label>
            <p className="text-[11px] font-normal font-['Poppins',sans-serif] text-gray-500 mt-1 ml-6">
              Check this to set a new PIN for the employee
            </p>
          </div>

          {/* PIN Input Fields - Only show if requirePINReset is checked */}
          {formData.requirePINReset && (
            <div className="space-y-4 mb-4 p-4 bg-blue-50 rounded-lg border border-blue-100">
              {/* New PIN */}
              <div>
                <label className="block text-[12px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-1">
                  New PIN <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  name="newPIN"
                  value={formData.newPIN}
                  onChange={handleChange}
                  placeholder="Enter 4-6 digit PIN"
                  maxLength={6}
                  className={`w-full px-3 py-2 text-[13px] font-['Poppins',sans-serif] border ${errors.newPIN ? 'border-red-500' : 'border-gray-300'
                    } rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500`}
                />
                {errors.newPIN && (
                  <p className="text-[11px] font-normal font-['Poppins',sans-serif] text-red-500 mt-1">
                    {errors.newPIN}
                  </p>
                )}
              </div>

              {/* Confirm PIN */}
              <div>
                <label className="block text-[12px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-1">
                  Confirm PIN <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  name="confirmPIN"
                  value={formData.confirmPIN}
                  onChange={handleChange}
                  placeholder="Re-enter PIN"
                  maxLength={6}
                  className={`w-full px-3 py-2 text-[13px] font-['Poppins',sans-serif] border ${errors.confirmPIN ? 'border-red-500' : 'border-gray-300'
                    } rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500`}
                />
                {errors.confirmPIN && (
                  <p className="text-[11px] font-normal font-['Poppins',sans-serif] text-red-500 mt-1">
                    {errors.confirmPIN}
                  </p>
                )}
              </div>

              {/* PIN Guidelines */}
              <div className="bg-white p-3 rounded border border-blue-200">
                <p className="text-[11px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-2">
                  PIN Requirements:
                </p>
                <ul className="text-[10px] font-normal font-['Poppins',sans-serif] text-gray-600 space-y-1 list-disc list-inside">
                  <li>Must be 4-6 digits</li>
                  <li>Only numbers allowed</li>
                  <li>Avoid common patterns (1234, 0000, etc.)</li>
                </ul>
              </div>
            </div>
          )}

          {/* Submit Error */}
          {errors.submit && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-[12px] font-normal font-['Poppins',sans-serif] text-red-600">
                {errors.submit}
              </p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-[13px] font-medium font-['Poppins',sans-serif] text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 text-[13px] font-medium font-['Poppins',sans-serif] text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Updating...
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M13.333 2L6 9.333L2.667 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Save Changes
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
