import React, { useEffect, useState } from 'react';
import detailInventoryService from '../../services/detailInventoryService';
import locationService from '../../services/locationService';

export const UpdateLocationModal = ({ isOpen, onClose, onSuccess, detailInventory }) => {
  const [formData, setFormData] = useState({
    location: ''
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [locations, setLocations] = useState([]);
  const [loadingLocations, setLoadingLocations] = useState(false);

  // Fetch available locations
  useEffect(() => {
    if (isOpen) {
      fetchLocations();
    }
  }, [isOpen]);

  const fetchLocations = async () => {
    try {
      setLoadingLocations(true);
      const data = await locationService.getAllLocations();

      // Filter active locations
      const activeLocations = Array.isArray(data)
        ? data.filter(loc => loc.isActive)
        : [];

      setLocations(activeLocations);
    } catch (err) {
      console.error('Error fetching locations:', err);
      setLocations([]);
    } finally {
      setLoadingLocations(false);
    }
  };

  // Populate form when detailInventory changes or modal opens
  useEffect(() => {
    if (isOpen && detailInventory) {
      setFormData({
        location: detailInventory.location?._id || detailInventory.location || ''
      });
      setError(null);
    }
  }, [isOpen, detailInventory]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setLoading(true);
    setError(null);

    try {
      const payload = {};

      // Only include location if it's not empty
      if (formData.location && formData.location.trim()) {
        payload.location = formData.location.trim();
      } else {
        payload.location = null; // Clear location if empty
      }

      const detailInventoryId = detailInventory.id || detailInventory._id;
      const updated = await detailInventoryService.updateDetailInventory(detailInventoryId, payload);

      if (onSuccess) onSuccess(updated);
      if (onClose) onClose();
    } catch (err) {
      console.error('Error updating detail inventory location:', err);

      // Handle duplicate location error
      let errorMessage = 'Failed to update location. Please try again.';

      if (err.response?.data?.error?.message) {
        errorMessage = err.response.data.error.message;
      } else if (err.error) {
        errorMessage = err.error;
      } else if (err.message) {
        errorMessage = err.message;
      }

      // Check for duplicate key error (MongoDB error code 11000)
      if (err.response?.status === 400 || err.response?.status === 409 ||
        errorMessage.includes('duplicate') || errorMessage.includes('E11000')) {
        errorMessage = 'This location is already assigned to another batch. Please choose a different location.';
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !detailInventory) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
              Update Batch Location
            </h2>
            <p className="text-[12px] text-gray-600 font-['Poppins',sans-serif] mt-1">
              Batch: {detailInventory.batchId?.batchCode || 'N/A'}
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
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
              {error}
            </div>
          )}

          {/* Current Stock Info */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-[10px] text-gray-500 font-['Poppins',sans-serif] uppercase mb-1">On Hand</p>
                <p className="text-[16px] font-bold font-['Poppins',sans-serif] text-gray-900">
                  {detailInventory.quantityOnHand || 0}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-gray-500 font-['Poppins',sans-serif] uppercase mb-1">On Shelf</p>
                <p className="text-[16px] font-bold font-['Poppins',sans-serif] text-emerald-600">
                  {detailInventory.quantityOnShelf || 0}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-gray-500 font-['Poppins',sans-serif] uppercase mb-1">Available</p>
                <p className="text-[16px] font-bold font-['Poppins',sans-serif] text-blue-600">
                  {detailInventory.quantityAvailable || 0}
                </p>
              </div>
            </div>
          </div>

          {/* Batch Info */}
          {detailInventory.batchId && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
              <div className="grid grid-cols-2 gap-3 text-[12px]">
                {detailInventory.batchId.expiryDate && (
                  <div>
                    <p className="text-gray-600 font-['Poppins',sans-serif] mb-1">Expiry Date</p>
                    <p className="font-semibold font-['Poppins',sans-serif] text-gray-900">
                      {new Date(detailInventory.batchId.expiryDate).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                      })}
                    </p>
                  </div>
                )}
                {detailInventory.batchId.quantity !== undefined && (
                  <div>
                    <p className="text-gray-600 font-['Poppins',sans-serif] mb-1">Batch Quantity</p>
                    <p className="font-semibold font-['Poppins',sans-serif] text-gray-900">
                      {detailInventory.batchId.quantity}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Location Dropdown */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Warehouse Location
            </label>

            {loadingLocations ? (
              <div className="flex items-center justify-center py-3">
                <svg className="animate-spin h-5 w-5 text-emerald-600" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span className="ml-2 text-[12px] text-gray-500">Loading locations...</span>
              </div>
            ) : (
              <>
                <select
                  value={formData.location}
                  onChange={(e) => handleChange('location', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                >
                  <option value="">-- No Location --</option>

                  {/* Current location if it's set and not in the list */}
                  {detailInventory?.location && !locations.find(loc => loc.id === formData.location) && (
                    <option value={detailInventory.location._id || detailInventory.location}>
                      {detailInventory.location.name || detailInventory.location} (Current - may be occupied)
                    </option>
                  )}

                  {/* Available locations */}
                  {locations
                    .filter(loc => !loc.currentBatch || loc.id === formData.location)
                    .map(loc => (
                      <option key={loc.id} value={loc.id}>
                        {loc.name} ({loc.locationCode})
                        {loc.currentBatch && loc.id === formData.location ? ' - Current' : ''}
                      </option>
                    ))}

                  {/* Separator */}
                  {locations.some(loc => loc.currentBatch && loc.id !== formData.location) && (
                    <option disabled>────── Occupied ──────</option>
                  )}

                  {/* Occupied locations (disabled) */}
                  {locations
                    .filter(loc => loc.currentBatch && loc.id !== formData.location)
                    .map(loc => (
                      <option key={loc.id} value={loc.id} disabled>
                        {loc.name} ({loc.locationCode}) - Occupied by {loc.currentBatch?.batchId?.batchCode || 'another batch'}
                      </option>
                    ))}
                </select>

                <div className="mt-2 space-y-1">
                  <p className="text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                    Select a warehouse location for this batch
                  </p>
                  <p className="text-[11px] text-emerald-600 font-['Poppins',sans-serif]">
                    {locations.filter(loc => !loc.currentBatch || loc.id === formData.location).length} available locations
                  </p>
                  {locations.length === 0 && !loadingLocations && (
                    <p className="text-[11px] text-orange-600 font-['Poppins',sans-serif]">
                      No locations found. Please create locations first.
                    </p>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Action Buttons */}
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
                'Update Location'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
