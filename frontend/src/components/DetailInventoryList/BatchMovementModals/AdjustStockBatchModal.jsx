import React, { useState, useEffect } from 'react';
import { X, Package, FileText, User, AlertTriangle, Info } from 'lucide-react';
import inventoryMovementBatchService from '../../../services/inventoryMovementBatchService';
import employeeService from '../../../services/employeeService';
import authService from '../../../services/authService';

export const AdjustStockBatchModal = ({ isOpen, onClose, onSuccess, detailInventory }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [currentEmployee, setCurrentEmployee] = useState(null);
  const [formData, setFormData] = useState({
    quantity: '',
    adjustmentType: 'increase',
    targetLocation: 'onHand', // 'onHand' or 'onShelf'
    reason: '',
    performedBy: '',
    notes: ''
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      fetchEmployeeData();
      setFormData({
        quantity: '',
        adjustmentType: 'increase',
        targetLocation: 'onHand',
        reason: '',
        performedBy: '',
        notes: ''
      });
      setError(null);
    }
  }, [isOpen]);

  const fetchEmployeeData = async () => {
    try {
      setLoading(true);
      const user = authService.getUser();
      setCurrentUser(user);

      if (user?.employeeId) {
        const employeeResponse = await employeeService.getEmployeeById(user.employeeId);
        if (employeeResponse.success && employeeResponse.data) {
          const employee = employeeResponse.data.employee;
          setCurrentEmployee(employee);
          setFormData(prev => ({
            ...prev,
            performedBy: user.employeeId
          }));
        }
      }
    } catch (err) {
      console.error('Error fetching employee:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const quantity = parseInt(formData.quantity);

    if (formData.adjustmentType === 'decrease') {
      const targetQty = formData.targetLocation === 'onHand'
        ? (detailInventory?.quantityOnHand || 0)
        : (detailInventory?.quantityOnShelf || 0);

      if (quantity > targetQty) {
        const locationName = formData.targetLocation === 'onHand' ? 'On Hand' : 'On Shelf';
        setError(`Insufficient stock for decrease. ${locationName}: ${targetQty}`);
        return;
      }
    }

    setLoading(true);
    setError(null);

    try {
      const batchId = detailInventory.batchId?.id || detailInventory.batchId;
      const locationId = detailInventory.locationId || null;

      const adjustmentQty = formData.adjustmentType === 'increase' ? quantity : -quantity;

      await inventoryMovementBatchService.adjustStock({
        batchId,
        locationId,
        quantity: adjustmentQty,
        targetLocation: formData.targetLocation,
        reason: formData.reason || 'manual_adjustment'
      });

      if (onSuccess) {
        onSuccess();
      }
      onClose();
    } catch (err) {
      console.error('Error creating adjustment:', err);
      const errMsg = err.response?.data?.error?.message || err.response?.data?.error || err.message || 'Failed to record adjustment';
      setError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000] p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${formData.adjustmentType === 'increase' ? 'bg-emerald-50 text-emerald-600' : 'bg-orange-50 text-orange-600'}`}>
              <Package className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold font-['Poppins',sans-serif] text-gray-900">
                Adjust Stock
              </h2>
              <p className="text-xs text-gray-500 font-['Poppins',sans-serif]">
                Manually correct inventory levels for batch {detailInventory?.batchId?.batchCode}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1 hover:bg-gray-100 rounded-full"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <span className="font-['Poppins',sans-serif]">{error}</span>
              </div>
            )}

            {/* Batch Info Card */}
            <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <h3 className="text-sm font-medium text-blue-900 font-['Poppins',sans-serif]">Current Status</h3>
                  <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-xs text-blue-700 font-['Poppins',sans-serif]">
                    <p><span className="font-medium text-blue-800">Batch:</span> {detailInventory?.batchId?.batchCode}</p>
                    <p><span className="font-medium text-blue-800">Batch Code:</span> {detailInventory?.batchId?.batchCode}</p>
                    <p><span className="font-medium text-blue-800">Warehouse (On Hand):</span> {detailInventory?.quantityOnHand || 0} units</p>
                    <p><span className="font-medium text-blue-800">Display (On Shelf):</span> {detailInventory?.quantityOnShelf || 0} units</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Type & Location */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-1.5">
                    Adjustment Type <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.adjustmentType}
                    onChange={(e) => setFormData({ ...formData, adjustmentType: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
                  >
                    <option value="increase">Increase Stock (+)</option>
                    <option value="decrease">Decrease Stock (-)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-1.5">
                    Target Location <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.targetLocation}
                    onChange={(e) => setFormData({ ...formData, targetLocation: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
                  >
                    <option value="onHand">On Hand (Warehouse)</option>
                    <option value="onShelf">On Shelf (Display)</option>
                  </select>
                </div>
              </div>

              {/* Quantity & Date */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-1.5">
                    Quantity <span className="text-red-500">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      min="1"
                      value={formData.quantity}
                      onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all pl-10"
                      placeholder="Enter amount"
                      required
                    />
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                      <Package className="w-4 h-4" />
                    </div>
                  </div>
                  <p className="mt-1 text-xs text-gray-500 font-['Poppins',sans-serif]">
                    Available: {formData.targetLocation === 'onHand'
                      ? (detailInventory?.quantityOnHand || 0)
                      : (detailInventory?.quantityOnShelf || 0)} units
                  </p>
                </div>
              </div>
            </div>

            {/* Reason */}
            <div>
              <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-1.5">
                Reason <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.reason}
                onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
                required
              >
                <option value="">Select a reason needed</option>
                <option value="Physical Count Discrepancy">Physical Count Discrepancy</option>
                <option value="Damage">Damage</option>
                <option value="Expired">Expired</option>
                <option value="Found Missing Items">Found Missing Items</option>
                <option value="System Error Correction">System Error Correction</option>
                <option value="Quality Issue">Quality Issue</option>
                <option value="Other">Other</option>
              </select>
            </div>

            {/* Performed By & Notes */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-1.5">
                  Performed By
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={currentEmployee?.fullName || currentUser?.username || 'N/A'}
                    disabled
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm font-['Poppins',sans-serif] bg-gray-50 text-gray-500 pl-10 cursor-not-allowed"
                  />
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                    <User className="w-4 h-4" />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium font-['Poppins',sans-serif] text-gray-700 mb-1.5">
                  Notes
                </label>
                <div className="relative">
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    rows="2"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all pl-10 resize-none"
                    placeholder="Optional details..."
                  />
                  <div className="absolute left-3 top-3 text-gray-400">
                    <FileText className="w-4 h-4" />
                  </div>
                </div>
              </div>
            </div>

            {/* Footer Actions - Inside form to handle submit */}
            <div className="flex items-center justify-end gap-3 pt-6 border-t border-gray-100">
              <button
                type="button"
                onClick={onClose}
                disabled={loading}
                className="px-4 py-2 text-sm font-medium font-['Poppins',sans-serif] text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className={`px-6 py-2 text-sm font-medium font-['Poppins',sans-serif] text-white rounded-lg shadow-sm transition-all flex items-center gap-2 disabled:opacity-50 ${formData.adjustmentType === 'increase'
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : 'bg-orange-600 hover:bg-orange-700'
                  }`}
              >
                {loading ? 'Processing...' : (formData.adjustmentType === 'increase' ? 'Add Stock' : 'Remove Stock')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
