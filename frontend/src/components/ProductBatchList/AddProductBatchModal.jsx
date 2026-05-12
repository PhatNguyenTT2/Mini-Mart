import React, { useState, useEffect } from 'react';
import productBatchService from '../../services/productBatchService';

export const AddProductBatchModal = ({ isOpen, onClose, onSuccess, productId }) => {
  const [formData, setFormData] = useState({
    costPrice: '',
    unitPrice: '',
    quantity: '',
    promotionApplied: 'none',
    discountPercentage: '0',
    mfgDate: '',
    expiryDate: '',
    status: 'active',
    notes: ''
  });

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setFormData({
        costPrice: '',
        unitPrice: '',
        quantity: '',
        promotionApplied: 'none',
        discountPercentage: '0',
        mfgDate: '',
        expiryDate: '',
        status: 'active',
        notes: ''
      });
      setErrors({});
      setApiError('');
    }
  }, [isOpen]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.costPrice || parseFloat(formData.costPrice) < 0) {
      newErrors.costPrice = 'Cost price is required and must be non-negative';
    }

    if (!formData.unitPrice || parseFloat(formData.unitPrice) < 0) {
      newErrors.unitPrice = 'Unit price is required and must be non-negative';
    }

    if (!formData.quantity || parseInt(formData.quantity) < 0) {
      newErrors.quantity = 'Quantity is required and must be non-negative';
    }

    if (formData.promotionApplied === 'discount') {
      const discount = parseFloat(formData.discountPercentage);
      if (discount < 0 || discount > 100) {
        newErrors.discountPercentage = 'Discount must be between 0 and 100';
      }
    }

    if (formData.mfgDate && formData.expiryDate) {
      if (new Date(formData.mfgDate) > new Date(formData.expiryDate)) {
        newErrors.expiryDate = 'Expiry date must be after manufacturing date';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
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

    setLoading(true);

    try {
      const batchData = {
        product: productId,
        costPrice: parseFloat(formData.costPrice),
        unitPrice: parseFloat(formData.unitPrice),
        quantity: parseInt(formData.quantity),
        promotionApplied: formData.promotionApplied,
        discountPercentage: parseFloat(formData.discountPercentage),
        status: formData.status
      };

      if (formData.mfgDate) {
        batchData.mfgDate = formData.mfgDate;
      }
      if (formData.expiryDate) {
        batchData.expiryDate = formData.expiryDate;
      }
      if (formData.notes.trim()) {
        batchData.notes = formData.notes.trim();
      }

      await productBatchService.createBatch(batchData);
      onSuccess && onSuccess();
      onClose();
    } catch (err) {
      console.error('Error creating batch:', err);
      setApiError(
        err.response?.data?.error?.message ||
        err.message ||
        'Failed to create batch'
      );
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
            Create New Batch
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
          {apiError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
              {apiError}
            </div>
          )}

          {/* Cost Price & Unit Price */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Cost Price (VND) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="costPrice"
                value={formData.costPrice}
                onChange={handleChange}
                step="0.01"
                min="0"
                placeholder="Enter cost price"
                className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.costPrice ? 'border-red-500' : 'border-gray-300'
                  }`}
                disabled={loading}
              />
              {errors.costPrice && (
                <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">{errors.costPrice}</p>
              )}
            </div>

            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Unit Price (VND) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                name="unitPrice"
                value={formData.unitPrice}
                onChange={handleChange}
                step="0.01"
                min="0"
                placeholder="Enter unit price"
                className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.unitPrice ? 'border-red-500' : 'border-gray-300'
                  }`}
                disabled={loading}
              />
              {errors.unitPrice && (
                <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">{errors.unitPrice}</p>
              )}
            </div>
          </div>

          {/* Quantity */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Quantity <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              name="quantity"
              value={formData.quantity}
              onChange={handleChange}
              min="0"
              placeholder="Enter quantity"
              className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.quantity ? 'border-red-500' : 'border-gray-300'
                }`}
              disabled={loading}
            />
            {errors.quantity && (
              <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">{errors.quantity}</p>
            )}
          </div>

          {/* Promotion & Discount */}
          <div className="grid grid-cols-2 gap-4">
            <div>
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
                <option value="buy1get1">Buy 1 Get 1</option>
              </select>
            </div>

            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Discount (%)
              </label>
              <input
                type="number"
                name="discountPercentage"
                value={formData.discountPercentage}
                onChange={handleChange}
                step="0.01"
                min="0"
                max="100"
                placeholder="0"
                disabled={loading || formData.promotionApplied !== 'discount'}
                className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.discountPercentage ? 'border-red-500' : 'border-gray-300'
                  } ${formData.promotionApplied !== 'discount' ? 'bg-gray-100' : ''}`}
              />
              {errors.discountPercentage && (
                <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">{errors.discountPercentage}</p>
              )}
            </div>
          </div>

          {/* MFG Date & Expiry Date */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Manufacturing Date
              </label>
              <input
                type="date"
                name="mfgDate"
                value={formData.mfgDate}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
                disabled={loading}
              />
            </div>

            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Expiry Date
              </label>
              <input
                type="date"
                name="expiryDate"
                value={formData.expiryDate}
                onChange={handleChange}
                className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.expiryDate ? 'border-red-500' : 'border-gray-300'
                  }`}
                disabled={loading}
              />
              {errors.expiryDate && (
                <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">{errors.expiryDate}</p>
              )}
            </div>
          </div>

          {/* Status */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Status
            </label>
            <select
              name="status"
              value={formData.status}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
              disabled={loading}
            >
              <option value="active">Active</option>
              <option value="expired">Expired</option>
            </select>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Notes (Optional)
            </label>
            <textarea
              name="notes"
              value={formData.notes}
              onChange={handleChange}
              rows={3}
              maxLength={500}
              placeholder="Enter notes..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
              disabled={loading}
            />
            <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
              {formData.notes.length}/500
            </p>
          </div>

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
                  Creating...
                </>
              ) : (
                'Create Batch'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
