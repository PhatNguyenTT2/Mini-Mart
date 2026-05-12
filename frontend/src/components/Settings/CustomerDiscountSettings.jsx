import React, { useState, useEffect } from 'react';
import customerDiscountSettingsService from '../../services/customerDiscountSettingsService';
import { ShoppingBag, Truck, Crown, History, RotateCcw, Save, AlertCircle } from 'lucide-react';
import { ViewHistoryModal } from './ViewHistoryModal';

export const CustomerDiscountSettings = () => {
  const [discounts, setDiscounts] = useState({
    retail: 10,
    wholesale: 15,
    vip: 20
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  const [reason, setReason] = useState('');

  useEffect(() => {
    loadDiscounts();
  }, []);

  const loadDiscounts = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await customerDiscountSettingsService.getActiveDiscounts();
      setDiscounts(response.data);
    } catch (err) {
      setError(err.error?.message || 'Failed to load discount settings');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (type, value) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue) && numValue >= 0 && numValue <= 100) {
      setDiscounts(prev => ({
        ...prev,
        [type]: numValue
      }));
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      if (!reason.trim()) {
        setError('Please provide a reason for the change');
        return;
      }

      await customerDiscountSettingsService.updateDiscounts({
        retail: discounts.retail,
        wholesale: discounts.wholesale,
        vip: discounts.vip,
        reason: reason
      });

      setSuccess('Discount settings updated successfully!');
      setReason('');
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to update settings');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Are you sure you want to reset to default values?')) {
      return;
    }

    try {
      const response = await customerDiscountSettingsService.resetToDefaults({
        reason: 'Reset to default values'
      });

      if (response.success && response.data) {
        setDiscounts({
          retail: response.data.discounts.retail,
          wholesale: response.data.discounts.wholesale,
          vip: response.data.discounts.vip
        });
        setSuccess('Settings reset to default values!');
        setTimeout(() => setSuccess(null), 3000);
      }
    } catch (err) {
      setError('Failed to reset settings');
    }
  };

  const handleRollbackSuccess = (version) => {
    loadDiscounts();
    setSuccess(`Successfully rolled back to version ${version}!`);
    setTimeout(() => setSuccess(null), 3000);
  };

  const DiscountCard = ({ title, type, icon: Icon, color, description }) => (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-100 p-6 relative overflow-hidden group hover:shadow-md transition-shadow`}>
      <div className={`absolute top-0 right-0 w-24 h-24 bg-${color}-50 rounded-bl-full -mr-4 -mt-4 transition-transform group-hover:scale-110`}></div>
      <div className="relative z-10">
        <div className={`w-12 h-12 rounded-lg bg-${color}-100 flex items-center justify-center mb-4 text-${color}-600`}>
          <Icon className="w-6 h-6" />
        </div>

        <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
        <p className="text-sm text-gray-500 mb-6 min-h-[40px]">{description}</p>

        <div className="flex items-end gap-3">
          <div className="flex-1">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Discount Rate
            </label>
            <div className="relative">
              <input
                type="number"
                min="0"
                max="100"
                step="0.5"
                value={discounts[type]}
                onChange={(e) => handleChange(type, e.target.value)}
                className="w-full pl-4 pr-12 py-3 bg-gray-50 border border-gray-200 rounded-lg text-xl font-bold text-gray-900 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
              />
              <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 font-bold pointer-events-none">
                %
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 font-['Poppins',sans-serif]">
            Discount Configuration
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Manage default discount rates for different customer tiers
          </p>
        </div>
        <button
          onClick={() => setShowHistoryModal(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
        >
          <History className="w-4 h-4" />
          View History
        </button>
      </div>

      {(error || success) && (
        <div className={`p-4 rounded-lg flex items-center gap-3 ${error ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-green-50 text-green-700 border border-green-100'
          }`}>
          {error ? <AlertCircle className="w-5 h-5" /> : <Save className="w-5 h-5" />}
          <span className="font-medium">{error || success}</span>
        </div>
      )}

      {/* Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <DiscountCard
          title="Retail Customers"
          type="retail"
          icon={ShoppingBag}
          color="blue"
          description="Standard discount rate applied to walk-in and regular retail customers."
        />
        <DiscountCard
          title="Wholesale Partners"
          type="wholesale"
          icon={Truck}
          color="orange"
          description="Special rates for bulk buyers and wholesale partners."
        />
        <DiscountCard
          title="VIP Members"
          type="vip"
          icon={Crown}
          color="purple"
          description="Exclusive rates for loyal customers and VIP program members."
        />
      </div>

      {/* Action Footer */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="mb-6">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Reason for Change (Required)
          </label>
          <div className="relative">
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g., Q3 Promotion, Market Adjustment..."
              className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">
            This reason will be recorded in the version history for auditing purposes.
          </p>
        </div>

        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Reset Defaults
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2.5 text-sm font-medium text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Changes
          </button>
        </div>
      </div>

      <ViewHistoryModal
        isOpen={showHistoryModal}
        onClose={() => setShowHistoryModal(false)}
        onRollbackSuccess={handleRollbackSuccess}
      />
    </div>
  );
};

export default CustomerDiscountSettings;
