import React, { useState, useEffect } from 'react';
import productBatchService from '../../services/productBatchService';

export const BulkDiscountModal = ({ isOpen, onClose, onSuccess, productId, productName }) => {
  const [formData, setFormData] = useState({
    promotionApplied: 'none',
    discountPercentage: 0
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      // Reset form when modal opens
      setFormData({
        promotionApplied: 'none',
        discountPercentage: 0
      });
      setError(null);
    }
  }, [isOpen]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'discountPercentage' ? parseFloat(value) || 0 : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (formData.promotionApplied === 'discount' && (formData.discountPercentage <= 0 || formData.discountPercentage > 100)) {
      setError('Discount percentage must be between 0 and 100');
      return;
    }

    try {
      setLoading(true);

      // Get all batches for this product
      const response = await productBatchService.getBatchesByProduct(productId, { limit: 1000 });

      if (!response.success || !response.data.batches) {
        throw new Error('Failed to fetch product batches');
      }

      const batches = response.data.batches;
      const updatePromises = batches.map(batch =>
        productBatchService.updateBatch(batch.id, {
          promotionApplied: formData.promotionApplied,
          discountPercentage: formData.promotionApplied === 'discount' ? formData.discountPercentage : 0
        })
      );

      await Promise.all(updatePromises);

      onSuccess && onSuccess();
      onClose();
    } catch (err) {
      console.error('Error updating bulk discount:', err);
      setError(err.response?.data?.error?.message || err.message || 'Failed to update discount');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-[16px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
            Configure Bulk Discount
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            disabled={loading}
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="px-6 py-4">
          {/* Product Info */}
          <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
            <p className="text-[11px] font-medium text-blue-800 uppercase tracking-wide mb-1">
              Product
            </p>
            <p className="text-[13px] font-semibold text-blue-900">
              {productName || 'All Batches'}
            </p>
            <p className="text-[11px] text-blue-600 mt-1">
              This will apply the discount to ALL batches of this product
            </p>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-[12px] text-red-600">{error}</p>
            </div>
          )}

          {/* Promotion Type */}
          <div className="mb-4">
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Promotion Type
            </label>
            <select
              name="promotionApplied"
              value={formData.promotionApplied}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
              disabled={loading}
            >
              <option value="none">None</option>
              <option value="discount">Discount</option>
            </select>
          </div>

          {/* Discount Percentage - Show only when discount is selected */}
          {formData.promotionApplied === 'discount' && (
            <div className="mb-4">
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Discount Percentage (%)
              </label>
              <input
                type="number"
                name="discountPercentage"
                value={formData.discountPercentage}
                onChange={handleChange}
                min="0"
                max="100"
                step="0.01"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                disabled={loading}
                required
              />
              <p className="text-[11px] text-gray-500 mt-1">
                Enter a value between 0 and 100
              </p>
            </div>
          )}

          {/* Preview */}
          {formData.promotionApplied !== 'none' && (
            <div className="mb-4 p-3 bg-amber-50 rounded-lg border border-amber-200">
              <p className="text-[11px] font-medium text-amber-800 uppercase tracking-wide mb-1">
                Preview
              </p>
              <p className="text-[13px] text-amber-900">
                {formData.promotionApplied === 'discount'
                  ? `${formData.discountPercentage}% discount will be applied to all batches`
                  : 'Promotion will be applied to all batches'}
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-[13px] font-medium font-['Poppins',sans-serif] text-gray-700 hover:bg-gray-50 transition-colors"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded-lg text-[13px] font-medium font-['Poppins',sans-serif] text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? 'Applying...' : 'Apply to All Batches'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
