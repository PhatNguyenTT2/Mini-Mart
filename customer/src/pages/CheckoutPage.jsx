import { useState, useEffect } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useCart } from '../contexts/CartContext';
import { useStore } from '../contexts/StoreContext';
import { Header } from '../components/Header';
import Footer from '../components/Footer/Footer';
import { ShippingForm } from '../components/Checkout/ShippingForm';
import { AddressBook } from '../components/Checkout/AddressBook';
import { OrderSummary } from '../components/Checkout/OrderSummary';
import { PaymentMethodSelect } from '../components/Checkout/PaymentMethodSelect';
import { ConfirmationStep } from '../components/Checkout/ConfirmationStep';
import orderService from '../services/orderService';
import paymentService from '../services/paymentService';
import productService from '../services/productService';
import { Loader2, MapPin, CreditCard, CheckCircle2 } from 'lucide-react';

export default function CheckoutPage() {
  const [step, setStep] = useState('shipping'); // 'shipping' | 'confirm'
  const { user } = useAuth();
  const { cartItems, getCartTotal, appliedCoupon, deliveryType, getTotalAmount } = useCart();
  const { selectedStore } = useStore();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    fullName: user?.fullName || '',
    phone: user?.phone || '',
    address: user?.address || '',
    notes: ''
  });

  // Sync formData if user data is loaded asynchronously (e.g., via getMe)
  // And try to load default address from AddressBook
  useEffect(() => {
    if (user) {
      let defaultAddress = null;
      try {
        const saved = localStorage.getItem(`saved_addresses_${user.id || user.customerId}`);
        if (saved) {
          const addresses = JSON.parse(saved);
          defaultAddress = addresses.find(a => a.isDefault) || addresses[0];
        }
      } catch {
        // ignore
      }

      setFormData(prev => ({
        ...prev,
        fullName: prev.fullName || defaultAddress?.fullName || user.fullName || '',
        phone: prev.phone || defaultAddress?.phone || user.phone || '',
        address: prev.address || defaultAddress?.address || user.address || ''
      }));
    }
  }, [user]);

  const [paymentMethod, setPaymentMethod] = useState('vnpay');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // If no user, redirect to login
  if (!user) {
    return <Navigate to="/login?redirect=/checkout" replace />;
  }

  // If cart empty, redirect to cart
  if (cartItems.length === 0) {
    return <Navigate to="/cart" replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.fullName || !formData.phone || !formData.address) {
      setError('Please fill in all shipping information');
      return;
    }

    if (step === 'shipping') {
      setStep('confirm');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    setLoading(true);
    setError('');

    try {
      // 0. Inventory Validation (Cart inventory real-time stock check)
      try {
        const invRes = await productService.getStoreInventorySummary(selectedStore.id);
        const inventoryMap = {};
        if (invRes?.data) {
          invRes.data.forEach(inv => {
            inventoryMap[inv.productId] = inv.quantityOnShelf;
          });
        }

        for (const item of cartItems) {
          const available = inventoryMap[item.id] || 0;
          if (item.quantity > available) {
            setError(`Product "${item.name}" only has ${available} items left at the store. Please update your cart.`);
            setStep('shipping');
            setLoading(false);
            return;
          }
        }
      } catch (err) {
        console.error('Inventory validation failed', err);
        // Continue if it fails to fetch so we don't block sales completely
      }

      // 1. Create Draft Order
      const orderRes = await orderService.createOrder({
        items: cartItems,
        customerId: user.customerId || user.id,
        deliveryType: deliveryType || 'delivery',
        shippingAddress: `${formData.address} - Phone: ${formData.phone} - Name: ${formData.fullName}`,
        shippingFee: deliveryType === 'delivery' ? 30000 : 0,
        notes: formData.notes,
        storeId: selectedStore.id,
        couponCode: appliedCoupon?.code || null
      });

      const order = orderRes.data?.order || orderRes.order || orderRes;
      const orderId = order.id || order.orderId;

      // Save Address logic
      try {
        const userId = user.id || user.customerId;
        const saved = localStorage.getItem(`saved_addresses_${userId}`);
        let addresses = saved ? JSON.parse(saved) : [];
        const isDuplicate = addresses.some(a => a.address === formData.address && a.phone === formData.phone);

        if (!isDuplicate) {
          // Add new address
          const newAddress = {
            fullName: formData.fullName,
            phone: formData.phone,
            address: formData.address,
            isDefault: addresses.length === 0 // Make default if it's the first one
          };
          addresses.push(newAddress);
          if (addresses.length > 5) addresses.shift(); // keep max 5
          localStorage.setItem(`saved_addresses_${userId}`, JSON.stringify(addresses));
        }
      } catch (e) {
        console.error('Failed to save address', e);
      }

      const orderTotal = order.total !== undefined ? order.total : getTotalAmount();

      if (paymentMethod === 'cod') {
        // COD: Create payment record to trigger Saga
        try {
          await paymentService.createDirectPayment({
            orderId,
            amount: orderTotal,
            items: order.details || cartItems.map(item => ({
              batchId: null,
              quantity: item.quantity
            })),
            storeId: selectedStore.id
          });
          navigate(`/order-status/${orderId}?payment=cod`, { replace: true });
        } catch (paymentErr) {
          console.error('COD payment creation failed:', paymentErr);
          // Graceful degradation: order exists, navigate with error flag
          navigate(`/order-status/${orderId}?payment=pending`, { replace: true });
        }
        return;
      }

      // 2. Create VNPay URL
      const paymentRes = await paymentService.createVNPayUrl({
        orderId: orderId,
        amount: orderTotal,
        orderInfo: `Payment for order ${orderId} POSMART`,
        storeId: selectedStore.id
      });

      const paymentData = paymentRes.data || paymentRes;

      // 3. Redirect to VNPay
      if (paymentData && paymentData.paymentUrl) {
        window.location.href = paymentData.paymentUrl;
      } else {
        throw new Error("Failed to retrieve VNPay URL");
      }
    } catch (err) {
      console.error("Checkout error:", err);
      setError(err.response?.data?.message || err.message || 'An error occurred during payment processing');
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-50 min-h-screen">
      <Header />
      <main className="max-w-7xl mx-auto px-4 lg:px-8 py-8">
        <h1 className="font-bold text-gray-800 text-3xl mb-8">Checkout</h1>

        {/* Stepper UI */}
        <div className="mb-10 max-w-3xl mx-auto">
          <div className="relative flex items-center justify-between">
            {/* Connecting Line */}
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-gray-200 rounded-full z-0"></div>
            <div
              className="absolute left-0 top-1/2 -translate-y-1/2 h-1 bg-emerald-500 rounded-full z-0 transition-all duration-300"
              style={{ width: step === 'confirm' ? '100%' : '50%' }}
            ></div>

            {/* Step 1: Shipping */}
            <div className="relative z-10 flex flex-col items-center">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-colors duration-300 border-2 ${step === 'shipping'
                ? 'bg-emerald-500 text-white border-emerald-500 ring-4 ring-emerald-50'
                : 'bg-emerald-500 text-white border-emerald-500'
                }`}>
                {step === 'confirm' ? <CheckCircle2 className="w-5 h-5" /> : 1}
              </div>
              <span className={`mt-2 text-sm font-semibold ${step === 'shipping' ? 'text-emerald-600' : 'text-gray-800'}`}>
                Shipping
              </span>
            </div>

            {/* Step 2: Payment/Confirm */}
            <div className="relative z-10 flex flex-col items-center">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-colors duration-300 border-2 ${step === 'confirm'
                ? 'bg-emerald-500 text-white border-emerald-500 ring-4 ring-emerald-50'
                : 'bg-white text-gray-400 border-gray-300'
                }`}>
                2
              </div>
              <span className={`mt-2 text-sm font-semibold ${step === 'confirm' ? 'text-emerald-600' : 'text-gray-400'}`}>
                Confirmation
              </span>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg border border-red-200 mb-6">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            {step === 'shipping' ? (
              <>
                <AddressBook onSelect={(addr) => {
                  setFormData(prev => ({
                    ...prev,
                    fullName: addr.fullName,
                    phone: addr.phone,
                    address: addr.address
                  }));
                  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                }} />
                <ShippingForm formData={formData} setFormData={setFormData} />
                <PaymentMethodSelect paymentMethod={paymentMethod} setPaymentMethod={setPaymentMethod} />
              </>
            ) : (
              <ConfirmationStep
                formData={formData}
                paymentMethod={paymentMethod}
                onEdit={() => setStep('shipping')}
              />
            )}
          </div>

          <div>
            <OrderSummary />
            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center items-center h-14 bg-emerald-500 text-white font-bold rounded-xl hover:bg-emerald-600 transition-colors disabled:bg-emerald-300 shadow-lg shadow-emerald-200"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : step === 'shipping' ? 'Continue' : 'Place Order'}
            </button>
          </div>
        </form>
      </main>
      <Footer />
    </div>
  );
}
