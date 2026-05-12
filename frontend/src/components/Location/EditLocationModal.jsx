import React, { useState, useEffect } from 'react';
import { X } from 'lucide-react';

export const EditLocationModal = ({ isOpen, onClose, onSuccess, location }) => {
  const [formData, setFormData] = useState({
    name: '',
    maxCapacity: 100,
    isActive: true
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (location && isOpen) {
      console.log('EditLocationModal opened with location:', location);
      setFormData({
        name: location.name || '',
        maxCapacity: location.maxCapacity || 100,
        isActive: location.isActive !== undefined ? location.isActive : true
      });
      setError('');
    }
  }, [location, isOpen]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      setError('Location name is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const locationService = (await import('../../services/locationService')).default;
      const result = await locationService.updateLocation(location.id, formData);

      console.log('Location updated successfully:', result);
      alert('Location updated successfully!');

      if (onSuccess) onSuccess();
      if (onClose) onClose();
    } catch (err) {
      console.error('Error updating location:', err);
      const errorMessage = err.response?.data?.error || 'Failed to update location';
      setError(errorMessage);
      alert('Error: ' + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError('');
  };

  if (!isOpen || !location) return null;

  const hasInventory = (location.inventoryItemCount || 0) > 0;
  const itemCount = location.inventoryItemCount || 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[100]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-[20px] font-semibold text-gray-900 font-['Poppins',sans-serif]">
              Edit Location
            </h2>
            <p className="text-[12px] text-gray-500 mt-1">
              {location.name}
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {/* Occupied Warning */}
          {hasInventory && (
            <div className="mb-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
              <p className="text-sm text-orange-700 font-medium">
                This location has {itemCount} inventory item{itemCount > 1 ? 's' : ''}
              </p>
              <p className="text-xs text-orange-600 mt-1">
                Max capacity: {location.maxCapacity || 100} units
              </p>
            </div>
          )}

          {/* Location Name */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Location Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="e.g., A-01-R05-S03, KỆ-A1, VT-001"
              disabled={loading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 text-sm uppercase"
            />
            <p className="mt-1 text-xs text-gray-500">
              Will be auto-converted to uppercase
            </p>
          </div>

          {/* Max Capacity */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Capacity <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              value={formData.maxCapacity}
              onChange={(e) => handleChange('maxCapacity', parseInt(e.target.value) || 100)}
              min="1"
              disabled={loading}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 text-sm"
            />
            <p className="mt-1 text-xs text-gray-500">
              Maximum quantity this location can hold
            </p>
          </div>

          {/* Is Active */}
          <div className="mb-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.isActive}
                onChange={(e) => handleChange('isActive', e.target.checked)}
                disabled={loading}
                className="w-4 h-4 text-emerald-600 border-gray-300 rounded focus:ring-emerald-500"
              />
              <span className="text-sm text-gray-700">Active location</span>
            </label>
            {!formData.isActive && hasInventory && (
              <p className="mt-1 text-xs text-orange-600">
                Warning: Deactivating will prevent new items, but {itemCount} item{itemCount > 1 ? 's' : ''} remain{itemCount === 1 ? 's' : ''}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-white bg-emerald-500 rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
