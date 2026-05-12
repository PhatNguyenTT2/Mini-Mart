import React, { useState } from 'react';

export const POSPaymentModal = ({
  isOpen,
  totals,
  onClose,
  onPaymentMethodSelect,
  existingOrder // NEW: Pass existing order if loaded from held orders
}) => {
  const [selectedMethod, setSelectedMethod] = useState(null);
  const [processing, setProcessing] = useState(false);

  if (!isOpen) return null;

  // NEW: Check if this is a held order or new order
  const isHeldOrder = !!existingOrder;

  const formatVND = (amount) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount);
  };

  const handleMethodSelect = async (method) => {
    setSelectedMethod(method);
    setProcessing(true);

    try {
      // Call parent with payment method
      // Parent will handle:
      // - New order: Create order + payment atomically
      // - Held order: Update order status + create payment
      await onPaymentMethodSelect(method);

      // Modal will be closed by parent after success
    } catch (error) {
      console.error('Payment error:', error);
      // Error already shown by parent
    } finally {
      setProcessing(false);
      setSelectedMethod(null);
    }
  };

  const handleCancelConfirmation = () => {
    setSelectedMethod(null);
  };

  const getMethodLabel = (method) => {
    const labels = {
      cash: 'Cash Payment',
      card: 'Card Payment',
      bank_transfer: 'Bank Transfer'
    };
    return labels[method] || method;
  };

  const getMethodIcon = (method) => {
    switch (method) {
      case 'cash':
        return (
          <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <rect x="2" y="5" width="20" height="14" rx="2" strokeWidth="2" />
            <circle cx="12" cy="12" r="3" strokeWidth="2" />
          </svg>
        );
      case 'card':
        return (
          <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <rect x="2" y="5" width="20" height="14" rx="2" strokeWidth="2" />
            <path d="M2 10h20" strokeWidth="2" />
          </svg>
        );
      case 'bank_transfer':
        return (
          <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" strokeWidth="2" />
            <polyline points="9 22 9 12 15 12 15 22" strokeWidth="2" />
          </svg>
        );
      default:
        return null;
    }
  };

  // Show payment method selection
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <div className="mb-6">
          <h2 className="text-[20px] font-bold font-['Poppins',sans-serif] text-gray-900 mb-2">
            Select Payment Method
          </h2>

          {/* NEW: Show order info if held order */}
          {isHeldOrder && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="text-sm font-semibold text-amber-800">Held Order</span>
              </div>
              <p className="text-xs text-amber-700">
                Order: <span className="font-mono font-bold">{existingOrder.orderNumber}</span>
              </p>
              <p className="text-xs text-amber-600 mt-1">
                Payment will be created for this existing order
              </p>
            </div>
          )}

          <p className="text-[14px] font-['Poppins',sans-serif] text-gray-600 mb-2">
            Total Amount:
          </p>
          <p className="text-[32px] font-bold font-['Poppins',sans-serif] text-emerald-600">
            {formatVND(totals.total)}
          </p>
        </div>

        <div className="space-y-3 mb-6">
          <button
            onClick={() => handleMethodSelect('cash')}
            disabled={processing}
            className="w-full py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[15px] font-semibold font-['Poppins',sans-serif] transition-colors flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {processing && selectedMethod === 'cash' ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {isHeldOrder ? 'Creating Payment...' : 'Creating Order...'}
              </>
            ) : (
              <>
                {getMethodIcon('cash')}
                Cash Payment
              </>
            )}
          </button>

          <button
            onClick={() => handleMethodSelect('card')}
            disabled={processing}
            className="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-[15px] font-semibold font-['Poppins',sans-serif] transition-colors flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {processing && selectedMethod === 'card' ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {isHeldOrder ? 'Creating Payment...' : 'Creating Order...'}
              </>
            ) : (
              <>
                {getMethodIcon('card')}
                Card Payment
              </>
            )}
          </button>

          <button
            onClick={() => handleMethodSelect('bank_transfer')}
            disabled={processing}
            className="w-full py-4 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-[15px] font-semibold font-['Poppins',sans-serif] transition-colors flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {processing && selectedMethod === 'bank_transfer' ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {isHeldOrder ? 'Creating Payment...' : 'Creating Order...'}
              </>
            ) : (
              <>
                {getMethodIcon('bank_transfer')}
                Bank Transfer
              </>
            )}
          </button>
        </div>

        <button
          onClick={onClose}
          disabled={processing}
          className="w-full py-3 border-2 border-gray-300 text-gray-700 rounded-lg text-[15px] font-semibold font-['Poppins',sans-serif] hover:bg-gray-50 transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
      </div >
    </div >
  );
};