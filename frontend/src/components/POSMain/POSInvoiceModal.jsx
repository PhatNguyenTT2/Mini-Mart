import React, { useState, useEffect, useRef, useCallback } from 'react';
import posDataService from '../../services/posDataService';

// Status progression for POS direct sale Saga
const SAGA_STEPS = [
  { key: 'payment', label: 'Payment', statuses: ['pending'] },
  { key: 'processing', label: 'Processing', statuses: ['draft'] },
  { key: 'completed', label: 'Completed', statuses: ['delivered', 'completed'] }
];

function getProgressFromOrder(order) {
  if (!order) return 0;
  const status = order.status;
  const paymentStatus = order.paymentStatus;

  if (status === 'delivered' || status === 'completed') return 100;
  if (paymentStatus === 'paid' || paymentStatus === 'completed') return 66;
  if (status === 'shipping') return 50;
  if (status === 'draft' && paymentStatus === 'pending') return 15;
  return 33;
}

function getStepStatus(stepIndex, order) {
  if (!order) return 'pending';
  const progress = getProgressFromOrder(order);
  if (stepIndex === 0) return progress >= 33 ? 'done' : 'active';
  if (stepIndex === 1) return progress >= 66 ? 'done' : progress >= 33 ? 'active' : 'pending';
  if (stepIndex === 2) return progress >= 100 ? 'done' : progress >= 66 ? 'active' : 'pending';
  return 'pending';
}

export const POSInvoiceModal = ({ isOpen, order: initialOrder, onClose, onComplete }) => {
  const [loading, setLoading] = useState(true);
  const [liveOrder, setLiveOrder] = useState(null);
  const [orderDetails, setOrderDetails] = useState([]);
  const [customerInfo, setCustomerInfo] = useState(null);
  const [employeeName, setEmployeeName] = useState('');
  const [confirmingDelivery, setConfirmingDelivery] = useState(false);
  const pollRef = useRef(null);
  const pollCountRef = useRef(0);

  // Fetch full order data + enrich customer/employee
  const fetchAndEnrich = useCallback(async (orderId) => {
    try {
      const res = await posDataService.getOrderById(orderId);
      const orderData = res.data?.order || res.data || res;
      const details = orderData.details || [];
      return { orderData, details };
    } catch (err) {
      console.error('Failed to fetch order:', err);
      return null;
    }
  }, []);

  // Initial load
  useEffect(() => {
    if (!isOpen || !initialOrder) { setLoading(false); return; }

    const init = async () => {
      setLoading(true);
      const orderId = initialOrder.id;

      // Fetch order with details
      const result = await fetchAndEnrich(orderId);
      if (result) {
        const merged = { ...initialOrder, ...result.orderData, paymentMethod: initialOrder.paymentMethod || result.orderData.paymentMethod };
        setLiveOrder(merged);
        setOrderDetails(result.details);
      } else {
        setLiveOrder(initialOrder);
        setOrderDetails(initialOrder.details || []);
      }

      // Enrich customer
      const custId = result?.orderData?.customerId || initialOrder.customerId;
      if (custId && custId !== 'virtual-guest') {
        try {
          const custRes = await posDataService.getCustomerById(custId);
          const c = custRes.data?.customer || custRes.data;
          if (c) setCustomerInfo(c);
        } catch (_) {
          // ignore error for optional customer info
        }
      }

      // Enrich employee
      const empId = result?.orderData?.createdBy || initialOrder.createdBy;
      if (empId) {
        try {
          const empRes = await posDataService.getEmployeeById(empId);
          const e = empRes.data?.employee || empRes.data;
          if (e) setEmployeeName(e.fullName || e.full_name || `Employee #${empId}`);
        } catch (_) {
          setEmployeeName(`Employee #${empId}`);
        }
      }

      setLoading(false);
    };

    init();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [isOpen, initialOrder, fetchAndEnrich]);

  // Poll for status updates (Saga async)
  useEffect(() => {
    if (!isOpen || !liveOrder) return;

    const isFinal = liveOrder.status === 'delivered' || liveOrder.status === 'completed';
    if (isFinal) { if (pollRef.current) clearInterval(pollRef.current); return; }

    pollCountRef.current = 0;
    pollRef.current = setInterval(async () => {
      pollCountRef.current++;
      if (pollCountRef.current > 20) { clearInterval(pollRef.current); return; } // Max 20 polls (~60s)

      try {
        const res = await posDataService.getOrderById(liveOrder.id);
        const fresh = res.data?.order || res.data || res;
        const newFinal = fresh.status === 'delivered' || fresh.status === 'completed';

        setLiveOrder(prev => ({
          ...prev,
          status: fresh.status,
          paymentStatus: fresh.paymentStatus,
          total: fresh.total || prev.total
        }));

        if (newFinal) clearInterval(pollRef.current);
      } catch (_) {
        // ignore polling errors
      }
    }, 3000);

    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [isOpen, liveOrder?.id, liveOrder?.status]);

  if (!isOpen || !initialOrder) return null;

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <div className="flex items-center gap-3">
            <svg className="animate-spin h-6 w-6 text-emerald-600" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-sm font-['Poppins',sans-serif] text-gray-600">Loading invoice...</p>
          </div>
        </div>
      </div>
    );
  }

  const order = liveOrder || initialOrder;

  const formatCurrency = (amount) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount || 0);
  const formatDate = (d) => new Date(d).toLocaleDateString('vi-VN', { year: 'numeric', month: '2-digit', day: '2-digit' });
  const formatTime = (d) => new Date(d).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });

  const details = orderDetails || [];
  const subtotal = details.reduce((sum, d) => sum + (parseFloat(d.quantity) || 0) * (parseFloat(d.unitPrice) || 0), 0);
  const discountPct = parseFloat(order.discountPercentage) || 0;
  const discountAmt = subtotal * (discountPct / 100);
  const shippingFee = parseFloat(order.shippingFee) || 0;
  const total = parseFloat(order.total) || (subtotal - discountAmt + shippingFee);

  const progress = getProgressFromOrder(order);
  const isFinalStatus = order.status === 'delivered' || order.status === 'completed';

  const handlePrint = () => {
    const el = document.getElementById('pos-invoice-content');
    if (!el) return;
    const w = window.open('', '_blank');
    w.document.write(`<html><head><title>Invoice - ${order.orderNumber}</title><style>body{font-family:Arial,sans-serif;padding:20px}table{width:100%;border-collapse:collapse;margin:20px 0}th,td{border:1px solid #ddd;padding:8px;text-align:left}th{background:#f4f4f4}.text-right{text-align:right}</style></head><body>${el.innerHTML}</body></html>`);
    w.document.close();
    w.print();
  };

  const handleConfirmDelivery = async () => {
    if (!window.confirm('Confirm that this order has been delivered to the customer?')) return;
    setConfirmingDelivery(true);
    try {
      await posDataService.updateOrder(order.id, { status: 'delivered' });
      setLiveOrder(prev => ({ ...prev, status: 'delivered' }));
      if (onComplete) onComplete();
    } catch (err) {
      console.error('Confirm delivery error:', err);
      alert('Failed to confirm delivery. Please try again.');
    } finally {
      setConfirmingDelivery(false);
    }
  };

  const paymentMethodLabel = {
    cash: 'CASH', card: 'CARD', bank_transfer: 'BANK TRANSFER', vnpay: 'VNPAY'
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-hidden" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-emerald-500 to-emerald-600">
          <h3 className="text-[20px] font-bold font-['Poppins',sans-serif] text-white">Order Invoice</h3>
          <button onClick={onClose} className="p-2 hover:bg-emerald-700 rounded-full transition-colors">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M18 6L6 18M6 6L18 18" stroke="white" strokeWidth="2" strokeLinecap="round" /></svg>
          </button>
        </div>

        {/* Progress Bar — Saga Status Tracker */}
        <div className="px-6 py-4 bg-gray-50 border-b">
          <div className="flex items-center justify-between mb-2">
            {SAGA_STEPS.map((step, i) => {
              const status = getStepStatus(i, order);
              return (
                <div key={step.key} className="flex flex-col items-center flex-1">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-500 ${status === 'done' ? 'bg-emerald-500 text-white' :
                    status === 'active' ? 'bg-amber-400 text-white animate-pulse' :
                      'bg-gray-200 text-gray-500'
                    }`}>
                    {status === 'done' ? (
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                    ) : i + 1}
                  </div>
                  <span className={`text-[11px] mt-1 font-medium ${status === 'done' ? 'text-emerald-600' : status === 'active' ? 'text-amber-600' : 'text-gray-400'}`}>
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
          {/* Progress line */}
          <div className="relative h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div className="absolute h-full bg-gradient-to-r from-emerald-400 to-emerald-500 rounded-full transition-all duration-1000 ease-out" style={{ width: `${progress}%` }} />
          </div>
          {!isFinalStatus && (
            <p className="text-[11px] font-['Poppins',sans-serif] text-amber-600 mt-1.5 text-center animate-pulse">
              Processing asynchronously... Status will update automatically
            </p>
          )}
        </div>

        {/* Invoice Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-280px)] p-6" id="pos-invoice-content">
          {/* Order Info */}
          <div className="grid grid-cols-2 gap-4 mb-5 text-[13px]">
            <div>
              <p className="font-['Poppins',sans-serif]"><span className="font-semibold text-emerald-600">Order Number:</span> <span className="ml-1 text-gray-900 font-medium">{order.orderNumber}</span></p>
            </div>
            <div className="text-right">
              <p className="font-['Poppins',sans-serif]"><span className="font-semibold text-emerald-600">Date:</span> <span className="ml-1">{formatDate(order.orderDate)}</span> — {formatTime(order.orderDate)}</p>
            </div>
          </div>

          {/* Customer Info */}
          <div className="mb-5 bg-gray-50 rounded-lg p-4">
            <p className="text-[14px] font-semibold font-['Poppins',sans-serif] text-emerald-600 mb-2">Customer Information</p>
            <div className="space-y-1 text-[13px]">
              <p className="font-['Poppins',sans-serif]"><span className="font-semibold text-gray-700">Name:</span> <span className="ml-1">{customerInfo?.fullName || customerInfo?.full_name || 'Walk-in Customer'}</span></p>
              {customerInfo?.phone && <p className="font-['Poppins',sans-serif]"><span className="font-semibold text-gray-700">Phone:</span> <span className="ml-1">{customerInfo.phone}</span></p>}
              {(customerInfo?.customerType || customerInfo?.customer_type) && (
                <p className="font-['Poppins',sans-serif]"><span className="font-semibold text-gray-700">Type:</span> <span className={`ml-1 capitalize font-medium ${(customerInfo.customerType || customerInfo.customer_type) === 'vip' ? 'text-amber-600' :
                  (customerInfo.customerType || customerInfo.customer_type) === 'wholesale' ? 'text-emerald-600' : 'text-blue-600'
                  }`}>{customerInfo.customerType || customerInfo.customer_type}</span></p>
              )}
              <p className="font-['Poppins',sans-serif]"><span className="font-semibold text-gray-700">Delivery:</span> <span className="ml-1 capitalize">{order.deliveryType === 'delivery' ? 'Home Delivery' : 'Pickup'}</span></p>
            </div>
          </div>

          {/* Items Table */}
          <div className="mb-5">
            <table className="w-full border-collapse border border-gray-300">
              <thead>
                <tr className="bg-emerald-50">
                  <th className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-center w-12">No.</th>
                  <th className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-left">Product Name</th>
                  <th className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-center w-16">Qty</th>
                  <th className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-right w-24">Price</th>
                  <th className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-right w-28">Amount</th>
                </tr>
              </thead>
              <tbody>
                {details.length > 0 ? details.map((d, i) => {
                  const qty = parseFloat(d.quantity) || 0;
                  const price = parseFloat(d.unitPrice) || 0;
                  return (
                    <tr key={d.id || i} className="hover:bg-gray-50">
                      <td className="border border-gray-300 px-3 py-2 text-xs text-center">{i + 1}</td>
                      <td className="border border-gray-300 px-3 py-2 text-[12px] font-medium">{d.productName || `Product #${d.productId}`}</td>
                      <td className="border border-gray-300 px-3 py-2 text-xs text-center">{qty}</td>
                      <td className="border border-gray-300 px-3 py-2 text-xs text-right">{formatCurrency(price)}</td>
                      <td className="border border-gray-300 px-3 py-2 text-xs text-right font-medium">{formatCurrency(qty * price)}</td>
                    </tr>
                  );
                }) : (
                  <tr><td colSpan="5" className="border border-gray-300 px-3 py-4 text-center text-[12px] text-gray-500">No items found</td></tr>
                )}

                <tr className="bg-gray-50">
                  <td colSpan="4" className="border border-gray-300 px-3 py-2 text-[13px] font-semibold font-['Poppins',sans-serif] text-right">Subtotal:</td>
                  <td className="border border-gray-300 px-3 py-2 text-[13px] font-semibold text-right">{formatCurrency(subtotal)}</td>
                </tr>

                {discountPct > 0 && (
                  <tr className="bg-gray-50">
                    <td colSpan="4" className="border border-gray-300 px-3 py-2 text-[13px] font-semibold font-['Poppins',sans-serif] text-right text-green-600">Discount ({discountPct}%):</td>
                    <td className="border border-gray-300 px-3 py-2 text-[13px] font-semibold text-right text-green-600">-{formatCurrency(discountAmt)}</td>
                  </tr>
                )}

                <tr className="bg-gray-50">
                  <td colSpan="4" className="border border-gray-300 px-3 py-2 text-[13px] font-semibold font-['Poppins',sans-serif] text-right">Shipping Fee:</td>
                  <td className="border border-gray-300 px-3 py-2 text-[13px] font-semibold font-['Poppins',sans-serif] text-right">
                    {shippingFee > 0 ? formatCurrency(shippingFee) : <span className="text-green-600">FREE</span>}
                  </td>
                </tr>

                <tr className="bg-emerald-50">
                  <td colSpan="4" className="border border-gray-300 px-3 py-2 text-[16px] font-bold font-['Poppins',sans-serif] text-right text-emerald-600">TOTAL:</td>
                  <td className="border border-gray-300 px-3 py-2 text-[16px] font-bold font-['Poppins',sans-serif] text-right text-emerald-600">{formatCurrency(total)}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Payment + Status */}
          <div className="grid grid-cols-2 gap-3 mb-5">
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3">
              <p className="text-[12px] font-semibold font-['Poppins',sans-serif] text-emerald-800 mb-1">Payment Method</p>
              <p className="text-[14px] font-bold font-['Poppins',sans-serif] text-emerald-600 uppercase">{paymentMethodLabel[order.paymentMethod] || order.paymentMethod || 'N/A'}</p>
            </div>
            <div className={`border rounded-lg p-3 ${order.paymentStatus === 'paid' ? 'bg-green-50 border-green-200' :
              order.paymentStatus === 'pending' ? 'bg-amber-50 border-amber-200' : 'bg-gray-50 border-gray-200'
              }`}>
              <p className="text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-1">Payment Status</p>
              <p className={`text-[14px] font-bold font-['Poppins',sans-serif] uppercase ${order.paymentStatus === 'paid' ? 'text-green-600' :
                order.paymentStatus === 'pending' ? 'text-amber-600' : 'text-gray-600'
                }`}>
                {order.paymentStatus === 'paid' ? 'PAID' : order.paymentStatus === 'pending' ? '⏳ PENDING' : (order.paymentStatus || 'N/A').toUpperCase()}
              </p>
            </div>
          </div>

          {/* Order Status Badge */}
          <div className="text-center mb-4">
            <span className={`inline-block px-6 py-2 rounded-full text-[14px] font-bold font-['Poppins',sans-serif] ${order.status === 'delivered' || order.status === 'completed' ? 'bg-green-100 text-green-800' :
              order.status === 'shipping' ? 'bg-blue-100 text-blue-800' :
                order.status === 'draft' ? 'bg-gray-100 text-gray-600' :
                  'bg-amber-100 text-amber-800'
              }`}>
              Status: {order.status === 'delivered' ? 'DELIVERED' :
                order.status === 'completed' ? 'COMPLETED' :
                  order.status === 'shipping' ? 'SHIPPING' :
                    order.status === 'draft' ? 'DRAFT' :
                      (order.status || 'N/A').toUpperCase()}
            </span>
          </div>

          {/* Footer */}
          <div className="mt-6 text-center border-t border-gray-200 pt-4">
            <p className="text-[12px] font-['Poppins',sans-serif] text-gray-600">Thank you for your business!</p>
            <p className="text-[11px] font-['Poppins',sans-serif] text-gray-500 mt-1">Served by: {employeeName || 'POS System'}</p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-between items-center">
          <button onClick={handlePrint} className="px-5 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-[14px] font-['Poppins',sans-serif] font-semibold transition-colors flex items-center gap-2">
            <svg width="18" height="18" viewBox="0 0 16 16" fill="none"><rect x="3" y="2" width="10" height="3" stroke="currentColor" strokeWidth="1.5" /><rect x="2" y="5" width="12" height="6" rx="1" stroke="currentColor" strokeWidth="1.5" /><rect x="4" y="9" width="8" height="5" stroke="currentColor" strokeWidth="1.5" /></svg>
            Print Invoice
          </button>

          {order.status === 'pending' ? (
            <button onClick={handleConfirmDelivery} disabled={confirmingDelivery} className="px-5 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[14px] font-['Poppins',sans-serif] font-semibold transition-colors flex items-center gap-2 disabled:opacity-50">
              {confirmingDelivery ? (
                <><svg className="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg> Confirming...</>
              ) : 'Confirm Delivery'}
            </button>
          ) : (
            <button onClick={() => onComplete && onComplete()} className="px-5 py-2.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[14px] font-['Poppins',sans-serif] font-semibold transition-colors">
              Complete & Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
