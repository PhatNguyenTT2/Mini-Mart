import React, { useState, useEffect } from 'react';
import { X, Clock, User, RotateCcw, Info, ArrowRight } from 'lucide-react';
import customerDiscountSettingsService from '../../services/customerDiscountSettingsService';

export const ViewHistoryModal = ({ isOpen, onClose, onRollbackSuccess, currentEmployeeId }) => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [rollingBack, setRollingBack] = useState(null);

  useEffect(() => {
    if (isOpen) {
      loadHistory();
    }
  }, [isOpen]);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await customerDiscountSettingsService.getHistory(20);
      setHistory(response.data || []);
    } catch (err) {
      console.error('Failed to load history:', err);
      setError('Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async (versionNumber) => {
    setError('Rollback is not available in the new system. Please create a new version with the desired values instead.');
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getChangeSummary = (changes) => {
    if (!changes) return [];
    const summary = [];
    // Customer discount changes
    if (changes.retail) summary.push({ field: 'Retail', from: changes.retail.from, to: changes.retail.to, suffix: '%' });
    if (changes.wholesale) summary.push({ field: 'Wholesale', from: changes.wholesale.from, to: changes.wholesale.to, suffix: '%' });
    if (changes.vip) summary.push({ field: 'VIP', from: changes.vip.from, to: changes.vip.to, suffix: '%' });
    // Promotion changes
    if (changes.autoPromotion) summary.push({ field: 'Auto Promotion', from: changes.autoPromotion.from ? 'ON' : 'OFF', to: changes.autoPromotion.to ? 'ON' : 'OFF', suffix: '' });
    if (changes.promoDiscount) summary.push({ field: 'Promo Discount', from: changes.promoDiscount.from, to: changes.promoDiscount.to, suffix: '%' });
    if (changes.promoStartTime) summary.push({ field: 'Start Time', from: changes.promoStartTime.from, to: changes.promoStartTime.to, suffix: '' });
    return summary;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] overflow-y-auto">
      <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" aria-hidden="true">
          <div className="absolute inset-0 bg-gray-900/50 backdrop-blur-sm" onClick={onClose}></div>
        </div>

        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full relative z-10">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-xl font-semibold text-gray-900 flex items-center gap-2">
                <Clock className="w-6 h-6 text-gray-500" />
                Version History
              </h3>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
                <X className="w-6 h-6" />
              </button>
            </div>

            {error && (
              <div className="mb-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
                <Info className="w-5 h-5" />
                {error}
              </div>
            )}

            {loading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
              </div>
            ) : history.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                No history records found
              </div>
            ) : (
              <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-2">
                {history.map((version) => (
                  <div
                    key={version.version}
                    className={`bg-white rounded-xl border-2 p-5 transition-all ${version.isActive ? 'border-emerald-500 ring-4 ring-emerald-50' : 'border-gray-100 hover:border-gray-200'
                      }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-3">
                          <span className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wide ${version.isActive ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'
                            }`}>
                            v{version.version}
                          </span>
                          {version.isActive && (
                            <span className="flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full border border-emerald-100">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                              Current Active
                            </span>
                          )}
                          <span className="text-xs text-gray-400 flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatDate(version.effectiveFrom)}
                          </span>
                        </div>

                        {/* Version Changes */}
                        {version.changes && getChangeSummary(version.changes).length > 0 && (
                          <div className="mb-4 bg-gray-50 rounded-lg p-3">
                            <div className="space-y-2">
                              {getChangeSummary(version.changes).map((change, idx) => (
                                <div key={idx} className="flex items-center gap-2 text-sm">
                                  <span className="font-medium text-gray-600 w-28">{change.field}</span>
                                  <span className="text-gray-500 line-through">{change.from}{change.suffix}</span>
                                  <ArrowRight className="w-3 h-3 text-gray-400" />
                                  <span className="font-bold text-gray-900">{change.to}{change.suffix}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {/* Fallback: show current discount values if no changes detected */}
                        {(!version.changes || getChangeSummary(version.changes).length === 0) && version.discounts && (
                          <div className="mb-4 bg-gray-50 rounded-lg p-3">
                            <div className="flex items-center gap-4 text-sm text-gray-600">
                              <span>Retail: <strong>{version.discounts.retail}%</strong></span>
                              <span>Wholesale: <strong>{version.discounts.wholesale}%</strong></span>
                              <span>VIP: <strong>{version.discounts.vip}%</strong></span>
                            </div>
                          </div>
                        )}

                        <div className="flex items-center gap-4 text-xs text-gray-500">
                          {version.changedBy && (
                            <div className="flex items-center gap-1.5">
                              <div className="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center">
                                <User className="w-3 h-3 text-gray-500" />
                              </div>
                              <span>
                                {version.changedBy.fullName || version.changedBy.username || `Employee #${version.changedBy.id || version.changedBy}`}
                              </span>
                            </div>
                          )}
                          {version.changeReason && (
                            <div className="flex items-center gap-1.5 italic text-gray-400 border-l border-gray-200 pl-4">
                              <Info className="w-3 h-3" />
                              {version.changeReason}
                            </div>
                          )}
                        </div>
                      </div>

                      {!version.isActive && (
                        <button
                          onClick={() => handleRollback(version.version)}
                          disabled={rollingBack === version.version}
                          className="ml-4 flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors disabled:opacity-50"
                        >
                          {rollingBack === version.version ? (
                            <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                          ) : (
                            <RotateCcw className="w-4 h-4" />
                          )}
                          Rollback
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="bg-gray-50 px-4 py-3 sm:px-6 flex justify-end">
            <button
              type="button"
              className="w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 sm:ml-3 sm:w-auto sm:text-sm"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
