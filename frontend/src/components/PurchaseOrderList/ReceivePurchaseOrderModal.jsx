import React, { useState, useEffect } from 'react';
import { ReceiveBatchInfoForm } from './ReceiveBatchInfoForm';
import purchaseOrderService from '../../services/purchaseOrderService';

/**
 * ReceivePurchaseOrderModal
 * Modal để nhận hàng từ Purchase Order
 * - Fetches full PO details on open (list view doesn't include details)
 * - Cho phép nhập batch info cho từng sản phẩm
 * - Submit ALL items in one backend call → POST /purchase-orders/:id/receive
 * - Backend handles: create batches → stock in → link to PO → update status
 */
export const ReceivePurchaseOrderModal = ({
  isOpen,
  onClose,
  onSuccess,
  purchaseOrder
}) => {
  const [receivingItem, setReceivingItem] = useState(null);
  const [receivedBatchData, setReceivedBatchData] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState('');
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [poDetails, setPoDetails] = useState([]);

  // Fetch full PO details when modal opens
  useEffect(() => {
    if (!isOpen || !purchaseOrder) {
      setPoDetails([]);
      setReceivedBatchData({});
      setReceivingItem(null);
      setApiError('');
      return;
    }

    const fetchDetails = async () => {
      setLoadingDetails(true);
      try {
        const poId = purchaseOrder.id || purchaseOrder._id;
        const response = await purchaseOrderService.getPurchaseOrderById(poId);
        const fullPo = response.success ? response.data : response;
        setPoDetails(fullPo?.details || []);
      } catch (err) {
        console.error('Error fetching PO details:', err);
        setApiError('Failed to load purchase order details');
        setPoDetails([]);
      } finally {
        setLoadingDetails(false);
      }
    };

    fetchDetails();
  }, [isOpen, purchaseOrder]);

  // Handle single item batch info submission (local only, no API call)
  const handleReceiveItem = (batchData) => {
    const { poDetail, quantityReceived, mfgDate, expiryDate, location, notes } = batchData;
    const detailId = poDetail.id || poDetail._id;

    setReceivedBatchData(prev => ({
      ...prev,
      [detailId]: {
        poDetailId: detailId,
        quantity: quantityReceived,
        mfgDate,
        expiryDate,
        locationId: location || null,
        notes: notes || `Received from PO #${purchaseOrder.id}`
      }
    }));

    setReceivingItem(null);
    setApiError('');
  };

  // Remove batch data for an item (undo)
  const handleUndoItem = (detailId) => {
    setReceivedBatchData(prev => {
      const copy = { ...prev };
      delete copy[detailId];
      return copy;
    });
  };

  // Submit ALL received items to backend in one call
  const handleSubmitAll = async () => {
    const items = Object.values(receivedBatchData);
    if (items.length === 0) {
      setApiError('Please enter batch info for at least one item');
      return;
    }

    setSubmitting(true);
    setApiError('');

    try {
      const poId = purchaseOrder.id || purchaseOrder._id;
      const response = await purchaseOrderService.receivePurchaseOrderWithBatches(poId, items);

      if (response.success) {
        onSuccess && onSuccess(response.data);
        onClose();
      }
    } catch (error) {
      console.error('Error receiving purchase order:', error);
      setApiError(
        error.response?.data?.error?.message ||
        error.response?.data?.message ||
        error.message ||
        'Failed to receive purchase order'
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  const totalItems = poDetails.length;
  const receivedCount = Object.keys(receivedBatchData).length;
  const progressPercentage = totalItems > 0 ? (receivedCount / totalItems) * 100 : 0;
  const allItemsReady = totalItems > 0 && receivedCount === totalItems;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 p-6 z-10">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
                Receive Purchase Order
              </h2>
              <p className="text-[13px] text-gray-600 font-['Poppins',sans-serif] mt-1">
                #{purchaseOrder?.id} - {purchaseOrder?.supplier?.companyName}
              </p>
            </div>
            <button
              onClick={onClose}
              disabled={submitting}
              className="text-gray-400 hover:text-gray-600 disabled:opacity-50 transition-colors"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path
                  d="M18 6L6 18M6 6L18 18"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>

          {/* Step Progress */}
          <div className="mt-4 pb-2">
            <div className="flex items-center justify-center">
              {[
                { num: 1, label: 'Enter Batch Info' },
                { num: 2, label: 'Review & Submit' },
                { num: 3, label: 'Complete' }
              ].map((stepInfo, index) => {
                const currentStep = allItemsReady ? 2 : 1;
                const stepNum = stepInfo.num;

                return (
                  <div key={stepNum} className="flex items-center">
                    <div className="flex flex-col items-center">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center text-[14px] font-bold transition-all duration-300 ${stepNum < currentStep
                        ? 'bg-emerald-500 text-white'
                        : stepNum === currentStep
                          ? 'bg-blue-600 text-white ring-4 ring-blue-100'
                          : 'bg-gray-100 text-gray-400 border-2 border-gray-200'
                        }`}>
                        {stepNum < currentStep ? (
                          <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
                            <path d="M13.5 4L6 11.5L2.5 8" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        ) : (
                          stepNum
                        )}
                      </div>
                      <span className={`mt-2 text-[11px] font-medium whitespace-nowrap ${stepNum <= currentStep ? 'text-blue-600' : 'text-gray-400'
                        }`}>
                        {stepInfo.label}
                      </span>
                    </div>

                    {index < 2 && (
                      <div className="w-20 h-1 mx-3 rounded-full overflow-hidden bg-gray-200">
                        <div
                          className={`h-full transition-all duration-500 ease-out ${stepNum < currentStep ? 'bg-emerald-500' : 'bg-gray-200'
                            }`}
                          style={{ width: stepNum < currentStep ? '100%' : '0%' }}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Progress Bar */}
          {totalItems > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="relative w-12 h-12">
                    <svg className="w-12 h-12 transform -rotate-90" viewBox="0 0 48 48">
                      <circle cx="24" cy="24" r="20" stroke="#e5e7eb" strokeWidth="4" fill="none" />
                      <circle
                        cx="24" cy="24" r="20"
                        stroke={progressPercentage === 100 ? '#10b981' : '#3b82f6'}
                        strokeWidth="4" fill="none" strokeLinecap="round"
                        strokeDasharray={`${2 * Math.PI * 20}`}
                        strokeDashoffset={`${2 * Math.PI * 20 * (1 - progressPercentage / 100)}`}
                        className="transition-all duration-500 ease-out"
                      />
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className={`text-[11px] font-bold ${progressPercentage === 100 ? 'text-emerald-600' : 'text-blue-600'}`}>
                        {progressPercentage.toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-gray-800">
                      {receivedCount} of {totalItems} items ready
                    </p>
                    <p className="text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                      {totalItems - receivedCount === 0 ? 'All items ready! Click Submit to receive.' : `${totalItems - receivedCount} remaining`}
                    </p>
                  </div>
                </div>
                <div className={`px-3 py-1.5 rounded-full text-[11px] font-semibold ${progressPercentage === 100
                  ? 'bg-emerald-100 text-emerald-700'
                  : progressPercentage > 0
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-100 text-gray-600'
                  }`}>
                  {progressPercentage === 100 ? (
                    <span className="flex items-center gap-1">
                      <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                        <path d="M13.5 4L6 11.5L2.5 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      Ready
                    </span>
                  ) : progressPercentage > 0 ? 'In Progress' : 'Not Started'}
                </div>
              </div>

              {/* Segmented Progress Bar */}
              <div className="flex items-center gap-1">
                {poDetails.map((detail, index) => (
                  <div
                    key={detail.id || index}
                    className={`flex-1 h-2 rounded-full transition-all duration-300 ${receivedBatchData[detail.id]
                      ? 'bg-emerald-500'
                      : 'bg-gray-200'
                      }`}
                    title={`${detail.productName || 'Item'} - ${receivedBatchData[detail.id] ? 'Ready' : 'Pending'}`}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-6">
          {apiError && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px] mb-4">
              {apiError}
            </div>
          )}

          {loadingDetails ? (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600 mb-3"></div>
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                Loading purchase order details...
              </p>
            </div>
          ) : poDetails.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No items found in this purchase order
              </p>
            </div>
          ) : receivingItem ? (
            /* Show receiving form for selected item */
            <div>
              <button
                onClick={() => setReceivingItem(null)}
                className="flex items-center gap-2 text-[13px] text-gray-600 hover:text-gray-800 font-['Poppins',sans-serif] mb-4"
                disabled={submitting}
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M10 12L6 8L10 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                Back to item list
              </button>

              <ReceiveBatchInfoForm
                poDetail={receivingItem}
                onSubmit={handleReceiveItem}
                onCancel={() => setReceivingItem(null)}
                loading={submitting}
              />
            </div>
          ) : (
            /* Show list of items */
            <div className="space-y-3">
              {poDetails.map((detail, index) => {
                const detailId = detail.id || detail._id;
                const isReady = !!receivedBatchData[detailId];
                const batchInfo = receivedBatchData[detailId];

                return (
                  <div
                    key={detailId}
                    className={`border rounded-lg p-4 transition-all ${isReady
                      ? 'bg-emerald-50 border-emerald-200'
                      : 'bg-white border-gray-200 hover:border-emerald-300'
                      }`}
                  >
                    <div className="flex items-center gap-4">
                      <div className="flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-600">
                        {index + 1}
                      </div>

                      <div className="flex-1">
                        <h4 className="text-[14px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
                          {detail.productName || 'Product'}
                        </h4>
                        <div className="flex items-center gap-4 mt-1 text-[12px] font-['Poppins',sans-serif] text-gray-600">
                          <span>Qty: {detail.quantity}</span>
                          <span>•</span>
                          <span>Cost: {(detail.costPrice || 0).toLocaleString('vi-VN')} đ</span>
                          <span>•</span>
                          <span>Total: {(detail.totalPrice || detail.quantity * detail.costPrice || 0).toLocaleString('vi-VN')} đ</span>
                        </div>
                        {isReady && batchInfo && (
                          <div className="flex items-center gap-3 mt-1 text-[11px] text-emerald-600">
                            <span>Qty: {batchInfo.quantity}</span>
                            {batchInfo.mfgDate && <span>MFG: {batchInfo.mfgDate}</span>}
                            {batchInfo.expiryDate && <span>EXP: {batchInfo.expiryDate}</span>}
                          </div>
                        )}
                      </div>

                      {isReady ? (
                        <div className="flex items-center gap-2">
                          <div className="flex items-center gap-1 text-emerald-600">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                              <path
                                d="M7 10L9 12L13 8M19 10C19 14.9706 14.9706 19 10 19C5.02944 19 1 14.9706 1 10C1 5.02944 5.02944 1 10 1C14.9706 1 19 5.02944 19 10Z"
                                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                              />
                            </svg>
                            <span className="text-[13px] font-semibold font-['Poppins',sans-serif]">Ready</span>
                          </div>
                          <button
                            onClick={() => handleUndoItem(detailId)}
                            className="px-2 py-1 text-[11px] text-gray-500 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                            title="Remove batch info"
                          >
                            Undo
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setReceivingItem(detail)}
                          className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-medium transition-colors flex items-center gap-2"
                        >
                          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                            <path d="M8 12V4M8 4L5 7M8 4L11 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                            <path d="M2 12H14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                          Receive
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        {!receivingItem && poDetails.length > 0 && (
          <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div className="text-[13px] font-['Poppins',sans-serif] text-gray-600">
                {allItemsReady ? (
                  <span className="text-emerald-600 font-semibold">
                    All items ready! Click Submit to create batches and receive stock.
                  </span>
                ) : (
                  <span>
                    {totalItems - receivedCount} item(s) remaining
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={onClose}
                  disabled={submitting}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-white text-[13px] font-['Poppins',sans-serif] font-medium transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSubmitAll}
                  disabled={submitting || receivedCount === 0}
                  className="px-6 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg"
                >
                  {submitting ? (
                    <>
                      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Receiving...
                    </>
                  ) : (
                    <>
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                        <path d="M13.5 4L6 11.5L2.5 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      Submit & Receive ({receivedCount}/{totalItems})
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};