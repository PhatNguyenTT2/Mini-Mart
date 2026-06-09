import { useEffect, useState } from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useStore } from '../contexts/StoreContext';
import { useCart } from '../contexts/CartContext';
import orderService from '../services/orderService';
import productService from '../services/productService';
import couponService from '../services/couponService';
import { Header } from '../components/Header';
import Footer from '../components/Footer/Footer';
import { ShoppingBag, ChevronRight, PackageX, RefreshCw, Ticket, Check } from 'lucide-react';
import toast from 'react-hot-toast';

export default function OrderHistoryPage() {
  const { user } = useAuth();
  const { selectedStore } = useStore();
  const { addMultipleToCart } = useCart();

  const [activeTab, setActiveTab] = useState('orders'); // 'orders' | 'coupons'
  const [orders, setOrders] = useState([]);
  const [coupons, setCoupons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingCoupons, setLoadingCoupons] = useState(false);
  const [error, setError] = useState('');
  const [reorderingId, setReorderingId] = useState(null);

  useEffect(() => {
    if (!user) return;

    const fetchOrders = async () => {
      try {
        const res = await orderService.getMyOrders({ customer: user.customerId || user.id }, selectedStore?.id);
        const fetchedOrders = res.data?.orders || res.orders || [];
        // Sort by created_at desc
        fetchedOrders.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        setOrders(fetchedOrders);
      } catch (err) {
        console.error('Error fetching order list:', err);
        setError('Unable to fetch order list. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, [user, selectedStore?.id]);

  useEffect(() => {
    if (activeTab === 'coupons') {
      const fetchCoupons = async () => {
        setLoadingCoupons(true);
        try {
          const res = await couponService.getAvailableCoupons();
          setCoupons(res.data || []);
        } catch (err) {
          console.error('Error fetching user coupons:', err);
        } finally {
          setLoadingCoupons(false);
        }
      };
      fetchCoupons();
    }
  }, [activeTab]);

  if (!user) {
    return <Navigate to="/login?redirect=/orders" replace />;
  }

  const getStatusBadge = (status, paymentStatus) => {
    if (status === 'cancelled') {
      return <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-xs font-semibold">Cancelled</span>;
    }
    if (status === 'delivered') {
      return <span className="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-semibold">Delivered</span>;
    }
    if (status === 'shipping') {
      return <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold">Shipping</span>;
    }
    if (status === 'draft') {
      if (paymentStatus === 'completed') {
        return <span className="px-3 py-1 bg-amber-100 text-amber-700 rounded-full text-xs font-semibold">Processing</span>;
      }
      return <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-semibold">Pending Payment</span>;
    }
    return <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-semibold">{status}</span>;
  };

  const handleReorder = async (e, orderId) => {
    e.preventDefault();
    e.stopPropagation();

    if (reorderingId) return;
    setReorderingId(orderId);

    try {
      // 1. Fetch order details
      const detailsRes = await orderService.getOrderDetails(orderId, selectedStore?.id);
      const items = detailsRes.data?.items || detailsRes.items || [];

      if (items.length === 0) {
        toast.error('Order has no items to re-order');
        setReorderingId(null);
        return;
      }

      // 2. Fetch inventory summary
      const inventoryRes = await productService.getStoreInventorySummary(selectedStore?.id);
      const inventoryList = inventoryRes.data?.summary || inventoryRes.summary || [];
      const inventoryMap = {};
      inventoryList.forEach(inv => {
        inventoryMap[inv.product_id] = inv.total_quantity;
      });

      // 3. Map order items to cart format
      const cartItems = items.map(item => ({
        id: item.product_id,
        name: item.product_name,
        price: item.unit_price,
        quantity: item.quantity,
        image: item.image || 'https://via.placeholder.com/150',
      }));

      // 4. Add to cart
      await addMultipleToCart(cartItems, inventoryMap);

    } catch (err) {
      console.error('Re-order failed:', err);
      toast.error('Failed to re-order. Please try again.');
    } finally {
      setReorderingId(null);
    }
  };

  const formatVND = (amt) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amt);
  };

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col">
      <Header />
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 lg:px-8 py-8">
        {/* Tab Headers */}
        <div className="flex border-b border-gray-200 mb-8">
          <button
            onClick={() => setActiveTab('orders')}
            className={`py-4 px-6 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${activeTab === 'orders'
              ? 'border-emerald-500 text-emerald-600'
              : 'border-transparent text-gray-450 hover:text-gray-700'
              }`}
          >
            <ShoppingBag className="w-5 h-5" />
            My Orders
          </button>
          <button
            onClick={() => setActiveTab('coupons')}
            className={`py-4 px-6 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${activeTab === 'coupons'
              ? 'border-emerald-500 text-emerald-600'
              : 'border-transparent text-gray-450 hover:text-gray-700'
              }`}
          >
            <Ticket className="w-5 h-5" />
            My Coupons
          </button>
        </div>

        {error && (
          <div className="bg-red-50 text-red-650 p-4 rounded-lg border border-red-200 mb-6">
            {error}
          </div>
        )}

        {activeTab === 'orders' ? (
          loading ? (
            <div className="flex justify-center items-center py-20">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-500" />
            </div>
          ) : orders.length === 0 ? (
            <div className="bg-white border border-gray-200 rounded-xl p-12 text-center flex flex-col items-center">
              <PackageX className="w-16 h-16 text-gray-300 mb-4" />
              <h2 className="text-xl font-bold text-gray-800 mb-2">You have no orders yet</h2>
              <p className="text-gray-500 mb-6">Discover our fresh products today!</p>
              <Link
                to="/"
                className="bg-emerald-500 text-white font-semibold px-6 py-3 rounded-lg hover:bg-emerald-600 transition-colors no-underline"
              >
                Continue Shopping
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {orders.map(order => (
                <Link
                  key={order.id}
                  to={`/order-status/${order.id}`}
                  className="block bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md transition-shadow group no-underline"
                >
                  <div className="flex flex-col md:flex-row justify-between md:items-center gap-4">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-bold text-lg text-gray-850">Order #{order.id}</span>
                        {getStatusBadge(order.status, order.paymentStatus)}
                      </div>
                      <p className="text-sm text-gray-500 mb-1">
                        Order Date: {new Date(order.orderDate || new Date()).toLocaleString('en-US')}
                      </p>
                      <p className="text-sm text-gray-500">
                        Items: {order.itemCount || 0} items
                      </p>
                    </div>

                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between md:justify-end gap-4 border-t md:border-t-0 pt-4 md:pt-0 border-gray-100 w-full md:w-auto mt-4 md:mt-0">
                      <div className="text-left md:text-right flex-1">
                        <span className="text-sm text-gray-500 block">Total</span>
                        <span className="font-bold text-emerald-600 text-xl">
                          {formatVND(order.total || 0)}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 w-full md:w-auto">
                        <button
                          type="button"
                          onClick={(e) => handleReorder(e, order.id)}
                          disabled={reorderingId === order.id}
                          className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-white border border-emerald-500 text-emerald-600 font-semibold rounded-lg hover:bg-emerald-50 transition-colors disabled:opacity-50"
                        >
                          <RefreshCw className={`w-4 h-4 ${reorderingId === order.id ? 'animate-spin' : ''}`} />
                          <span className="whitespace-nowrap">{reorderingId === order.id ? 'Loading...' : 'Re-order'}</span>
                        </button>
                        <div className="w-10 h-10 shrink-0 rounded-full bg-emerald-50 text-emerald-500 flex items-center justify-center group-hover:bg-emerald-500 group-hover:text-white transition-colors">
                          <ChevronRight className="w-5 h-5" />
                        </div>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )
        ) : (
          /* Coupons Tab Content */
          loadingCoupons ? (
            <div className="flex justify-center items-center py-20">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-emerald-500" />
            </div>
          ) : coupons.length === 0 ? (
            <div className="bg-white border border-gray-200 rounded-xl p-12 text-center flex flex-col items-center">
              <Ticket className="w-16 h-16 text-gray-300 mb-4" />
              <h2 className="text-xl font-bold text-gray-800 mb-2">No coupons available right now</h2>
              <p className="text-gray-500 mb-6">Check back later for new promotional campaigns!</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {coupons.map((coupon) => (
                <div
                  key={coupon.id}
                  className="bg-white border border-gray-200 rounded-xl p-6 relative overflow-hidden flex gap-5 hover:shadow-md transition-shadow"
                >
                  {/* Decorative Ticket Notch */}
                  <div className="absolute top-1/2 -left-3 w-6 h-6 rounded-full bg-gray-50 border border-gray-200 transform -translate-y-1/2" />
                  <div className="absolute top-1/2 -right-3 w-6 h-6 rounded-full bg-gray-50 border border-gray-200 transform -translate-y-1/2" />

                  <div className="flex-1 min-w-0">
                    <span className="inline-block px-3 py-1 rounded bg-emerald-50 text-emerald-700 font-extrabold text-xs uppercase tracking-wider mb-3">
                      {coupon.discount_type === 'freeship' ? 'Free Shipping' : coupon.discount_type === 'percent' ? 'Discount %' : 'Discount Cash'}
                    </span>
                    <h3 className="font-extrabold text-gray-850 text-lg uppercase mb-1">{coupon.code}</h3>
                    <p className="text-gray-650 text-sm mb-4 leading-relaxed">{coupon.description}</p>
                    <div className="flex justify-between items-center text-xs text-gray-400 mt-2">
                      <span>Min Spend: {formatVND(coupon.min_order_amount || 0)}</span>
                      <span>Expires: {coupon.end_date ? new Date(coupon.end_date).toLocaleDateString() : 'No expiry'}</span>
                    </div>
                  </div>
                  <div className="flex flex-col justify-between items-end border-l border-dashed border-gray-200 pl-4 w-28">
                    <div className="text-emerald-600 font-extrabold text-lg text-right">
                      {coupon.discount_type === 'percent' ? `${coupon.discount_value}%` : formatVND(coupon.discount_value)}
                    </div>
                    {coupon.usage_limit && coupon.usage_count >= coupon.usage_limit ? (
                      <span className="text-xs text-red-500 font-medium">Fully Used</span>
                    ) : (
                      <div className="flex items-center gap-1 text-[11px] text-emerald-500 font-bold bg-emerald-50 px-2 py-1 rounded">
                        <Check className="w-3.5 h-3.5" />
                        Available
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </main>
      <Footer />
    </div>
  );
}
