import { useCart } from '../../contexts/CartContext';
import { useAuth } from '../../contexts/AuthContext';
import { useState, useEffect } from 'react';
import { X, Award } from 'lucide-react';
import couponService from '../../services/couponService';

const formatVND = (amount) => {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND' }).format(amount);
};

export function OrderSummary() {
  const {
    cartItems,
    getCartTotal,
    appliedCoupon,
    applyCoupon,
    removeCoupon,
    getCartDiscount,
    // Omnichannel sequential discount details
    discountPercentage,
    getMembershipDiscount,
    getSubtotalAfterMember,
    deliveryType,
    getShippingFee,
    getShippingDiscount,
    getTotalAmount
  } = useCart();
  const { user } = useAuth();
  const [couponInput, setCouponInput] = useState('');
  const [availableCoupons, setAvailableCoupons] = useState([]);
  const [loadingCoupons, setLoadingCoupons] = useState(false);

  useEffect(() => {
    let active = true;
    const fetchCoupons = async () => {
      setLoadingCoupons(true);
      try {
        const res = await couponService.getAvailableCoupons();
        if (active) {
          setAvailableCoupons(res.data || res || []);
        }
      } catch (err) {
        console.error('Error fetching available coupons on checkout:', err);
      } finally {
        if (active) {
          setLoadingCoupons(false);
        }
      }
    };
    fetchCoupons();
    return () => { active = false; };
  }, []);

  const handleApplyCoupon = async (e) => {
    e.preventDefault();
    if (!couponInput.trim()) return;
    const success = await applyCoupon(couponInput);
    if (success) setCouponInput('');
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
      <h2 className="font-bold text-gray-800 text-xl mb-4">Order Summary</h2>

      {/* Membership discount info banner */}
      {user?.customerType && user.customerType !== 'retail' && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-100 rounded-lg flex items-start gap-2.5 text-xs text-blue-700 font-medium">
          <Award className="w-4 h-4 shrink-0 text-blue-600 mt-0.5" />
          <div>
            Your <span className="uppercase font-bold">{user.customerType}</span> membership discount will be applied automatically at checkout.
          </div>
        </div>
      )}

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
            <div className="flex flex-col min-w-0 pr-2">
              <span className="font-bold text-emerald-700 text-sm">{appliedCoupon.code}</span>
              <span className="text-emerald-600 text-xs truncate">{appliedCoupon.description}</span>
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
          <>
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

            {/* Suggested Available Vouchers */}
            {availableCoupons.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-100/50">
                <span className="block text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">Available Coupons</span>
                <div className="space-y-2 max-h-[160px] overflow-y-auto pr-1 custom-scrollbar">
                  {availableCoupons.map((coupon) => (
                    <button
                      key={coupon.id}
                      type="button"
                      onClick={() => applyCoupon(coupon.code)}
                      className="w-full text-left p-2.5 border border-dashed border-gray-200 hover:border-emerald-500 rounded-xl hover:bg-emerald-50/30 transition-all flex justify-between items-center group bg-gray-50/50"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <span className="font-bold text-[13px] text-gray-800 uppercase tracking-wide group-hover:text-emerald-700">{coupon.code}</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 font-bold shrink-0">
                            {coupon.discount_type === 'percent' ? `-${coupon.discount_value}%` : coupon.discount_type === 'freeship' ? 'Free Ship' : `-${formatVND(coupon.discount_value)}`}
                          </span>
                        </div>
                        <p className="text-[11px] text-gray-500 line-clamp-1">{coupon.description}</p>
                      </div>
                      <span className="text-[11px] font-bold text-emerald-600 border border-emerald-200 px-2.5 py-1 rounded-lg bg-white group-hover:bg-emerald-500 group-hover:text-white group-hover:border-emerald-500 transition-all ml-2 whitespace-nowrap">
                        Select
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Totals */}
      <div className="border-t border-gray-100 pt-4 space-y-2">
        <div className="flex justify-between text-sm text-gray-600">
          <span>Subtotal</span>
          <span className="font-semibold text-gray-800">{formatVND(getCartTotal())}</span>
        </div>

        {/* Membership Discount */}
        {discountPercentage > 0 && (
          <>
            <div className="flex justify-between text-sm text-emerald-600">
              <span>Membership Discount ({discountPercentage}%)</span>
              <span className="font-semibold">-{formatVND(getMembershipDiscount())}</span>
            </div>
            <div className="flex justify-between text-xs text-gray-400">
              <span>Subtotal after Member Discount</span>
              <span>{formatVND(getSubtotalAfterMember())}</span>
            </div>
          </>
        )}

        {/* Coupon Discount */}
        {appliedCoupon && getCartDiscount() > 0 && (
          <div className="flex justify-between text-sm text-emerald-600">
            <span>Coupon Discount ({appliedCoupon.code})</span>
            <span className="font-semibold">-{formatVND(getCartDiscount())}</span>
          </div>
        )}

        {/* Shipping Fee */}
        <div className="flex justify-between text-sm text-gray-600">
          <span>Shipping Fee</span>
          <span className="font-semibold text-gray-800">
            {getShippingFee() > 0 ? formatVND(getShippingFee()) : 'Free'}
          </span>
        </div>

        {/* Shipping discount */}
        {appliedCoupon && getShippingDiscount() > 0 && (
          <div className="flex justify-between text-sm text-emerald-600">
            <span>Shipping Discount</span>
            <span className="font-semibold">-{formatVND(getShippingDiscount())}</span>
          </div>
        )}

        <div className="flex justify-between pt-2 border-t border-gray-100 mt-2">
          <span className="font-bold text-lg text-gray-800">Total</span>
          <span className="font-bold text-xl text-emerald-600">{formatVND(Math.max(0, getTotalAmount()))}</span>
        </div>
      </div>
    </div>
  );
}
