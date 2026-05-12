import React from 'react';
import { X, CheckCircle, XCircle, Package, Calendar, Percent, TrendingDown } from 'lucide-react';

/**
 * Modal to display promotion application results
 * Shows list of batches that received promotions
 */
export const PromotionResultModal = ({ result, onClose }) => {
  if (!result) return null;

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      return dateString;
    }
  };

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '0₫';
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const appliedBatches = result.appliedBatches || [];
  const removedBatches = result.removedBatches || [];

  return (
    <div className="fixed inset-0 z-[100] overflow-y-auto">
      <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" aria-hidden="true">
          <div className="absolute inset-0 bg-gray-900/50 backdrop-blur-sm" onClick={onClose}></div>
        </div>

        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full relative z-10">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center gap-3">
              {result.success ? (
                <CheckCircle className="w-6 h-6 text-green-600" />
              ) : (
                <XCircle className="w-6 h-6 text-red-600" />
              )}
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  Promotion Results
                </h2>
                <p className="text-sm text-gray-600 mt-1">
                  {formatDate(result.timestamp)}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Summary */}
          <div className="p-6 bg-gradient-to-r from-emerald-50 to-blue-50 border-b border-gray-200">
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <span className="text-sm font-medium text-gray-600">Applied</span>
                </div>
                <p className="text-2xl font-bold text-green-600">{result.applied || 0}</p>
                <p className="text-xs text-gray-500 mt-1">Batches promoted</p>
              </div>

              <div className="bg-white rounded-lg p-4 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <XCircle className="w-5 h-5 text-red-600" />
                  <span className="text-sm font-medium text-gray-600">Removed</span>
                </div>
                <p className="text-2xl font-bold text-red-600">{result.removed || 0}</p>
                <p className="text-xs text-gray-500 mt-1">Expired batches</p>
              </div>

              <div className="bg-white rounded-lg p-4 shadow-sm">
                <div className="flex items-center gap-2 mb-2">
                  <Package className="w-5 h-5 text-blue-600" />
                  <span className="text-sm font-medium text-gray-600">Total</span>
                </div>
                <p className="text-2xl font-bold text-blue-600">
                  {(result.applied || 0) + (result.removed || 0)}
                </p>
                <p className="text-xs text-gray-500 mt-1">Batches affected</p>
              </div>
            </div>

            {result.message && (
              <div className="mt-4 p-3 bg-white rounded-lg">
                <p className="text-sm text-gray-700">{result.message}</p>
              </div>
            )}
          </div>

          {/* Content - Scrollable */}
          <div className="flex-1 overflow-y-auto p-6">
            {/* Applied Promotions */}
            {appliedBatches.length > 0 && (
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <TrendingDown className="w-5 h-5 text-green-600" />
                  Applied Promotions ({appliedBatches.length})
                </h3>
                <div className="space-y-3">
                  {appliedBatches.map((batch, index) => (
                    <div
                      key={index}
                      className="bg-green-50 border border-green-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Package className="w-4 h-4 text-green-600" />
                            <span className="font-semibold text-gray-900">
                              {batch.batchCode}
                            </span>
                            <span className="px-2 py-1 bg-green-600 text-white text-xs rounded-full font-medium">
                              <Percent className="w-3 h-3 inline mr-1" />
                              {batch.discountPercentage}% OFF
                            </span>
                          </div>

                          <p className="text-sm text-gray-700 mb-2">
                            <strong>Product:</strong> {batch.productName || 'N/A'}
                          </p>

                          <div className="grid grid-cols-2 gap-3 text-sm">
                            <div>
                              <span className="text-gray-600">Original Price:</span>
                              <p className="font-medium text-gray-900">
                                {formatCurrency(batch.originalPrice)}
                              </p>
                            </div>
                            <div>
                              <span className="text-gray-600">Discounted Price:</span>
                              <p className="font-medium text-green-600">
                                {formatCurrency(batch.discountedPrice)}
                              </p>
                            </div>
                            <div>
                              <span className="text-gray-600">Quantity:</span>
                              <p className="font-medium text-gray-900">{batch.quantity}</p>
                            </div>
                            <div className="flex items-center gap-1">
                              <Calendar className="w-4 h-4 text-orange-600" />
                              <div>
                                <span className="text-gray-600">Expires:</span>
                                <p className="font-medium text-orange-600">
                                  {formatDate(batch.expiryDate)}
                                </p>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Removed Promotions */}
            {removedBatches.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <XCircle className="w-5 h-5 text-red-600" />
                  Removed Promotions ({removedBatches.length})
                </h3>
                <div className="space-y-3">
                  {removedBatches.map((batch, index) => (
                    <div
                      key={index}
                      className="bg-red-50 border border-red-200 rounded-lg p-4"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <Package className="w-4 h-4 text-red-600" />
                            <span className="font-semibold text-gray-900">
                              {batch.batchCode}
                            </span>
                            <span className="px-2 py-1 bg-red-600 text-white text-xs rounded-full font-medium">
                              EXPIRED
                            </span>
                          </div>

                          <p className="text-sm text-gray-700 mb-2">
                            <strong>Product:</strong> {batch.productName || 'N/A'}
                          </p>

                          <div className="flex items-center gap-1 text-sm">
                            <Calendar className="w-4 h-4 text-red-600" />
                            <span className="text-gray-600">Expired:</span>
                            <p className="font-medium text-red-600">
                              {formatDate(batch.expiryDate)}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* No results */}
            {appliedBatches.length === 0 && removedBatches.length === 0 && (
              <div className="text-center py-12">
                <Package className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-500 text-lg">No batches were affected</p>
                <p className="text-gray-400 text-sm mt-2">
                  No eligible batches found for promotion at this time
                </p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-6 border-t border-gray-200 bg-gray-50">
            <button
              onClick={onClose}
              className="w-full px-6 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
