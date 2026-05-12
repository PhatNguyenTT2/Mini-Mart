import React, { useState } from 'react';
import customerService from '../../services/customerService';

export const AddCustomerModal = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    phone: '',
    address: '',
    dateOfBirth: '',
    gender: '',
    customerType: 'retail'
  });

  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Reset form when modal closes
  React.useEffect(() => {
    if (!isOpen) {
      setFormData({
        fullName: '',
        email: '',
        phone: '',
        address: '',
        dateOfBirth: '',
        gender: '',
        customerType: 'retail'
      });
      setErrors({});
    }
  }, [isOpen]);

  // Handle input change
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  // Validate form
  const validateForm = () => {
    const newErrors = {};

    // Full Name - required
    if (!formData.fullName.trim()) {
      newErrors.fullName = 'Full name is required';
    } else if (formData.fullName.trim().length < 2) {
      newErrors.fullName = 'Full name must be at least 2 characters';
    }

    // Email - optional but must be valid if provided
    if (formData.email.trim()) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.email)) {
        newErrors.email = 'Invalid email format';
      }
    }

    // Phone - required
    if (!formData.phone.trim()) {
      newErrors.phone = 'Phone number is required';
    } else {
      const phoneRegex = /^[0-9]{10,15}$/;
      if (!phoneRegex.test(formData.phone.replace(/[\s\-()]/g, ''))) {
        newErrors.phone = 'Phone must be 10-15 digits';
      }
    }

    // Date of Birth - optional but must be in past if provided
    if (formData.dateOfBirth) {
      const dob = new Date(formData.dateOfBirth);
      const today = new Date();
      if (dob >= today) {
        newErrors.dateOfBirth = 'Date of birth must be in the past';
      }
    }

    // Gender - required
    if (!formData.gender) {
      newErrors.gender = 'Gender is required';
    }

    // Customer Type - required
    if (!formData.customerType) {
      newErrors.customerType = 'Customer type is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle submit
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      // Prepare data for API
      const customerData = {
        fullName: formData.fullName.trim(),
        phone: formData.phone.trim().replace(/[\s\-()]/g, ''), // Remove spaces, dashes, parentheses
        gender: formData.gender.toLowerCase(), // Ensure lowercase for enum validation
        customerType: formData.customerType.toLowerCase() // Ensure lowercase for enum validation
      };

      // Add optional fields if provided
      if (formData.email.trim()) {
        customerData.email = formData.email.trim().toLowerCase();
      }
      if (formData.address.trim()) {
        customerData.address = formData.address.trim();
      }
      if (formData.dateOfBirth) {
        customerData.dateOfBirth = formData.dateOfBirth;
      }


      await customerService.createCustomer(customerData);

      // Success
      if (onSuccess) {
        onSuccess();
      }
      onClose();
    } catch (error) {
      console.error('Error creating customer:', error);

      // Handle specific error cases
      if (error.response?.data?.error) {
        const errorData = error.response.data.error;
        const errorMessage = typeof errorData === 'string' ? errorData : errorData.message;
        const errorCode = typeof errorData === 'object' ? errorData.code : null;

        // Check for duplicate email
        if (errorCode === 'DUPLICATE_EMAIL' || (errorMessage && errorMessage.toLowerCase().includes('email'))) {
          setErrors(prev => ({
            ...prev,
            email: 'This email is already registered'
          }));
        } else {
          setErrors(prev => ({
            ...prev,
            submit: errorMessage || 'Failed to create customer'
          }));
        }
      } else {
        setErrors(prev => ({
          ...prev,
          submit: 'Failed to create customer. Please try again.'
        }));
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-semibold font-['Poppins',sans-serif] text-gray-900">
            Add New Customer
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={isSubmitting}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Submit Error */}
          {errors.submit && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600 font-['Poppins',sans-serif]">{errors.submit}</p>
            </div>
          )}

          {/* Full Name - Required */}
          <div>
            <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-2">
              Full Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              name="fullName"
              value={formData.fullName}
              onChange={handleChange}
              className={`w-full px-3 py-2 border ${errors.fullName ? 'border-red-300' : 'border-gray-300'} rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-['Poppins',sans-serif] text-sm`}
              placeholder="Enter full name"
              disabled={isSubmitting}
            />
            {errors.fullName && (
              <p className="mt-1 text-xs text-red-600 font-['Poppins',sans-serif]">{errors.fullName}</p>
            )}
          </div>

          {/* Email - Optional */}
          <div>
            <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-2">
              Email
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className={`w-full px-3 py-2 border ${errors.email ? 'border-red-300' : 'border-gray-300'} rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-['Poppins',sans-serif] text-sm`}
              placeholder="customer@example.com"
              disabled={isSubmitting}
            />
            {errors.email && (
              <p className="mt-1 text-xs text-red-600 font-['Poppins',sans-serif]">{errors.email}</p>
            )}
          </div>

          {/* Phone - Required */}
          <div>
            <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-2">
              Phone Number <span className="text-red-500">*</span>
            </label>
            <input
              type="tel"
              name="phone"
              value={formData.phone}
              onChange={handleChange}
              className={`w-full px-3 py-2 border ${errors.phone ? 'border-red-300' : 'border-gray-300'} rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-['Poppins',sans-serif] text-sm`}
              placeholder="0123456789"
              disabled={isSubmitting}
            />
            {errors.phone && (
              <p className="mt-1 text-xs text-red-600 font-['Poppins',sans-serif]">{errors.phone}</p>
            )}
          </div>

          {/* Address - Optional */}
          <div>
            <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-2">
              Address
            </label>
            <textarea
              name="address"
              value={formData.address}
              onChange={handleChange}
              rows={2}
              className={`w-full px-3 py-2 border ${errors.address ? 'border-red-300' : 'border-gray-300'} rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-['Poppins',sans-serif] text-sm resize-none`}
              placeholder="Enter full address"
              disabled={isSubmitting}
            />
            {errors.address && (
              <p className="mt-1 text-xs text-red-600 font-['Poppins',sans-serif]">{errors.address}</p>
            )}
          </div>

          {/* Date of Birth - Optional */}
          <div>
            <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-2">
              Date of Birth
            </label>
            <input
              type="date"
              name="dateOfBirth"
              value={formData.dateOfBirth}
              onChange={handleChange}
              max={new Date().toISOString().split('T')[0]}
              className={`w-full px-3 py-2 border ${errors.dateOfBirth ? 'border-red-300' : 'border-gray-300'} rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-['Poppins',sans-serif] text-sm`}
              disabled={isSubmitting}
            />
            {errors.dateOfBirth && (
              <p className="mt-1 text-xs text-red-600 font-['Poppins',sans-serif]">{errors.dateOfBirth}</p>
            )}
          </div>

          {/* Gender - Required */}
          <div>
            <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-2">
              Gender <span className="text-red-500">*</span>
            </label>
            <select
              name="gender"
              value={formData.gender}
              onChange={handleChange}
              className={`w-full px-3 py-2 border ${errors.gender ? 'border-red-300' : 'border-gray-300'} rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-['Poppins',sans-serif] text-sm`}
              disabled={isSubmitting}
            >
              <option value="">Select gender</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
            {errors.gender && (
              <p className="mt-1 text-xs text-red-600 font-['Poppins',sans-serif]">{errors.gender}</p>
            )}
          </div>

          {/* Customer Type - Required */}
          <div>
            <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-2">
              Customer Type <span className="text-red-500">*</span>
            </label>
            <select
              name="customerType"
              value={formData.customerType}
              onChange={handleChange}
              className={`w-full px-3 py-2 border ${errors.customerType ? 'border-red-300' : 'border-gray-300'} rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-['Poppins',sans-serif] text-sm`}
              disabled={isSubmitting}
            >
              <option value="guest">Guest</option>
              <option value="retail">Retail</option>
              <option value="wholesale">Wholesale</option>
              <option value="vip">VIP</option>
            </select>
            {errors.customerType && (
              <p className="mt-1 text-xs text-red-600 font-['Poppins',sans-serif]">{errors.customerType}</p>
            )}
          </div>

          {/* Total Spent - Read Only */}
          <div>
            <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-2">
              Total Spent
            </label>
            <input
              type="text"
              value="₫0"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 font-['Poppins',sans-serif] text-sm text-gray-500"
              disabled
              readOnly
            />
            <p className="mt-1 text-xs text-gray-500 font-['Poppins',sans-serif]">
              New customers start with ₫0 total spent
            </p>
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium font-['Poppins',sans-serif] text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium font-['Poppins',sans-serif] text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Creating...' : 'Create Customer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
