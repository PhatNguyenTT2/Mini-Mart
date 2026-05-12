import React, { useState, useEffect } from 'react';
import locationService from '../../services/locationService';

/**
 * ReceiveBatchInfoForm
 * Form để nhập thông tin batch khi nhận hàng từ Purchase Order
 * Tạo batch mới với manufacturing date, expiry date từ bao bì sản phẩm
 */
export const ReceiveBatchInfoForm = ({
  poDetail,
  onSubmit,
  onCancel,
  loading = false
}) => {
  const [formData, setFormData] = useState({
    quantityReceived: poDetail?.quantity || '',
    mfgDate: '',
    expiryDate: '',
    location: '', // LocationMaster ID (optional)
    notes: ''
  });

  const [errors, setErrors] = useState({});
  const [locations, setLocations] = useState([]);
  const [loadingLocations, setLoadingLocations] = useState(false);

  // Fetch locations on mount
  useEffect(() => {
    const fetchLocations = async () => {
      try {
        setLoadingLocations(true);
        const response = await locationService.getAllLocations();

        // Extract locations array from response
        const locationsList = response.success && response.data
          ? (response.data.locations || response.data)
          : (Array.isArray(response) ? response : []);

        // Filter active locations only
        const activeLocations = locationsList.filter(loc => loc.isActive !== false);
        setLocations(activeLocations);
      } catch (error) {
        console.error('Error fetching locations:', error);
        setLocations([]);
      } finally {
        setLoadingLocations(false);
      }
    };

    fetchLocations();
  }, []);

  // Reset form when poDetail changes
  useEffect(() => {
    if (poDetail) {
      setFormData({
        quantityReceived: poDetail.quantity || '',
        mfgDate: '',
        expiryDate: '',
        location: '',
        notes: ''
      });
      setErrors({});
    }
  }, [poDetail]);

  const validateForm = () => {
    const newErrors = {};

    // Quantity validation
    const receivedQty = parseInt(formData.quantityReceived);
    const orderedQty = poDetail?.quantity || 0;

    if (!formData.quantityReceived || receivedQty <= 0) {
      newErrors.quantityReceived = 'Quantity received is required and must be greater than 0';
    } else if (receivedQty > orderedQty) {
      newErrors.quantityReceived = `Cannot receive more than ordered quantity (${orderedQty})`;
    }

    // Manufacturing date validation
    if (!formData.mfgDate) {
      newErrors.mfgDate = 'Manufacturing date is required';
    }
    // REMOVED: mfgDate future check - Allow future dates for perishable goods ordered before production

    // Expiry date validation
    if (!formData.expiryDate) {
      newErrors.expiryDate = 'Expiry date is required';
    } else if (formData.mfgDate) {
      const mfg = new Date(formData.mfgDate);
      const exp = new Date(formData.expiryDate);

      if (exp <= mfg) {
        newErrors.expiryDate = 'Expiry date must be after manufacturing date';
      }

      const today = new Date();
      today.setHours(0, 0, 0, 0);
      if (exp <= today) {
        newErrors.expiryDate = 'Expiry date must be in the future';
      }
    }

    // Location validation - Optional, no validation needed
    // Location can be assigned later if not selected during receiving

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

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    onSubmit({
      ...formData,
      quantityReceived: parseInt(formData.quantityReceived),
      poDetail: poDetail
    });
  };

  if (!poDetail) return null;

  const orderedQty = poDetail.quantity || 0;
  const costPrice = poDetail.costPrice || 0;
  const totalCost = orderedQty * costPrice;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Product Info Header */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
        <div className="flex items-start gap-4">
          {poDetail.product?.image && (
            <img
              src={poDetail.product.image}
              alt={poDetail.product?.name}
              className="w-16 h-16 object-cover rounded-lg"
            />
          )}
          <div className="flex-1">
            <h4 className="text-[14px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              {poDetail.product?.name || 'Product'}
            </h4>
            <div className="mt-2 grid grid-cols-3 gap-4 text-[12px] font-['Poppins',sans-serif]">
              <div>
                <span className="text-gray-600">Ordered:</span>
                <span className="ml-2 font-semibold text-emerald-700">{orderedQty} units</span>
              </div>
              <div>
                <span className="text-gray-600">Cost Price:</span>
                <span className="ml-2 font-semibold text-emerald-700">
                  {costPrice.toLocaleString('vi-VN')} đ
                </span>
              </div>
              <div>
                <span className="text-gray-600">Total Cost:</span>
                <span className="ml-2 font-semibold text-emerald-700">
                  {totalCost.toLocaleString('vi-VN')} đ
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quantity Received */}
      <div>
        <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
          Quantity Received <span className="text-red-500">*</span>
        </label>
        <div className="relative">
          <input
            type="number"
            name="quantityReceived"
            value={formData.quantityReceived}
            onChange={handleChange}
            min="1"
            max={orderedQty}
            placeholder={`Max: ${orderedQty} units`}
            className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.quantityReceived ? 'border-red-500' : 'border-gray-300'
              }`}
            disabled={loading}
          />
          {formData.quantityReceived && (
            <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-[11px] text-gray-500">
              {((parseInt(formData.quantityReceived) / orderedQty) * 100).toFixed(0)}%
            </div>
          )}
        </div>
        {errors.quantityReceived && (
          <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">
            {errors.quantityReceived}
          </p>
        )}
        {formData.quantityReceived && parseInt(formData.quantityReceived) < orderedQty && (
          <p className="mt-1 text-[11px] text-orange-600 font-['Poppins',sans-serif]">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline mr-1 align-text-bottom text-orange-500"><path d="M8 5.5V8.5M8 10.5H8.01M3.07 14H12.93C14.07 14 14.78 12.77 14.21 11.79L9.28 3.15C8.71 2.17 7.29 2.17 6.72 3.15L1.79 11.79C1.22 12.77 1.93 14 3.07 14Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>Receiving partial quantity. Remaining: {orderedQty - parseInt(formData.quantityReceived)} units
          </p>
        )}
      </div>
      {/* Manufacturing Date & Expiry Date */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
            Manufacturing Date <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            name="mfgDate"
            value={formData.mfgDate}
            onChange={handleChange}
            className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.mfgDate ? 'border-red-500' : 'border-gray-300'
              }`}
            disabled={loading}
          />
          {errors.mfgDate && (
            <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">
              {errors.mfgDate}
            </p>
          )}
        </div>

        <div>
          <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
            Expiry Date <span className="text-red-500">*</span>
          </label>
          <input
            type="date"
            name="expiryDate"
            value={formData.expiryDate}
            onChange={handleChange}
            min={formData.mfgDate || new Date().toISOString().split('T')[0]}
            className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.expiryDate ? 'border-red-500' : 'border-gray-300'
              }`}
            disabled={loading}
          />
          {errors.expiryDate && (
            <p className="mt-1 text-[11px] text-red-600 font-['Poppins',sans-serif]">
              {errors.expiryDate}
            </p>
          )}
          {formData.mfgDate && formData.expiryDate && !errors.expiryDate && (
            <p className="mt-1 text-[11px] text-emerald-600 font-['Poppins',sans-serif]">
              Shelf life: {Math.ceil((new Date(formData.expiryDate) - new Date(formData.mfgDate)) / (1000 * 60 * 60 * 24))} days
            </p>
          )}
        </div>
      </div>

      {/* Warehouse Location - Optional */}
      <div>
        <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
          Warehouse Location <span className="text-gray-400 font-normal">(Optional)</span>
        </label>
        <select
          name="location"
          value={formData.location}
          onChange={handleChange}
          className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 ${errors.location ? 'border-red-500' : 'border-gray-300'
            }`}
          disabled={loading || loadingLocations}
        >
          <option value="">-- Assign later --</option>
          {locations.map((loc) => (
            <option key={loc._id || loc.id} value={loc._id || loc.id}>
              {loc.locationCode} - {loc.name}
            </option>
          ))}
        </select>
        {loadingLocations && (
          <p className="mt-1 text-[11px] text-gray-500 font-['Poppins',sans-serif]">
            Loading locations...
          </p>
        )}
        {!loadingLocations && locations.length === 0 && (
          <p className="mt-1 text-[11px] text-orange-600 font-['Poppins',sans-serif]">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline mr-1 align-text-bottom text-orange-500"><path d="M8 5.5V8.5M8 10.5H8.01M3.07 14H12.93C14.07 14 14.78 12.77 14.21 11.79L9.28 3.15C8.71 2.17 7.29 2.17 6.72 3.15L1.79 11.79C1.22 12.77 1.93 14 3.07 14Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>No active locations available. You can assign location later.
          </p>
        )}
        {formData.location && (() => {
          const selectedLoc = locations.find(loc => (loc._id || loc.id) === formData.location);
          if (selectedLoc) {
            return (
              <p className="mt-1 text-[11px] text-emerald-600 font-['Poppins',sans-serif]">
                Selected: {selectedLoc.locationCode} - {selectedLoc.name}
              </p>
            );
          }
          return null;
        })()}
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
          placeholder="e.g., Package condition, temperature, special handling..."
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
          onClick={onCancel}
          disabled={loading}
          className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50 flex items-center gap-2 transition-colors"
        >
          {loading ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="none"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Receiving...
            </>
          ) : (
            <>
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path
                  d="M8 12V4M8 4L5 7M8 4L11 7"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="M2 12H14"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Receive Stock
            </>
          )}
        </button>
      </div>
    </form>
  );
};