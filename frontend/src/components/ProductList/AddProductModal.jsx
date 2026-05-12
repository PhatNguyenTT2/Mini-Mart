import React, { useState, useEffect } from 'react';
import productService from '../../services/productService';
import categoryService from '../../services/categoryService';

export const AddProductModal = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    name: '',
    image: '',
    category: '',
    unitPrice: '',
    vendor: '',
    isActive: true
  });

  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');

  // Fetch categories when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchCategories();
    }
  }, [isOpen]);

  const fetchCategories = async () => {
    try {
      const response = await categoryService.getAllCategories();
      if (response.success && response.data && response.data.categories) {
        setCategories(response.data.categories);
      } else if (Array.isArray(response)) {
        setCategories(response);
      }
    } catch (err) {
      console.error('Error fetching categories:', err);
      setApiError('Failed to load categories');
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Product name is required';
    } else if (formData.name.length > 255) {
      newErrors.name = 'Product name must be at most 255 characters';
    }

    if (!formData.category) {
      newErrors.category = 'Category is required';
    }

    if (!formData.unitPrice) {
      newErrors.unitPrice = 'Unit price is required';
    } else if (isNaN(formData.unitPrice) || parseFloat(formData.unitPrice) < 0) {
      newErrors.unitPrice = 'Unit price must be a non-negative number';
    }

    if (formData.vendor && formData.vendor.length > 100) {
      newErrors.vendor = 'Vendor name must be at most 100 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError('');

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      // Prepare data for API
      const productData = {
        name: formData.name.trim(),
        category: formData.category,
        unitPrice: parseFloat(formData.unitPrice),
        isActive: formData.isActive
      };

      // Only include optional fields if they have values
      if (formData.image.trim()) {
        productData.image = formData.image.trim();
      }
      if (formData.vendor.trim()) {
        productData.vendor = formData.vendor.trim();
      }

      const response = await productService.createProduct(productData);

      // Success
      onSuccess(response);
      handleClose();
    } catch (err) {
      console.error('Error creating product:', err);
      setApiError(
        err.response?.data?.error?.message ||
        err.message ||
        'Failed to create product. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({
      name: '',
      image: '',
      category: '',
      unitPrice: '',
      vendor: '',
      isActive: true
    });
    setErrors({});
    setApiError('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
            Create New Product
          </h2>
          <button
            onClick={handleClose}
            disabled={isLoading}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {apiError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
              {apiError}
            </div>
          )}

          {/* Product Name */}
          <div>
            <label htmlFor="name" className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Product Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="Enter product name"
              required
              maxLength={255}
              className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.name ? 'border-red-500' : 'border-gray-300'}`}
              disabled={isLoading}
            />
            {errors.name ? (
              <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">{errors.name}</p>
            ) : (
              <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                Maximum 255 characters
              </p>
            )}
          </div>

          {/* Category */}
          <div>
            <label htmlFor="category" className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Category <span className="text-red-500">*</span>
            </label>
            <select
              id="category"
              name="category"
              value={formData.category}
              onChange={handleChange}
              required
              className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.category ? 'border-red-500' : 'border-gray-300'}`}
              disabled={isLoading}
            >
              <option value="">Select a category</option>
              {categories.map(cat => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
            {errors.category && (
              <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">{errors.category}</p>
            )}
          </div>

          {/* Unit Price */}
          <div>
            <label htmlFor="unitPrice" className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Unit Price (VND) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              id="unitPrice"
              name="unitPrice"
              value={formData.unitPrice}
              onChange={handleChange}
              step="0.01"
              min="0"
              placeholder="Enter unit price"
              required
              className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.unitPrice ? 'border-red-500' : 'border-gray-300'}`}
              disabled={isLoading}
            />
            {errors.unitPrice && (
              <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">{errors.unitPrice}</p>
            )}
          </div>

          {/* Vendor */}
          <div>
            <label htmlFor="vendor" className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Vendor (Optional)
            </label>
            <input
              type="text"
              id="vendor"
              name="vendor"
              value={formData.vendor}
              onChange={handleChange}
              placeholder="Enter vendor name"
              maxLength={100}
              className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.vendor ? 'border-red-500' : 'border-gray-300'}`}
              disabled={isLoading}
            />
            {errors.vendor ? (
              <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">{errors.vendor}</p>
            ) : (
              <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                Maximum 100 characters
              </p>
            )}
          </div>

          {/* Image URL */}
          <div>
            <label htmlFor="image" className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Image URL (Optional)
            </label>
            <input
              type="url"
              id="image"
              name="image"
              value={formData.image}
              onChange={handleChange}
              placeholder="https://example.com/image.jpg"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
              disabled={isLoading}
            />
            <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
              Enter the full URL of the product image
            </p>

            {/* Image Preview */}
            {formData.image && (
              <div className="mt-3">
                <p className="text-[12px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                  Preview:
                </p>
                <img
                  src={formData.image}
                  alt="Preview"
                  className="w-32 h-32 object-cover rounded-lg border border-gray-200"
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128"%3E%3Crect width="128" height="128" fill="%23f3f4f6"/%3E%3Ctext x="64" y="64" text-anchor="middle" dy=".3em" fill="%23ef4444" font-family="sans-serif" font-size="12"%3EInvalid URL%3C/text%3E%3C/svg%3E';
                  }}
                />
              </div>
            )}
          </div>

          {/* Active Status */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="isActive"
              name="isActive"
              checked={formData.isActive}
              onChange={handleChange}
              className="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500"
              disabled={isLoading}
            />
            <label htmlFor="isActive" className="ml-2 text-[13px] text-gray-700 font-['Poppins',sans-serif]">
              Active
            </label>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={handleClose}
              disabled={isLoading}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Creating...
                </>
              ) : (
                'Create Product'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddProductModal;
