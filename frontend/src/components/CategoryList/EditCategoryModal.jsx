import React, { useState, useEffect } from 'react';
import categoryService from '../../services/categoryService';

export const EditCategoryModal = ({ isOpen, onClose, onSuccess, category, rootCategories = [] }) => {
  const [formData, setFormData] = useState({
    name: '',
    parentId: '',
    image: '',
    description: '',
    isPerishable: false
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Pre-fill form when category changes or modal opens
  useEffect(() => {
    if (isOpen && category) {
      setFormData({
        name: category.name || '',
        parentId: category.parentId ? String(category.parentId) : '',
        image: category.image || '',
        description: category.description || '',
        isPerishable: category.isPerishable || false
      });
      setError(null);
    }
  }, [isOpen, category]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      setError('Category name is required');
      return;
    }

    if (!category?.id) {
      setError('Invalid category');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Prepare data - only include non-empty fields
      const categoryData = {
        name: formData.name.trim()
      };

      if (formData.image.trim()) {
        categoryData.image = formData.image.trim();
      } else {
        // If image is empty, explicitly set to null to remove it
        categoryData.image = null;
      }

      if (formData.description.trim()) {
        categoryData.description = formData.description.trim();
      } else {
        categoryData.description = null;
      }

      // Handle parentId: empty = root (null), otherwise set parentId
      categoryData.parentId = formData.parentId ? parseInt(formData.parentId) : null;

      categoryData.isPerishable = formData.isPerishable;

      const response = await categoryService.updateCategory(category.id, categoryData);

      if (onSuccess) {
        onSuccess(response);
      }
      onClose();
    } catch (err) {
      console.error('Error updating category:', err);
      setError(err.response?.data?.error?.message || err.message || 'Failed to update category. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  if (!isOpen || !category) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Edit Category
            </h2>
            <p className="text-[12px] text-gray-500 font-['Poppins',sans-serif] mt-1">
              Category ID: {category.id}
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
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
              {error}
            </div>
          )}

          {/* Category Name */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Category Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="Enter category name"
              required
              maxLength={100}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
              Maximum 100 characters
            </p>
          </div>

          {/* Parent Category */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Parent Category
            </label>
            <select
              value={formData.parentId}
              onChange={(e) => handleChange('parentId', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
            >
              <option value="">— Root Category (No Parent) —</option>
              {rootCategories
                .filter(cat => cat.id !== category?.id)
                .map(cat => (
                  <option key={cat.id} value={cat.id}>{cat.name}</option>
                ))}
            </select>
            <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
              Set to root or assign under an existing root category.
            </p>
          </div>

          {/* Image URL */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Image URL (Optional)
            </label>
            <input
              type="url"
              value={formData.image}
              onChange={(e) => handleChange('image', e.target.value)}
              placeholder="https://example.com/image.jpg"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
              Enter the full URL of the category image. Leave empty to remove image.
            </p>

            {/* Image Preview */}
            {formData.image && (
              <div className="mt-3">
                <p className="text-[12px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                  Preview:
                </p>
                <div className="flex items-start gap-3">
                  <img
                    src={formData.image}
                    alt="Preview"
                    className="w-32 h-32 object-cover rounded-lg border border-gray-200"
                    onError={(e) => {
                      e.target.onerror = null;
                      e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128"%3E%3Crect width="128" height="128" fill="%23f3f4f6"/%3E%3Ctext x="64" y="64" text-anchor="middle" dy=".3em" fill="%23ef4444" font-family="sans-serif" font-size="12"%3EInvalid URL%3C/text%3E%3C/svg%3E';
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => handleChange('image', '')}
                    className="px-3 py-1.5 text-[12px] text-red-600 border border-red-300 rounded-lg hover:bg-red-50 font-['Poppins',sans-serif] font-medium"
                  >
                    Remove Image
                  </button>
                </div>
              </div>
            )}

            {/* Show current image if exists but form is empty */}
            {!formData.image && category.image && (
              <div className="mt-3 bg-gray-50 border border-gray-200 rounded-lg p-3">
                <p className="text-[12px] text-gray-600 font-['Poppins',sans-serif] mb-2">
                  Current image will be removed when you save
                </p>
                <img
                  src={category.image}
                  alt="Current"
                  className="w-32 h-32 object-cover rounded-lg border border-gray-300 opacity-50"
                />
              </div>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Description (Optional)
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder="Enter category description"
              rows={4}
              maxLength={500}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
            />
            <div className="flex items-center justify-between mt-1">
              <p className="text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                Maximum 500 characters. Leave empty to remove description.
              </p>
              <p className="text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                {formData.description.length}/500
              </p>
            </div>
          </div>

          {/* Perishable Toggle */}
          <div className="flex items-center justify-between p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <div>
              <label htmlFor="editIsPerishable" className="text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] cursor-pointer">
                Perishable Category
              </label>
              <p className="text-[11px] text-gray-500 font-['Poppins',sans-serif] mt-1">
                Products in this category will be targeted by auto-promotion for expiring items.
              </p>
            </div>
            <label className="relative inline-block w-11 h-6 cursor-pointer">
              <input
                type="checkbox"
                id="editIsPerishable"
                className="peer sr-only"
                checked={formData.isPerishable}
                onChange={(e) => handleChange('isPerishable', e.target.checked)}
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-amber-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-amber-500"></div>
            </label>
          </div>

          {/* Metadata Info */}
          {category.createdAt && (
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <h4 className="text-[13px] font-semibold font-['Poppins',sans-serif] text-[#212529] mb-2">
                Metadata
              </h4>
              <div className="space-y-1 text-[12px] font-['Poppins',sans-serif] text-gray-600">
                <div className="flex justify-between">
                  <span>Product Count:</span>
                  <span className="font-medium text-gray-900">{category.productCount ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Created:</span>
                  <span className="font-medium text-gray-900">
                    {new Date(category.createdAt).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric'
                    })}
                  </span>
                </div>
                {category.updatedAt && (
                  <div className="flex justify-between">
                    <span>Last Updated:</span>
                    <span className="font-medium text-gray-900">
                      {new Date(category.updatedAt).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Actions */}
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
                  Updating...
                </>
              ) : (
                'Update Category'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
