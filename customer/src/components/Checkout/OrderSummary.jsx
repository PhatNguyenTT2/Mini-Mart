import { useCart } from '../../contexts/CartContext';
import { useState } from 'react';
import { X } from 'lucide-react';

const formatVND = (amount) => {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND' }).format(amount);
};

export function OrderSummary() {
  const { cartItems, getCartTotal, appliedCoupon, applyCoupon, removeCoupon, getCartDiscount } = useCart();
  const [couponInput, setCouponInput] = useState('');

  const handleApplyCoupon = (e) => {
    e.preventDefault();
    if (!couponInput.trim()) return;
    const success = applyCoupon(couponInput);
    if (success) setCouponInput('');
  };
  
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
      <h2 className="font-bold text-gray-800 text-xl mb-4">Order Summary</h2>
      
      {/* Items List */}
      <div className="space-y-4 mb-6">
        {cartItems.map((item) => (
          <div key={item.id} className="flex items-center gap-4">
            <img src={item.image} alt={item.name} className="w-12 h-12 object-contain border border-gray-200 rounded" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-gray-800 line-clamp-1">{item.name}</h4>
              <p className="text-xs text-gray-500">Qty: {item.quantity}</p>
            </div>
            <span className="text-sm font-bold text-emerald-600">{formatVND(item.price * item.quantity)}</span>
          </div>
        ))}
      </div>

      {/* Coupon Section */}
      <div className="mb-6 pt-6 border-t border-gray-100">
        <h3 className="font-bold text-gray-800 text-sm mb-3">Discount Coupon</h3>
        {appliedCoupon ? (
          <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-lg p-3">
            <div className="flex flex-col">
              <span className="font-bold text-emerald-700 text-sm">{appliedCoupon.code}</span>
              <span className="text-emerald-600 text-xs">{appliedCoupon.description}</span>
            </div>
            <button
              type="button"
              onClick={removeCoupon}
              className="text-emerald-500 hover:text-red-500 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        ) : (
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Enter code..."
              value={couponInput}
              onChange={(e) => setCouponInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleApplyCoupon(e)}
              className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 uppercase"
            />
            <button
              type="button"
              onClick={handleApplyCoupon}
              disabled={!couponInput.trim()}
              className="bg-gray-800 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors disabled:opacity-50"
            >
              Apply
            </button>
          </div>
        )}
      </div>

      {/* Totals */}
      <div className="border-t border-gray-100 pt-4 space-y-2">
        <div className="flex justify-between text-sm text-gray-600">
          <span>Subtotal</span>
          <span className="font-semibold text-gray-800">{formatVND(getCartTotal())}</span>
        </div>
        <div className="flex justify-between text-sm text-gray-600">
          <span>Shipping Fee</span>
          <span className="font-semibold text-emerald-600">Free</span>
        </div>
        {appliedCoupon && (
          <div className="flex justify-between text-sm text-emerald-600">
            <span>Discount ({appliedCoupon.code})</span>
            <span className="font-semibold">-{formatVND(getCartDiscount())}</span>
          </div>
        )}
        <div className="flex justify-between pt-2 border-t border-gray-100 mt-2">
          <span className="font-bold text-lg text-gray-800">Total</span>
          <span className="font-bold text-xl text-emerald-600">{formatVND(Math.max(0, getCartTotal() - getCartDiscount()))}</span>
        </div>
      </div>
    </div>
  );
}
