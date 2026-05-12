import React, { useState, useEffect } from 'react';
import settingsService from '../../services/settingsService';
import { PromotionResultModal } from './PromotionResultModal';
import { Clock, Timer, Zap, Percent, Save, AlertCircle, Rocket, Calendar } from 'lucide-react';

/**
 * FreshProductPromotionSettings Component
 * 
 * Auto-promotion settings for fresh products (category='fresh')
 * - Enable/disable auto promotion for expiring fresh products
 * - Configure promotion start time each day
 * - Set discount percentage for fresh products expiring today
 */
export const FreshProductPromotionSettings = () => {
  const [settings, setSettings] = useState({
    autoPromotionEnabled: false,
    promotionStartTime: '17:00', // Default 5 PM
    discountPercentage: 20, // Default 20% off
    applyToExpiringToday: true, // Apply to batches expiring within 24 hours
    applyToExpiringTomorrow: false // Apply to batches expiring within 48 hours
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [runStatus, setRunStatus] = useState('');
  const [errors, setErrors] = useState({});
  const [successMessage, setSuccessMessage] = useState('');
  const [promotionResult, setPromotionResult] = useState(null);
  const [showResultModal, setShowResultModal] = useState(false);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setLoading(true);
    try {
      const response = await settingsService.getSalesSettings();
      const sales = response.data || response;
      setSettings({
        autoPromotionEnabled: sales.auto_promotion_enabled || false,
        promotionStartTime: sales.promotion_start_time || '18:00',
        discountPercentage: parseFloat(sales.promotion_discount_percentage) || 20,
        applyToExpiringToday: sales.apply_to_expiring_today !== false,
        applyToExpiringTomorrow: sales.apply_to_expiring_tomorrow || false
      });
    } catch (error) {
      console.error('Failed to load fresh product promotion settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const validateSettings = () => {
    const newErrors = {};

    if (settings.discountPercentage < 0 || settings.discountPercentage > 100) {
      newErrors.discountPercentage = 'Discount must be between 0% and 100%';
    }

    if (!settings.promotionStartTime) {
      newErrors.promotionStartTime = 'Promotion start time is required';
    }

    if (!settings.applyToExpiringToday && !settings.applyToExpiringTomorrow) {
      newErrors.applyTo = 'Must select at least one option (today or tomorrow)';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateSettings()) {
      return;
    }

    setSaving(true);
    setSuccessMessage('');
    setErrors({});

    try {
      await settingsService.updateSalesSettings({
        auto_promotion_enabled: settings.autoPromotionEnabled,
        promotion_start_time: settings.promotionStartTime,
        promotion_discount_percentage: settings.discountPercentage,
        apply_to_expiring_today: settings.applyToExpiringToday,
        apply_to_expiring_tomorrow: settings.applyToExpiringTomorrow
      }, 'Fresh product promotion update');

      setSuccessMessage('Fresh product promotion settings saved successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (error) {
      console.error('Failed to save settings:', error);
      setErrors({
        submit: error.response?.data?.error?.message || 'Failed to save settings'
      });
    } finally {
      setSaving(false);
    }
  };

  const handleRunNow = async () => {
    setRunning(true);
    setRunStatus('Triggering promotion...');
    setErrors({});

    try {
      const result = await settingsService.runPromotionAndWait(
        (status) => {
          if (status.status === 'pending') {
            setRunStatus('Processing batches...');
          } else if (status.status === 'completed') {
            setRunStatus('Done!');
          }
        },
        2000, // poll every 2s
        30000 // timeout after 30s
      );

      setPromotionResult(result.result || result);
      setShowResultModal(true);
    } catch (error) {
      console.error('Promotion failed:', error);
      setErrors({ submit: error.message || 'Failed to run promotion' });
    } finally {
      setRunning(false);
      setRunStatus('');
    }
  };

  const handleChange = (field, value) => {
    setSettings(prev => ({
      ...prev,
      [field]: value
    }));
    // Clear error for this field
    if (errors[field]) {
      const newErrors = { ...errors };
      delete newErrors[field];
      setErrors(newErrors);
    }
  };

  const SettingCard = ({ title, icon: Icon, color, children }) => (
    <div className={`bg-white rounded-xl shadow-sm border border-gray-100 p-6 relative overflow-hidden h-full`}>
      <div className={`absolute top-0 right-0 w-24 h-24 bg-${color}-50 rounded-bl-full -mr-4 -mt-4`}></div>
      <div className="relative z-10">
        <div className={`w-12 h-12 rounded-lg bg-${color}-100 flex items-center justify-center mb-6 text-${color}-600`}>
          <Icon className="w-6 h-6" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-6">{title}</h3>
        {children}
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-orange-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900 font-['Poppins',sans-serif]">
          Fresh Product Promotion
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Automated discount rules for fresh products nearing expiration
        </p>
      </div>

      {(successMessage || errors.submit) && (
        <div className={`p-4 rounded-lg flex items-center gap-3 ${errors.submit ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-green-50 text-green-700 border border-green-100'
          }`}>
          {errors.submit ? <AlertCircle className="w-5 h-5" /> : <Save className="w-5 h-5" />}
          <span className="font-medium">{errors.submit || successMessage}</span>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Core Settings */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <div className="flex items-start gap-4">
              <div className={`p-3 rounded-lg ${settings.autoPromotionEnabled ? 'bg-emerald-100 text-emerald-600' : 'bg-gray-100 text-gray-500'}`}>
                <Zap className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="autoPromotionEnabled" className="text-lg font-semibold text-gray-900 cursor-pointer">
                    Enable Auto-Promotion
                  </label>
                  <label className="relative inline-block w-12 h-6 transition duration-200 ease-in-out rounded-full cursor-pointer">
                    <input
                      type="checkbox"
                      id="autoPromotionEnabled"
                      className="peer sr-only"
                      checked={settings.autoPromotionEnabled}
                      onChange={(e) => handleChange('autoPromotionEnabled', e.target.checked)}
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-emerald-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                  </label>
                </div>
                <p className="text-sm text-gray-500">
                  Automatically apply discounts to fresh products based on expiry criteria.
                </p>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <SettingCard title="Schedule & Rules" icon={Clock} color="blue">
              <div className="space-y-6">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Start Time
                  </label>
                  <input
                    type="time"
                    value={settings.promotionStartTime}
                    onChange={(e) => handleChange('promotionStartTime', e.target.value)}
                    disabled={!settings.autoPromotionEnabled}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 transition-all font-semibold text-gray-900"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Target Products
                  </label>
                  <div className="space-y-3">
                    <label className={`flex items-center p-3 rounded-lg border ${settings.applyToExpiringToday && settings.autoPromotionEnabled
                      ? 'border-blue-200 bg-blue-50'
                      : 'border-gray-200 hover:bg-gray-50'
                      } transition-colors cursor-pointer`}>
                      <input
                        type="checkbox"
                        checked={settings.applyToExpiringToday}
                        onChange={(e) => handleChange('applyToExpiringToday', e.target.checked)}
                        disabled={!settings.autoPromotionEnabled}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                      />
                      <span className="ml-3 text-sm font-medium text-gray-700">Expires Today (24h)</span>
                    </label>

                    <label className={`flex items-center p-3 rounded-lg border ${settings.applyToExpiringTomorrow && settings.autoPromotionEnabled
                      ? 'border-blue-200 bg-blue-50'
                      : 'border-gray-200 hover:bg-gray-50'
                      } transition-colors cursor-pointer`}>
                      <input
                        type="checkbox"
                        checked={settings.applyToExpiringTomorrow}
                        onChange={(e) => handleChange('applyToExpiringTomorrow', e.target.checked)}
                        disabled={!settings.autoPromotionEnabled}
                        className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                      />
                      <span className="ml-3 text-sm font-medium text-gray-700">Expires Tomorrow (48h)</span>
                    </label>
                  </div>
                  {errors.applyTo && <p className="mt-1 text-xs text-red-500">{errors.applyTo}</p>}
                </div>
              </div>
            </SettingCard>

            <SettingCard title="Discount Rate" icon={Percent} color="orange">
              <div className="flex flex-col h-full justify-between">
                <div>
                  <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                    Discount Percentage
                  </label>
                  <div className="relative mb-6">
                    <input
                      type="number"
                      value={settings.discountPercentage}
                      onChange={(e) => handleChange('discountPercentage', parseFloat(e.target.value))}
                      min="0"
                      max="100"
                      disabled={!settings.autoPromotionEnabled}
                      className="w-full pl-4 pr-12 py-3 bg-gray-50 border border-gray-200 rounded-lg text-3xl font-bold text-gray-900 focus:ring-2 focus:ring-orange-500 focus:border-transparent transition-all"
                    />
                    <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 font-bold pointer-events-none text-xl">
                      %
                    </div>
                  </div>

                  <input
                    type="range"
                    value={settings.discountPercentage}
                    onChange={(e) => handleChange('discountPercentage', parseFloat(e.target.value))}
                    min="0"
                    max="100"
                    step="5"
                    disabled={!settings.autoPromotionEnabled}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-orange-600"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-2 font-medium">
                    <span>0%</span>
                    <span>50%</span>
                    <span>100%</span>
                  </div>
                </div>

                {errors.discountPercentage && <p className="mt-1 text-xs text-red-500">{errors.discountPercentage}</p>}
              </div>
            </SettingCard>
          </div>
        </div>

        {/* Preview & Actions */}
        <div className="space-y-6">
          <div className="bg-gray-900 text-white rounded-xl shadow-lg p-6 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-bl-full -mr-8 -mt-8"></div>

            <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-emerald-400" />
              Summary
            </h3>

            <div className="space-y-4 text-gray-300 text-sm">
              <div className="flex justify-between pb-3 border-b border-gray-800">
                <span>Status</span>
                <span className={`font-medium ${settings.autoPromotionEnabled ? 'text-emerald-400' : 'text-gray-500'}`}>
                  {settings.autoPromotionEnabled ? 'Active' : 'Disabled'}
                </span>
              </div>
              <div className="flex justify-between pb-3 border-b border-gray-800">
                <span>Execution Time</span>
                <span className="font-medium text-white">{settings.promotionStartTime}</span>
              </div>
              <div className="flex justify-between pb-3 border-b border-gray-800">
                <span>Discount</span>
                <span className="font-medium text-orange-400">{settings.discountPercentage}% OFF</span>
              </div>
              <div className="pt-2">
                <span className="block mb-2">Target Scope:</span>
                <div className="flex flex-wrap gap-2">
                  {settings.applyToExpiringToday && (
                    <span className="bg-gray-800 text-xs px-2 py-1 rounded border border-gray-700">Expires Today</span>
                  )}
                  {settings.applyToExpiringTomorrow && (
                    <span className="bg-gray-800 text-xs px-2 py-1 rounded border border-gray-700">Expires Tomorrow</span>
                  )}
                  {!settings.applyToExpiringToday && !settings.applyToExpiringTomorrow && (
                    <span className="text-gray-500 italic">No scope selected</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={handleRunNow}
            disabled={saving || running || !settings.autoPromotionEnabled}
            className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-blue-50 text-blue-700 font-semibold rounded-xl hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all border border-blue-100 shadow-sm"
          >
            {running ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-700"></div>
                {runStatus || 'Processing...'}
              </>
            ) : (
              <>
                <Rocket className="w-5 h-5" />
                Run Promotion Now
              </>
            )}
          </button>

          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full flex items-center justify-center gap-2 px-6 py-4 bg-emerald-600 text-white font-semibold rounded-xl hover:bg-emerald-700 shadow-lg shadow-emerald-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : null}
            Save Configuration
          </button>
        </div>
      </div>

      {showResultModal && (
        <PromotionResultModal
          result={promotionResult}
          onClose={() => {
            setShowResultModal(false);
            setPromotionResult(null);
          }}
        />
      )}
    </div>
  );
};
