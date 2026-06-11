import { useEffect, useState, useRef } from 'react';
import { useParams, useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useStore } from '../contexts/StoreContext';
import { useCart } from '../contexts/CartContext';
import orderService from '../services/orderService';
import { Header } from '../components/Header';
import Footer from '../components/Footer/Footer';
import { CheckCircle, Clock, Truck, Package, XCircle, ArrowLeft } from 'lucide-react';
import paymentService from '../services/paymentService';
import { PaymentMethodSelect } from '../components/Checkout/PaymentMethodSelect';

export default function OrderStatusPage() {
  const { orderId } = useParams();
  const [searchParams] = useSearchParams();
  const paymentStatus = searchParams.get('payment'); // 'success' or 'failed'

  const { selectedStore } = useStore();
  const { clearCart } = useCart();
  const navigate = useNavigate();

  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [retryPaymentMethod, setRetryPaymentMethod] = useState('cod');
  const [isRetrying, setIsRetrying] = useState(false);

  const pollIntervalRef = useRef(null);

  useEffect(() => {
    // If VNPay returns success or COD was chosen, clear cart automatically
    if (paymentStatus === 'success' || paymentStatus === 'cod') {
      clearCart();
    }
  }, [paymentStatus, clearCart]);

  useEffect(() => {
    let isSubscribed = true;

    const fetchOrder = async () => {
      try {
        const res = await orderService.getOrderById(orderId, selectedStore?.id);
        if (!isSubscribed) return;

        const fetchedOrder = res.data?.order || res.order || res;
        setOrder(fetchedOrder);
        setLoading(false);

        // Stop polling if order is cancelled or delivered
        if (fetchedOrder.status === 'cancelled' || fetchedOrder.status === 'delivered') {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      } catch {
        if (!isSubscribed) return;
        setError('Unable to fetch order information');
        setLoading(false);
      }
    };

    const startPolling = () => {
      if (!pollIntervalRef.current) {
        pollIntervalRef.current = setInterval(fetchOrder, 5000);
      }
    };

    const stopPolling = () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };

    const handleVisibilityChange = () => {
      if (document.hidden) {
        stopPolling();
      } else {
        fetchOrder(); // Fetch immediately when tab becomes visible
        startPolling();
      }
    };

    // Initial fetch and start polling
    fetchOrder();
    startPolling();

    const handleChatAction = (e) => {
      const action = e.detail;
      if (action && action.type === 'CANCEL_ORDER' && Number(action.payload?.orderId) === Number(orderId)) {
        fetchOrder();
      }
    };
    window.addEventListener('posmart:customer_chat_action', handleChatAction);

    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      isSubscribed = false;
      stopPolling();
      window.removeEventListener('posmart:customer_chat_action', handleChatAction);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [orderId, selectedStore?.id]);

  if (loading && !order) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header />
        <div className="flex-1 flex items-center justify-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-500" />
        </div>
        <Footer />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col">
        <Header />
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="bg-white p-8 rounded-xl border border-gray-200 text-center max-w-md w-full">
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-800 mb-2">Error</h2>
            <p className="text-gray-600 mb-6">{error}</p>
            <Link to="/" className="text-emerald-600 font-semibold hover:underline">Back to Home</Link>
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  // Calculate timeout for draft pending orders (Task 8)
  const isTimedOut = () => {
    if (order.status !== 'draft' || order.payment_status !== 'pending') return false;
    const createdAt = new Date(order.created_at);
    const now = new Date();
    const diffMinutes = (now - createdAt) / 1000 / 60;
    return diffMinutes >= 15;
  };

  const timedOut = isTimedOut();

  const handleRetryPayment = async () => {
    if (!order) return;
    setIsRetrying(true);
    setError('');

    try {
      if (retryPaymentMethod === 'cod') {
        await paymentService.createDirectPayment({
          orderId: order.id,
          amount: order.total,
          items: order.details || [],
          storeId: selectedStore?.id || 1
        });
        navigate(`/orders/${order.id}?payment=cod`, { replace: true });
        window.location.reload();
        return;
      }

      if (retryPaymentMethod === 'vnpay') {
        const paymentRes = await paymentService.createVNPayUrl({
          orderId: order.id,
          amount: order.total,
          orderInfo: `Payment for order ${order.id} POSMART`,
          storeId: selectedStore?.id || 1
        });

        const paymentData = paymentRes.data || paymentRes;
        if (paymentData && paymentData.paymentUrl) {
          window.location.href = paymentData.paymentUrl;
        } else {
          throw new Error("Failed to retrieve VNPay URL");
        }
      }
    } catch (err) {
      console.error("Retry payment error:", err);
      setError(err.response?.data?.message || err.message || 'An error occurred during payment processing');
    } finally {
      setIsRetrying(false);
    }
  };

  const renderPaymentResult = () => {
    if (order?.status === 'cancelled' || order?.status === 'refunded') return null;

    const effectivePaymentStatus = paymentStatus || order?.paymentStatus;

    if (effectivePaymentStatus === 'success') {
      return (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6 text-center mb-8">
          <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-emerald-800 mb-2">Payment Successful!</h2>
          <p className="text-emerald-600">Your order is being processed.</p>
        </div>
      );
    }
    if (effectivePaymentStatus === 'cod') {
      return (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6 text-center mb-8">
          <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-emerald-800 mb-2">Order Placed Successfully!</h2>
          <p className="text-emerald-600">You will pay via Cash on Delivery when receiving the order.</p>
        </div>
      );
    }
    if (effectivePaymentStatus === 'failed') {
      return (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-8">
          <div className="text-center mb-6">
            <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-red-800 mb-2">Payment Failed</h2>
            <p className="text-red-600 mb-4">Please try again or select another payment method.</p>
          </div>

          <div className="bg-white rounded-lg p-6 max-w-lg mx-auto shadow-sm">
            <h3 className="font-semibold text-gray-800 mb-4">Try another payment method</h3>
            <PaymentMethodSelect paymentMethod={retryPaymentMethod} setPaymentMethod={setRetryPaymentMethod} />
            <div className="mt-6 text-center">
              <button
                onClick={handleRetryPayment}
                disabled={isRetrying}
                className={`bg-emerald-500 text-white font-semibold px-8 py-3 rounded-lg hover:bg-emerald-600 transition-colors w-full sm:w-auto ${isRetrying ? 'opacity-70 cursor-not-allowed' : ''}`}
              >
                {isRetrying ? 'Processing...' : 'Pay Now'}
              </button>
            </div>
          </div>
        </div>
      );
    }
    if (effectivePaymentStatus === 'pending') {
      return (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-8">
          <div className="text-center mb-6">
            <Clock className="w-16 h-16 text-amber-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-amber-800 mb-2">Order Created</h2>
            <p className="text-amber-600 mb-4">
              Your order was created but payment confirmation is still processing. Please check back shortly.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="bg-amber-500 text-white font-semibold px-6 py-2 rounded-lg hover:bg-amber-600 transition-colors"
            >
              Refresh Status
            </button>
          </div>

          <div className="bg-white rounded-lg p-6 max-w-lg mx-auto shadow-sm border-t border-amber-100 mt-6 pt-6">
            <h3 className="font-semibold text-gray-800 mb-4">Or select another payment method</h3>
            <PaymentMethodSelect paymentMethod={retryPaymentMethod} setPaymentMethod={setRetryPaymentMethod} />
            <div className="mt-6 text-center">
              <button
                onClick={handleRetryPayment}
                disabled={isRetrying}
                className={`bg-emerald-500 text-white font-semibold px-8 py-3 rounded-lg hover:bg-emerald-600 transition-colors w-full sm:w-auto ${isRetrying ? 'opacity-70 cursor-not-allowed' : ''}`}
              >
                {isRetrying ? 'Processing...' : 'Pay Now'}
              </button>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  const renderTimeline = () => {
    const steps = [
      { id: 'draft', label: 'Draft', icon: Package },
      { id: 'paid', label: 'Paid', icon: CheckCircle },
      { id: 'shipping', label: 'Shipping', icon: Truck },
      { id: 'delivered', label: 'Delivered', icon: CheckCircle }
    ];

    let currentStepIndex = 0;
    if (order.status === 'shipping') currentStepIndex = 2;
    if (order.status === 'delivered') currentStepIndex = 3;
    if (order.paymentStatus === 'completed' && order.status === 'draft') currentStepIndex = 1;

    // Override if cancelled or timed out
    if (order.status === 'cancelled' || timedOut) {
      return (
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-8 text-center">
          <XCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <h3 className="font-bold text-lg text-gray-800">
            {timedOut ? 'Payment timeout (Exceeded 15 minutes)' : 'Order has been cancelled'}
          </h3>
        </div>
      );
    }

    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6 mb-8">
        <h3 className="font-bold text-lg text-gray-800 mb-6">Order Status</h3>
        <div className="flex flex-col md:flex-row justify-between relative">
          {/* Connecting line */}
          <div className="hidden md:block absolute top-6 left-0 right-0 h-1 bg-gray-200 -z-10" />

          {steps.map((step, index) => {
            const Icon = step.icon;
            const isCompleted = index <= currentStepIndex;
            const isCurrent = index === currentStepIndex;

            return (
              <div key={step.id} className="flex flex-col items-center mb-6 md:mb-0 bg-white px-2">
                <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-3 transition-colors ${isCompleted ? 'bg-emerald-500 text-white' : 'bg-gray-100 text-gray-400'
                  } ${isCurrent ? 'ring-4 ring-emerald-100' : ''}`}>
                  <Icon className="w-6 h-6" />
                </div>
                <span className={`text-sm font-semibold ${isCompleted ? 'text-gray-800' : 'text-gray-400'}`}>
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 max-w-3xl mx-auto w-full px-4 lg:px-8 py-8">
        <button
          onClick={() => navigate('/')}
          className="flex items-center text-gray-500 hover:text-emerald-600 transition-colors mb-6 font-semibold text-sm"
        >
          <ArrowLeft className="w-4 h-4 mr-2" /> Back to Home
        </button>

        {renderPaymentResult()}
        {renderTimeline()}

        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h3 className="font-bold text-lg text-gray-800 mb-4">Order ID: #{order.id}</h3>

          <div className="space-y-4">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Total</span>
              <span className="font-bold text-gray-800">
                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND' }).format(order.total || 0)}
              </span>
            </div>

            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Order Date</span>
              <span className="font-semibold text-gray-800">
                {new Date(order.orderDate || new Date()).toLocaleString('en-US')}
              </span>
            </div>

            <div className="pt-4 border-t border-gray-100">
              <span className="text-gray-500 text-sm block mb-2">Shipping Address</span>
              <p className="font-semibold text-gray-800 text-sm whitespace-pre-line">{order.address || 'None'}</p>
            </div>

            {order.notes && (
              <div className="pt-4 border-t border-gray-100">
                <span className="text-gray-500 text-sm block mb-2">Notes</span>
                <p className="text-gray-800 text-sm">{order.notes}</p>
              </div>
            )}

            {order.details && order.details.length > 0 && (
              <div className="pt-4 border-t border-gray-100">
                <span className="text-gray-500 text-sm block mb-4">Order Items</span>
                <div className="space-y-3">
                  {order.details.map((item, idx) => (
                    <div key={idx} className="flex justify-between items-center text-sm">
                      <div className="flex-1">
                        <p className="font-semibold text-gray-800">{item.productName}</p>
                        <p className="text-gray-500">Qty: {item.quantity}</p>
                      </div>
                      <span className="font-bold text-gray-800">
                        {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'VND' }).format(item.totalPrice || (item.quantity * item.unitPrice))}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
