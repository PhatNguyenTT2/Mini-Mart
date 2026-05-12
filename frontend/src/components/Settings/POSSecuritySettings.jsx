import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import { ShieldAlert, Timer, RotateCcw, Save, AlertCircle } from 'lucide-react';

export const POSSecuritySettings = () => {
  const [security, setSecurity] = useState({
    maxFailedAttempts: 5,
    lockDurationMinutes: 15
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [reason, setReason] = useState('');

  // Load current settings on mount
  useEffect(() => {
    loadSecurity();
  }, []);

  const loadSecurity = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await settingsService.getPOSSecurity();
      setSecurity(response.data);
    } catch (err) {
      setError(err.error?.message || 'Failed to load POS security settings');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    const numValue = parseInt(value);
    if (!isNaN(numValue)) {
      setSecurity(prev => ({
        ...prev,
        [field]: numValue
      }));
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      const validation = settingsService.validatePOSSecurity(security);
      if (!validation.valid) {
        setError(validation.errors.join(', '));
        return;
      }

      if (!reason.trim()) {
        setError('Please provide a reason for the change');
        return;
      }

      await settingsService.updatePOSSecurity(security, reason);

      setSuccess('POS security settings updated successfully!');
      setReason('');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err.response?.data?.error?.message || err.error?.message || 'Failed to update settings');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset POS security to default values?')) return;
    try {
      setError(null);
      setSuccess(null);
      const response = await settingsService.resetPOSSecurity();
      if (response.success && response.data) {
        setSecurity(response.data);
        setSuccess('Settings reset to default values!');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError('Failed to reset settings');
      }
    } catch (err) {
      console.error('Error resetting POS security:', err);
      setError(err.response?.data?.error?.message || err.message || 'Failed to reset settings');
    }
  };

  const SecurityCard = ({ title, field, icon: Icon, color, description, min, max, unit }) => (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-100 p-6 relative overflow-hidden group hover:shadow-md transition-shadow h-full flex flex-col`}>
      <div className={`absolute top-0 right-0 w-24 h-24 bg-${color}-50 rounded-bl-full -mr-4 -mt-4 transition-transform group-hover:scale-110`}></div>
      <div className="relative z-10 flex flex-col flex-1">
        <div className={`w-12 h-12 rounded-lg bg-${color}-100 flex items-center justify-center mb-4 text-${color}-600`}>
          <Icon className="w-6 h-6" />
        </div>

        <h3 className="text-lg font-semibold text-gray-900 mb-1">{title}</h3>
        <p className="text-sm text-gray-500 mb-6 flex-1">{description}</p>

        <div className="flex items-end gap-3 mt-auto">
          <div className="flex-1">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">
              Value
            </label>
            <div className="relative">
              <input
                type="number"
                min={min}
                max={max}
                value={security[field]}
                onChange={(e) => handleChange(field, e.target.value)}
                className="w-full pl-4 pr-16 py-3 bg-gray-50 border border-gray-200 rounded-lg text-xl font-bold text-gray-900 focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
              />
              <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 font-bold pointer-events-none text-sm uppercase">
                {unit}
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
      <div>
        <h2 className="text-2xl font-bold text-gray-900 font-['Poppins',sans-serif]">
          POS Security Configuration
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Configure security settings for POS PIN authentication and access control
        </p>
      </div>

      {(error || success) && (
        <div className={`p-4 rounded-lg flex items-center gap-3 ${error ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-green-50 text-green-700 border border-green-100'
          }`}>
          {error ? <AlertCircle className="w-5 h-5" /> : <Save className="w-5 h-5" />}
          <span className="font-medium">{error || success}</span>
        </div>
      )}

      {/* Settings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SecurityCard
          title="Max Failed Attempts"
          field="maxFailedAttempts"
          icon={ShieldAlert}
          color="red"
          description="The maximum number of incorrect PIN attempts allowed before the account is temporarily locked to prevent brute force attacks."
          min={1}
          max={10}
          unit="Attempts"
        />
        <SecurityCard
          title="Lockout Duration"
          field="lockDurationMinutes"
          icon={Timer}
          color="amber"
          description="How long the account remains locked after exceeding the maximum failed attempts. Set 0 to disable auto-unlock."
          min={1}
          max={1440}
          unit="Minutes"
        />
      </div>

      {/* Action Footer */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="mb-4">
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Reason for Change (Required)
          </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g., Security policy update..."
            className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all"
          />
          <p className="text-xs text-gray-500 mt-1">This will be recorded in the audit history.</p>
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
    </div>
  );
};

export default POSSecuritySettings;
