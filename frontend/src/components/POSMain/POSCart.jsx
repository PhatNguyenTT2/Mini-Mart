import React, { useState, useEffect, useRef } from 'react';
import { POSCustomerSelector } from './POSCustomerSelector';

export const POSCart = ({
  holdLoading,
  cart,
  onUpdateQuantity,
  onRemoveItem,
  onClearCart,
  onCheckout,
  onHoldOrder,
  onOpenHeldOrders,
  totals,
  // Customer selector props
  selectedCustomer,
  onCustomerChange,
  customerDiscounts,
  lastAddedId
}) => {
  const [highlightedId, setHighlightedId] = useState(null);
  const highlightTimerRef = useRef(null);
  const cartEndRef = useRef(null);

  // Flash highlight when new item is added
  useEffect(() => {
    if (lastAddedId) {
      setHighlightedId(lastAddedId);
      // Auto-scroll to show the item
      setTimeout(() => {
        const el = document.getElementById(`cart-item-${lastAddedId}`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 50);
      // Clear highlight after 800ms
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
      highlightTimerRef.current = setTimeout(() => setHighlightedId(null), 800);
    }
    return () => {
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
    };
  }, [lastAddedId]);
  const formatVND = (amount) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount);
  };

  return (
    <div className="w-96 bg-white shadow-2xl flex flex-col">
      {/* Cart Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[18px] font-bold font-['Poppins',sans-serif] text-gray-900">
            Current Order
          </h2>
          <div className="flex items-center gap-2">
            {cart.length > 0 && (
              <button
                id="pos-clear-cart-btn"
                onClick={onClearCart}
                className="text-[12px] font-medium font-['Poppins',sans-serif] text-red-600 hover:text-red-700 flex items-center gap-1"
                title="Ctrl+Delete"
              >
                <span>Clear All</span>
                <span className="text-[10px] opacity-70">(Ctrl+Del)</span>
              </button>
            )}
          </div>
        </div>
        <p className="text-[13px] font-['Poppins',sans-serif] text-gray-500">
          {cart.reduce((sum, item) => sum + item.quantity, 0)} item{cart.reduce((sum, item) => sum + item.quantity, 0) !== 1 ? 's' : ''}
        </p>
      </div>

      {/* Held Orders Button */}
      <div className="p-4 border-b border-gray-200">
        <button
          onClick={onOpenHeldOrders}
          className="w-full py-3 bg-amber-500 hover:bg-amber-600 text-white rounded-lg font-semibold transition-colors flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>Held Orders</span>
          <span className="text-[12px] font-normal opacity-75">(F4)</span>
        </button>
      </div>

      {/* Customer Selector */}
      <div className="p-4 border-b border-gray-200">
        <POSCustomerSelector
          selectedCustomer={selectedCustomer}
          onCustomerChange={onCustomerChange}
          customerDiscounts={customerDiscounts}
        />
      </div>

      {/* Cart Items */}
      <div className="flex-1 overflow-y-auto p-4">
        {cart.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-400">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" className="mb-3">
              <circle cx="9" cy="21" r="1" stroke="currentColor" strokeWidth="2" />
              <circle cx="20" cy="21" r="1" stroke="currentColor" strokeWidth="2" />
              <path d="M1 1h4l2.68 13.39a2 2 0 002 1.61h9.72a2 2 0 002-1.61L23 6H6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <p className="text-[14px] font-['Poppins',sans-serif]">
              Cart is empty
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {cart.map(item => (
              <div
                key={item.id}
                id={`cart-item-${item.id}`}
                className={`rounded-lg p-3 transition-all duration-300 ${highlightedId === item.id
                  ? 'bg-emerald-100 ring-2 ring-emerald-400 scale-[1.02]'
                  : 'bg-gray-50'
                  }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 pr-2">
                    <h3 className="text-[13px] font-semibold font-['Poppins',sans-serif] text-gray-900 line-clamp-2">
                      {item.name}
                    </h3>
                    <p className="text-[10px] font-['Poppins',sans-serif] text-gray-500 mt-0.5">
                      {item.productCode}
                      {/* Show batch code for fresh products */}
                      {item.batch && (
                        <span className="ml-2 px-1.5 py-0.5 bg-orange-100 text-orange-700 rounded text-[9px] font-semibold">
                          {item.batch.batchCode}
                        </span>
                      )}
                    </p>
                  </div>
                  <button
                    onClick={() => onRemoveItem(item.id)}
                    className="text-red-500 hover:text-red-700 flex-shrink-0"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                      <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => onUpdateQuantity(item.id, item.quantity - 1)}
                      className="w-8 h-8 bg-white rounded border border-gray-300 hover:bg-gray-100 flex items-center justify-center transition-colors"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                        <path d="M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      </svg>
                    </button>
                    <input
                      type="number"
                      min="1"
                      value={item.quantity}
                      onChange={(e) => {
                        const newQty = parseInt(e.target.value) || 1;
                        if (newQty >= 1) {
                          onUpdateQuantity(item.id, newQty);
                        }
                      }}
                      onFocus={(e) => e.target.select()}
                      className="w-16 h-8 text-center text-[14px] font-semibold font-['Poppins',sans-serif] border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                    />
                    <button
                      onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
                      className="w-8 h-8 bg-white rounded border border-gray-300 hover:bg-gray-100 flex items-center justify-center transition-colors"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                        <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                      </svg>
                    </button>
                  </div>

                  <div className="text-right">
                    {/* Check if item has discount (batch with discount or product with discount) */}
                    {(() => {
                      const hasDiscount = item.batch?.discountPercentage > 0 || item.discountPercentage > 0;
                      const basePrice = item.batch?.unitPrice || item.basePrice || item.price;
                      const discountPercent = item.batch?.discountPercentage || item.discountPercentage || 0;

                      if (hasDiscount) {
                        return (
                          <>
                            <div className="flex items-center justify-end gap-1 mb-0.5">
                              <span className="text-[10px] font-['Poppins',sans-serif] text-gray-400 line-through">
                                {formatVND(basePrice)}
                              </span>
                              <span className="text-[9px] font-bold font-['Poppins',sans-serif] px-1 py-0.5 bg-red-100 text-red-600 rounded">
                                -{discountPercent}%
                              </span>
                            </div>
                            <p className="text-[11px] font-['Poppins',sans-serif] text-emerald-600 font-semibold">
                              {formatVND(item.price)} each
                            </p>
                            <p className="text-[15px] font-bold font-['Poppins',sans-serif] text-emerald-600">
                              {formatVND(item.price * item.quantity)}
                            </p>
                          </>
                        );
                      } else {
                        return (
                          <>
                            <p className="text-[11px] font-['Poppins',sans-serif] text-gray-500">
                              {formatVND(item.price)} each
                            </p>
                            <p className="text-[15px] font-bold font-['Poppins',sans-serif] text-emerald-600">
                              {formatVND(item.price * item.quantity)}
                            </p>
                          </>
                        );
                      }
                    })()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Cart Footer - Totals & Checkout */}
      {cart.length > 0 && (
        <div className="border-t border-gray-200 p-4 space-y-3">
          <div className="space-y-2">
            <div className="flex justify-between text-[13px] font-['Poppins',sans-serif]">
              <span className="text-gray-600">Subtotal:</span>
              <span className="font-semibold">
                {formatVND(totals.subtotal)}
              </span>
            </div>
            {totals.discount > 0 && (
              <div className="flex justify-between text-[13px] font-['Poppins',sans-serif]">
                <span className="text-gray-600">
                  Discount ({totals.discountPercentage}%):
                </span>
                <span className="font-semibold text-green-600">
                  -{formatVND(totals.discount)}
                </span>
              </div>
            )}
            {totals.shippingFee > 0 && (
              <div className="flex justify-between text-[13px] font-['Poppins',sans-serif]">
                <span className="text-gray-600">Shipping:</span>
                <span className="font-semibold">
                  {formatVND(totals.shippingFee)}
                </span>
              </div>
            )}
            <div className="flex justify-between text-[18px] font-bold font-['Poppins',sans-serif] pt-2 border-t border-gray-200">
              <span className="text-gray-900">Total:</span>
              <span className="text-emerald-600">
                {formatVND(totals.total)}
              </span>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              id="pos-hold-order-btn"
              onClick={onHoldOrder}
              disabled={holdLoading}
              className={`flex-1 py-4 text-white rounded-lg text-[16px] font-bold font-['Poppins',sans-serif] transition-colors flex items-center justify-center gap-2 ${holdLoading ? 'bg-amber-400 cursor-not-allowed' : 'bg-amber-500 hover:bg-amber-600'
                }`}
              title="Save order as draft to process later"
            >
              {holdLoading ? (
                <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              ) : (
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01" />
                </svg>
              )}
              <span>{holdLoading ? 'Saving...' : 'Hold'}</span>
              {!holdLoading && <span className="text-[12px] font-normal opacity-75">(F8)</span>}
            </button>
            <button
              id="pos-checkout-btn"
              onClick={onCheckout}
              className="flex-1 py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-[16px] font-bold font-['Poppins',sans-serif] transition-colors flex items-center justify-center gap-2"
            >
              <span>Payment</span>
              <span className="text-[12px] font-normal opacity-75">(F9)</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
