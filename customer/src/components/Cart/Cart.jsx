import { ShoppingCart, Plus, Minus, X, Trash2 } from 'lucide-react';
import { useCart } from '../../contexts/CartContext';
import { Link } from 'react-router-dom';
import { useState, Fragment } from 'react';
import { Dialog, Transition } from '@headlessui/react';

const formatVND = (amount) => {
  return new Intl.NumberFormat('vi-VN', {
    style: 'currency',
    currency: 'VND'
  }).format(amount);
};

export default function Cart() {
  const { 
    cartItems, 
    removeFromCart, 
    updateQuantity, 
    getCartTotal, 
    clearCart,
    appliedCoupon,
    applyCoupon,
    removeCoupon,
    getCartDiscount
  } = useCart();
  
  const [couponInput, setCouponInput] = useState('');
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);

  const handleApplyCoupon = () => {
    if (!couponInput.trim()) return;
    const success = applyCoupon(couponInput);
    if (success) setCouponInput('');
  };

  if (cartItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <ShoppingCart className="w-16 h-16 text-gray-300 mb-5" />
        <h2 className="font-bold text-gray-800 text-2xl mb-2">Your cart is empty</h2>
        <p className="text-gray-500 text-sm mb-6">
          You haven&apos;t added any products to your cart yet.
        </p>
        <Link
          to="/"
          className="bg-emerald-500 text-white font-semibold text-sm px-6 py-3 rounded-lg hover:bg-emerald-600 transition-colors no-underline"
        >
          Continue Shopping
        </Link>
      </div>
    );
  }

  return (
    <>
      <div className="max-w-7xl mx-auto px-4 lg:px-8 py-8">
      <h1 className="font-bold text-gray-800 text-2xl mb-6">Your Cart</h1>

      {/* Cart Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {/* Header */}
        <div className="hidden md:grid grid-cols-[3fr_1fr_1fr_1fr_auto] gap-4 px-6 py-3 bg-gray-50 border-b border-gray-200">
          <span className="font-bold text-gray-700 text-sm">Product</span>
          <span className="font-bold text-gray-700 text-sm text-center">Unit Price</span>
          <span className="font-bold text-gray-700 text-sm text-center">Quantity</span>
          <span className="font-bold text-gray-700 text-sm text-center">Subtotal</span>
          <span className="w-8" />
        </div>

        {/* Items */}
        {cartItems.map((item) => (
          <div key={item.id} className="grid grid-cols-1 md:grid-cols-[3fr_1fr_1fr_1fr_auto] gap-4 px-6 py-4 border-b border-gray-100 items-center">
            <div className="flex items-center gap-3">
              <img src={item.image} alt={item.name} className="w-16 h-16 object-contain rounded-lg border border-gray-200" />
              <div>
                <h3 className="font-semibold text-gray-800 text-sm leading-5">{item.name}</h3>
                <span className="text-gray-400 text-xs">{item.category}</span>
              </div>
            </div>

            <div className="text-center">
              <span className="font-bold text-emerald-600 text-sm">{formatVND(item.price)}</span>
            </div>

            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => updateQuantity(item.id, item.quantity - 1)}
                className="w-7 h-7 border border-gray-200 rounded flex items-center justify-center text-gray-600 hover:border-emerald-400 transition-colors bg-white"
              >
                <Minus className="w-3 h-3" />
              </button>
              <span className="font-bold text-gray-800 text-sm w-6 text-center">{item.quantity}</span>
              <button
                onClick={() => updateQuantity(item.id, item.quantity + 1)}
                className="w-7 h-7 border border-gray-200 rounded flex items-center justify-center text-gray-600 hover:border-emerald-400 transition-colors bg-white"
              >
                <Plus className="w-3 h-3" />
              </button>
            </div>

            <div className="text-center">
              <span className="font-bold text-emerald-600 text-sm">{formatVND(item.price * item.quantity)}</span>
            </div>

            <button
              onClick={() => removeFromCart(item.id)}
              className="w-7 h-7 flex items-center justify-center text-gray-400 hover:text-red-500 transition-colors bg-transparent border-none"
              aria-label={`Remove ${item.name}`}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="flex flex-col md:flex-row justify-between items-start mt-6 gap-6">
        <button
          onClick={() => setIsClearModalOpen(true)}
          className="flex items-center gap-2 border border-gray-200 rounded-lg px-5 py-2.5 font-semibold text-gray-700 text-sm hover:border-red-400 hover:text-red-500 transition-colors bg-white"
        >
          <Trash2 className="w-4 h-4" />
          Clear Cart
        </button>

        <div className="flex-1 w-full max-w-md">
          {/* Coupon Section */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 mb-4">
            <h3 className="font-bold text-gray-800 text-lg mb-4">Have a coupon?</h3>
            {appliedCoupon ? (
              <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-lg p-3">
                <div className="flex flex-col">
                  <span className="font-bold text-emerald-700 text-sm">{appliedCoupon.code}</span>
                  <span className="text-emerald-600 text-xs">{appliedCoupon.description}</span>
                </div>
                <button
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
                  placeholder="Enter coupon code"
                  value={couponInput}
                  onChange={(e) => setCouponInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleApplyCoupon()}
                  className="flex-1 border border-gray-200 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent uppercase"
                />
                <button
                  onClick={handleApplyCoupon}
                  disabled={!couponInput.trim()}
                  className="bg-gray-800 text-white px-5 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-700 transition-colors disabled:opacity-50"
                >
                  Apply
                </button>
              </div>
            )}
            <div className="mt-3 flex gap-2 text-xs text-gray-500">
              <span className="px-2 py-1 bg-gray-100 rounded">WELCOME10</span>
              <span className="px-2 py-1 bg-gray-100 rounded">FREESHIP50</span>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-6">
            <h3 className="font-bold text-gray-800 text-xl mb-5">Order Summary</h3>

          <div className="flex justify-between items-center py-2.5 border-b border-gray-100">
            <span className="text-gray-500 text-sm">Subtotal</span>
            <span className="font-bold text-emerald-600">{formatVND(getCartTotal())}</span>
          </div>

          <div className="flex justify-between items-center py-2.5 border-b border-gray-100">
            <span className="text-gray-500 text-sm">Shipping</span>
            <span className="font-semibold text-emerald-600 text-sm">Free</span>
          </div>

          {appliedCoupon && (
            <div className="flex justify-between items-center py-2.5 border-b border-gray-100">
              <span className="text-emerald-600 text-sm flex items-center gap-1">
                Discount ({appliedCoupon.code})
              </span>
              <span className="font-bold text-emerald-600">-{formatVND(getCartDiscount())}</span>
            </div>
          )}

          <div className="flex justify-between items-center py-3">
            <span className="font-bold text-gray-800 text-lg">Total</span>
            <span className="font-bold text-emerald-600 text-xl">{formatVND(Math.max(0, getCartTotal() - getCartDiscount()))}</span>
          </div>

          <Link 
            to="/checkout"
            className="w-full flex items-center justify-center h-12 bg-emerald-500 text-white font-bold rounded-lg hover:bg-emerald-600 transition-colors mt-3 no-underline"
          >
            Checkout
          </Link>
        </div>
      </div>
      </div>
    </div>

      {/* Clear Cart Confirmation Modal */}
      <Transition appear show={isClearModalOpen} as={Fragment}>
        <Dialog as="div" className="relative z-50" onClose={() => setIsClearModalOpen(false)}>
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="ease-in duration-200"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <div className="fixed inset-0 bg-black bg-opacity-25 backdrop-blur-sm" />
          </Transition.Child>

          <div className="fixed inset-0 overflow-y-auto">
            <div className="flex min-h-full items-center justify-center p-4 text-center">
              <Transition.Child
                as={Fragment}
                enter="ease-out duration-300"
                enterFrom="opacity-0 scale-95"
                enterTo="opacity-100 scale-100"
                leave="ease-in duration-200"
                leaveFrom="opacity-100 scale-100"
                leaveTo="opacity-0 scale-95"
              >
                <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all border border-gray-100">
                  <Dialog.Title as="h3" className="text-lg font-bold leading-6 text-gray-900 flex items-center gap-2">
                    <Trash2 className="w-5 h-5 text-red-500" />
                    Clear Shopping Cart
                  </Dialog.Title>
                  <div className="mt-4">
                    <p className="text-sm text-gray-500">
                      Are you sure you want to clear all {cartItems.length} items from your cart? This action cannot be undone.
                    </p>
                  </div>

                  <div className="mt-8 flex justify-end gap-3">
                    <button
                      type="button"
                      className="inline-flex justify-center rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
                      onClick={() => setIsClearModalOpen(false)}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="inline-flex justify-center rounded-lg border border-transparent bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 transition-colors"
                      onClick={() => {
                        clearCart();
                        setIsClearModalOpen(false);
                      }}
                    >
                      Clear All
                    </button>
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </Dialog>
      </Transition>
    </>
  );
}
