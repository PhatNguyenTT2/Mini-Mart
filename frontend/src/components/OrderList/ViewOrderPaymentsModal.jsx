import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { X, CreditCard, Plus, CheckCircle } from 'lucide-react';
import paymentService from '../../services/paymentService';
import orderService from '../../services/orderService';

export const ViewOrderPaymentsModal = ({ order, onClose, onPaymentCreated }) => {
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [orderDetails, setOrderDetails] = useState([]);

  // Add Payment Form State
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    amount: '',
    paymentMethod: 'cash',
    paymentDate: new Date().toISOString().split('T')[0],
    notes: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  useEffect(() => {
    if (order) {
      loadPayments();
      loadOrderDetails();
    }
  }, [order]);

  const loadPayments = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await paymentService.getAllPayments({
        referenceType: 'Order',
        referenceId: order.id || order._id,
        limit: 100
      });

      const paymentsData = response?.data?.payments || [];
      console.log('Order payments loaded:', paymentsData.length);

      setPayments(paymentsData);
    } catch (err) {
      console.error('Error loading payments:', err);
      setError(err.response?.data?.error?.message || 'Failed to load payments');
    } finally {
      setLoading(false);
    }
  };

  // Calculate summary
  const orderTotal = parseFloat(order?.total) || 0;
  const totalPaid = payments
    .filter(p => p.status === 'completed')
    .reduce((sum, p) => sum + (parseFloat(p.amount) || 0), 0);
  const totalPending = payments
    .filter(p => p.status === 'pending')
    .reduce((sum, p) => sum + (parseFloat(p.amount) || 0), 0);
  const remainingBalance = Math.max(0, orderTotal - totalPaid);

  // Reset form when opening
  const handleOpenAddForm = () => {
    setFormData({
      amount: remainingBalance > 0 ? remainingBalance.toString() : '',
      paymentMethod: 'cash',
      paymentDate: new Date().toISOString().split('T')[0],
      notes: ''
    });
    setFormError(null);
    setShowAddForm(true);
  };

  // Fetch full order with details for items array
  // List view only returns headers — no sale_order_detail rows
  const loadOrderDetails = async () => {
    try {
      const response = await orderService.getOrderById(order.id || order._id);
      const fullOrder = response?.data?.order;
      if (fullOrder?.details && Array.isArray(fullOrder.details)) {
        setOrderDetails(fullOrder.details);
      }
    } catch (err) {
      console.error('Error loading order details:', err);
    }
  };

  // Build items array from fetched order details (for inventory deduction)
  const getOrderItems = () => {
    const details = orderDetails.length > 0 ? orderDetails : order?.details;
    if (details && Array.isArray(details)) {
      return details.map(d => ({
        batchId: d.batchId,
        locationId: d.locationId || null,
        quantity: d.quantity,
        productName: d.productName
      }));
    }
    return [];
  };

  // Handle form submit — supports both pending and direct (completed) modes
  const handleSubmit = async (e, direct = false) => {
    e.preventDefault();

    const amountValue = parseFloat(formData.amount);
    if (!amountValue || amountValue <= 0) {
      setFormError('Please enter a valid amount greater than 0');
      return;
    }

    // Overpay validation
    if (amountValue > remainingBalance && remainingBalance > 0) {
      const confirmOverpay = window.confirm(
        `Amount (₫${amountValue.toLocaleString('vi-VN')}) exceeds remaining balance (₫${remainingBalance.toLocaleString('vi-VN')}).\n\nDo you want to continue?`
      );
      if (!confirmOverpay) return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      const paymentData = {
        referenceType: 'Order',
        referenceId: order.id || order._id,
        amount: amountValue,
        paymentMethod: formData.paymentMethod,
        paymentDate: formData.paymentDate,
        notes: formData.notes.trim() || undefined,
        items: getOrderItems(),
        deliveryType: order?.deliveryType || 'pickup'
      };

      if (direct) {
        // Direct: creates as 'completed' + publishes payment.completed event
        await paymentService.createDirectPayment(paymentData);
      } else {
        // Pending: creates as 'pending', admin must approve later
        paymentData.status = 'pending';
        await paymentService.createPayment(paymentData);
      }

      // Refresh payments list
      await loadPayments();
      setShowAddForm(false);

      // Notify parent if callback provided
      if (onPaymentCreated) {
        onPaymentCreated();
      }
    } catch (err) {
      console.error('Error creating payment:', err);
      setFormError(err.response?.data?.error?.message || 'Failed to create payment');
    } finally {
      setSubmitting(false);
    }
  };

  if (!order) return null;

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₫0';
    if (typeof amount === 'object' && amount.$numberDecimal) {
      return `₫${Number(amount.$numberDecimal).toLocaleString('vi-VN')}`;
    }
    return `₫${Number(amount).toLocaleString('vi-VN')}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Pending' },
      completed: { bg: 'bg-green-100', text: 'text-green-800', label: 'Completed' },
      cancelled: { bg: 'bg-red-100', text: 'text-red-800', label: 'Cancelled' },
      refunded: { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Refunded' },
    };
    const config = statusMap[status?.toLowerCase()] || { bg: 'bg-gray-100', text: 'text-gray-800', label: status };
    return (
      <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };

  const getPaymentMethodLabel = (method) => {
    const methods = {
      bank_transfer: 'Bank Transfer',
      cash: 'Cash',
      card: 'Card'
    };
    return methods[method] || method;
  };

  const getPaymentStatusBadge = (status) => {
    const statusMap = {
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Pending' },
      partial: { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Partial' },
      paid: { bg: 'bg-green-100', text: 'text-green-800', label: 'Paid' },
      failed: { bg: 'bg-red-100', text: 'text-red-800', label: 'Failed' },
      refunded: { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Refunded' },
    };
    const config = statusMap[status?.toLowerCase()] || { bg: 'bg-gray-100', text: 'text-gray-800', label: status };
    return (
      <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };

  const modalContent = (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]"
      onClick={onClose}
      style={{ zIndex: 9999 }}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-5xl w-full mx-4 max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <div>
            <h3 className="text-[18px] font-semibold text-gray-900">
              Payment History
            </h3>
            <div className="flex items-center gap-4 mt-1">
              <span className="text-[13px] font-semibold text-blue-600">
                {order.orderNumber}
              </span>
              <span className="text-[12px] text-gray-500">
                {order._customerName || 'Guest'}
              </span>
              {getPaymentStatusBadge(order.paymentStatus || 'pending')}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Summary Cards */}
        <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm">
              <p className="text-[11px] text-gray-500 font-medium">Order Total</p>
              <p className="text-[16px] font-bold text-gray-900">{formatCurrency(orderTotal)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg border border-emerald-200 shadow-sm">
              <p className="text-[11px] text-gray-500 font-medium">Paid</p>
              <p className="text-[16px] font-bold text-emerald-600">{formatCurrency(totalPaid)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg border border-yellow-200 shadow-sm">
              <p className="text-[11px] text-gray-500 font-medium">Pending</p>
              <p className="text-[16px] font-bold text-yellow-600">{formatCurrency(totalPending)}</p>
            </div>
            <div className="bg-white p-3 rounded-lg border border-orange-200 shadow-sm">
              <p className="text-[11px] text-gray-500 font-medium">Remaining</p>
              <p className="text-[16px] font-bold text-orange-600">{formatCurrency(remainingBalance)}</p>
            </div>
          </div>
        </div>

        {/* Add Payment Form */}
        {showAddForm && (
          <div className="px-6 py-4 bg-blue-50 border-b border-blue-200">
            <form onSubmit={handleSubmit}>
              <div className="flex items-center gap-2 mb-3">
                <Plus className="w-4 h-4 text-blue-600" />
                <h4 className="text-[14px] font-semibold text-gray-900">Add New Payment</h4>
              </div>

              {formError && (
                <div className="mb-3 px-3 py-2 bg-red-100 border border-red-200 text-red-700 rounded-lg text-[12px]">
                  {formError}
                </div>
              )}

              <div className="grid grid-cols-4 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-gray-700 mb-1">
                    Amount (VND) *
                  </label>
                  <input
                    type="number"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                    placeholder="Enter amount"
                    required
                    min="1"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-gray-700 mb-1">
                    Payment Method *
                  </label>
                  <select
                    value={formData.paymentMethod}
                    onChange={(e) => setFormData({ ...formData, paymentMethod: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="cash">Cash</option>
                    <option value="card">Card</option>
                    <option value="bank_transfer">Bank Transfer</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-gray-700 mb-1">
                    Payment Date *
                  </label>
                  <input
                    type="date"
                    value={formData.paymentDate}
                    onChange={(e) => setFormData({ ...formData, paymentDate: e.target.value })}
                    max={new Date().toISOString().split('T')[0]}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-gray-700 mb-1">
                    Notes
                  </label>
                  <input
                    type="text"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="Optional notes"
                    maxLength={200}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[12px] focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2 mt-3">
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  disabled={submitting}
                  className="px-3 py-1.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-[12px] font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-3 py-1.5 bg-gray-600 text-white rounded-lg hover:bg-gray-700 text-[12px] font-medium disabled:opacity-50 flex items-center gap-1"
                >
                  {submitting ? (
                    <>
                      <div className="animate-spin h-3 w-3 border-2 border-white border-t-transparent rounded-full"></div>
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="w-3 h-3" />
                      Save as Pending
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={(e) => handleSubmit(e, true)}
                  disabled={submitting}
                  className="px-3 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[12px] font-medium disabled:opacity-50 flex items-center gap-1"
                >
                  {submitting ? (
                    <>
                      <div className="animate-spin h-3 w-3 border-2 border-white border-t-transparent rounded-full"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-3 h-3" />
                      Pay & Complete
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                <p className="font-medium">Error loading payments</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Payments Table */}
          {!loading && !error && (
            <div className="p-6">
              {payments.length > 0 ? (
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Payment ID
                        </th>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Method
                        </th>
                        <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Amount
                        </th>
                        <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Notes
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {payments.map((payment) => (
                        <tr key={payment.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3">
                            <span className="text-[13px] font-semibold text-blue-600">
                              {payment.paymentNumber}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-[12px] text-gray-600">
                              {formatDate(payment.paymentDate)}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-[12px] text-gray-700">
                              {getPaymentMethodLabel(payment.paymentMethod)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-[14px] font-semibold text-gray-900">
                              {formatCurrency(payment.amount)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            {getStatusBadge(payment.status)}
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-[12px] text-gray-500 truncate block max-w-[200px]">
                              {payment.notes || '-'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-16 text-center">
                  <CreditCard className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-4 text-[13px] text-gray-500">No payments found for this order</p>
                  <button
                    onClick={handleOpenAddForm}
                    className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-[12px] font-medium"
                  >
                    <Plus className="w-4 h-4" />
                    Add First Payment
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
          <div className="text-[12px] text-gray-500">
            {payments.length} payment{payments.length !== 1 ? 's' : ''} recorded
          </div>
          <div className="flex items-center gap-2">
            {!showAddForm && remainingBalance > 0 && (
              <button
                onClick={handleOpenAddForm}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-[12px] font-medium"
              >
                <Plus className="w-4 h-4" />
                Add Payment
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-100 text-[12px] font-medium"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};
