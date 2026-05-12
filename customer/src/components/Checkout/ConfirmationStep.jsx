import { useCart } from '../../contexts/CartContext';
import { useStore } from '../../contexts/StoreContext';

export const ConfirmationStep = ({ formData, paymentMethod, onEdit }) => {
  const { cartItems, getCartTotal } = useCart();
  const { selectedStore } = useStore();

  const formatVND = (amount) =>
    new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);

  return (
    <div className="bg-white rounded-2xl p-6 lg:p-8 shadow-sm border border-gray-100 mb-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-gray-800">Order Confirmation</h2>
        <button
          type="button"
          onClick={onEdit}
          className="text-sm font-semibold text-emerald-600 hover:text-emerald-700"
        >
          Edit
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Shipping Info */}
        <div>
          <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Shipping Information</h3>
          <div className="space-y-2 text-sm text-gray-700">
            <p><span className="font-medium text-gray-500 w-24 inline-block">Name:</span> {formData.fullName}</p>
            <p><span className="font-medium text-gray-500 w-24 inline-block">Phone:</span> {formData.phone}</p>
            <p><span className="font-medium text-gray-500 w-24 inline-block">Address:</span> {formData.address}</p>
            {formData.notes && (
              <p><span className="font-medium text-gray-500 w-24 inline-block">Notes:</span> {formData.notes}</p>
            )}
          </div>
        </div>

        {/* Store & Payment */}
        <div>
          <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">Other Information</h3>
          <div className="space-y-2 text-sm text-gray-700">
            <p><span className="font-medium text-gray-500 w-24 inline-block">Store:</span> {selectedStore?.name || 'Not selected'}</p>
            <p>
              <span className="font-medium text-gray-500 w-24 inline-block">Payment:</span> 
              <span className="font-semibold text-emerald-600">
                {paymentMethod === 'vnpay' ? 'Pay via VNPay' : 'Cash on Delivery (COD)'}
              </span>
            </p>
          </div>
        </div>
      </div>

      {/* Cart Summary (mini) */}
      <div className="mt-8 pt-6 border-t border-gray-100">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4">Products ({cartItems.length})</h3>
        <ul className="space-y-3">
          {cartItems.map((item) => (
            <li key={item.id} className="flex justify-between items-center text-sm">
              <div className="flex items-center gap-3">
                <span className="font-medium text-gray-800">{item.quantity}x</span>
                <span className="text-gray-600 truncate max-w-[200px] sm:max-w-xs">{item.name}</span>
              </div>
              <span className="font-medium text-gray-800">{formatVND(item.price * item.quantity)}</span>
            </li>
          ))}
        </ul>
        <div className="mt-4 pt-4 border-t border-gray-50 flex justify-between items-center">
          <span className="font-bold text-gray-800">Total</span>
          <span className="text-xl font-bold text-emerald-600">{formatVND(getCartTotal())}</span>
        </div>
      </div>
    </div>
  );
};
