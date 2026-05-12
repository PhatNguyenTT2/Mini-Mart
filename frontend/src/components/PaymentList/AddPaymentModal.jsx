import React, { useState, useEffect } from 'react';
import paymentService from '../../services/paymentService';
import orderService from '../../services/orderService';
import purchaseOrderService from '../../services/purchaseOrderService';

export const AddPaymentModal = ({ isOpen, onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    referenceType: 'PurchaseOrder',
    referenceId: '',
    amount: '',
    paymentMethod: 'bank_transfer',
    paymentDate: new Date().toISOString().split('T')[0],
    status: 'pending',
    notes: ''
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loadingReferences, setLoadingReferences] = useState(false);
  const [references, setReferences] = useState([]);
  const [selectedReference, setSelectedReference] = useState(null);
  const [referenceItems, setReferenceItems] = useState([]);
  const [completeImmediately, setCompleteImmediately] = useState(false);

  // Payment summary for partial payment support
  const [paymentSummary, setPaymentSummary] = useState({
    totalPrice: 0,
    totalPaid: 0,
    remainingBalance: 0,
    paymentsCount: 0
  });

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setFormData({
        referenceType: 'PurchaseOrder',
        referenceId: '',
        amount: '',
        paymentMethod: 'bank_transfer',
        paymentDate: new Date().toISOString().split('T')[0],
        status: 'pending',
        notes: ''
      });
      setError(null);
      setSelectedReference(null);
      setReferenceItems([]);
      setCompleteImmediately(false);
      setPaymentSummary({ totalPrice: 0, totalPaid: 0, remainingBalance: 0, paymentsCount: 0 });
      fetchReferences('PurchaseOrder');
    }
  }, [isOpen]);

  // Fetch references when referenceType changes
  useEffect(() => {
    if (isOpen && formData.referenceType) {
      fetchReferences(formData.referenceType);
    }
  }, [formData.referenceType, isOpen]);

  // Fetch reference details when referenceId changes
  useEffect(() => {
    if (formData.referenceId) {
      fetchReferenceDetails(formData.referenceType, formData.referenceId);
    } else {
      setSelectedReference(null);
      setPaymentSummary({ totalPrice: 0, totalPaid: 0, remainingBalance: 0, paymentsCount: 0 });
    }
  }, [formData.referenceId, formData.referenceType]);

  const fetchReferences = async (type) => {
    setLoadingReferences(true);
    try {
      let response;
      if (type === 'Order') {
        // Don't pass comma-separated status — backend does exact match
        // Fetch all, filter client-side
        response = await orderService.getAllOrders({});
      } else if (type === 'PurchaseOrder') {
        response = await purchaseOrderService.getAllPurchaseOrders({});
      }

      // Handle different response formats from microservices:
      // Order service: { status: 'success', data: { orders: [...] } }
      // PO service:    { success: true, data: [...] }
      let items = [];
      if (type === 'Order') {
        if (response?.data?.orders) {
          items = response.data.orders;
        } else if (response?.status === 'success' && response?.data) {
          items = Array.isArray(response.data) ? response.data : [];
        }
        // Filter: exclude cancelled, only show unpaid/partial
        items = items.filter(o =>
          o.status !== 'cancelled' && o.paymentStatus !== 'paid'
        );
      } else if (type === 'PurchaseOrder') {
        if (response?.success && Array.isArray(response?.data)) {
          items = response.data;
        } else if (response?.data?.purchaseOrders) {
          items = response.data.purchaseOrders;
        }
        // Filter: exclude cancelled, only show unpaid/partial
        items = items.filter(po =>
          po.status !== 'cancelled' && po.paymentStatus !== 'paid'
        );
      }
      setReferences(items);
    } catch (err) {
      console.error('Error fetching references:', err);
      setReferences([]);
    } finally {
      setLoadingReferences(false);
    }
  };

  const fetchReferenceDetails = async (type, id) => {
    try {
      let response;
      if (type === 'Order') {
        response = await orderService.getOrderById(id);
      } else if (type === 'PurchaseOrder') {
        response = await purchaseOrderService.getPurchaseOrderById(id);
      }

      // Extract item from different response formats:
      // Order:  { status: 'success', data: { order: {...} } }
      // PO:     { success: true, data: {...} }  (data IS the PO object)
      let item = null;
      if (type === 'Order') {
        item = response?.data?.order || null;
      } else if (type === 'PurchaseOrder') {
        // PO service returns data directly as the PO object (not wrapped)
        item = response?.data?.purchaseOrder || response?.data || null;
        // Avoid using raw response as item (check it has expected fields)
        if (item && !item.id && !item.totalPrice) item = null;
      }

      if (item) {
        setSelectedReference(item);

        // Store order items for payment payload (inventory deduction)
        if (type === 'Order' && item.details && Array.isArray(item.details)) {
          setReferenceItems(item.details.map(d => ({
            batchId: d.batchId,
            quantity: d.quantity,
            productName: d.productName
          })));
        } else {
          setReferenceItems([]);
        }

        // Calculate payment summary including existing payments
        const totalPrice = parseFloat(item.total || item.totalPrice || 0);

        // Fetch existing payments for this reference
        const paymentsResponse = await paymentService.getAllPayments({
          referenceType: type,
          referenceId: id,
          limit: 100
        });

        let totalPaid = 0;
        let paymentsCount = 0;

        if (paymentsResponse?.success && paymentsResponse?.data?.payments) {
          const completedPayments = paymentsResponse.data.payments.filter(
            p => p.status === 'completed'
          );
          totalPaid = completedPayments.reduce((sum, p) => sum + (parseFloat(p.amount) || 0), 0);
          paymentsCount = completedPayments.length;
        }

        const remainingBalance = Math.max(0, totalPrice - totalPaid);

        setPaymentSummary({
          totalPrice,
          totalPaid,
          remainingBalance,
          paymentsCount
        });

        // Auto-fill amount with remaining balance (for partial payment)
        setFormData(prev => ({
          ...prev,
          amount: remainingBalance > 0 ? remainingBalance.toString() : totalPrice.toString()
        }));
      }
    } catch (err) {
      console.error('Error fetching reference details:', err);
      setSelectedReference(null);
      setPaymentSummary({ totalPrice: 0, totalPaid: 0, remainingBalance: 0, paymentsCount: 0 });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.referenceType) {
      setError('Please select a reference type');
      return;
    }

    if (!formData.referenceId) {
      setError('Please select an order or purchase order');
      return;
    }

    const amountValue = parseFloat(formData.amount);
    if (!formData.amount || amountValue <= 0) {
      setError('Please enter a valid amount greater than 0');
      return;
    }

    // Validate amount doesn't exceed remaining balance
    if (amountValue > paymentSummary.remainingBalance && paymentSummary.remainingBalance > 0) {
      const confirmOverpay = window.confirm(
        `Amount (${formatCurrency(amountValue)}) exceeds remaining balance (${formatCurrency(paymentSummary.remainingBalance)}).\n\nDo you want to continue?`
      );
      if (!confirmOverpay) return;
    }

    if (!formData.paymentMethod) {
      setError('Please select a payment method');
      return;
    }

    if (!formData.paymentDate) {
      setError('Please select a payment date');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const paymentData = {
        referenceType: formData.referenceType,
        referenceId: formData.referenceId,
        amount: amountValue,
        paymentMethod: formData.paymentMethod,
        paymentDate: formData.paymentDate,
        status: completeImmediately ? 'completed' : 'pending',
        items: referenceItems,
        deliveryType: selectedReference?.deliveryType || 'pickup'
      };

      if (formData.notes.trim()) {
        paymentData.notes = formData.notes.trim();
      }

      let response;
      if (completeImmediately) {
        // Direct payment → auto-completes → triggers saga (payment.completed event)
        response = await paymentService.createDirectPayment(paymentData);
      } else {
        // Pending payment → admin approves later → manual status change to completed
        response = await paymentService.createPayment(paymentData);
      }

      if (onSuccess) {
        onSuccess(response);
      }
      onClose();
    } catch (err) {
      console.error('Error creating payment:', err);
      setError(err.response?.data?.error?.message || err.message || 'Failed to create payment. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));

    if (field === 'referenceType') {
      setFormData(prev => ({
        ...prev,
        referenceId: '',
        amount: ''
      }));
      setSelectedReference(null);
      setPaymentSummary({ totalPrice: 0, totalPaid: 0, remainingBalance: 0, paymentsCount: 0 });
    }
  };

  const handleQuickFill = (type) => {
    if (type === 'remaining') {
      setFormData(prev => ({
        ...prev,
        amount: paymentSummary.remainingBalance.toString()
      }));
    } else if (type === 'full') {
      setFormData(prev => ({
        ...prev,
        amount: paymentSummary.totalPrice.toString()
      }));
    }
  };

  const formatCurrency = (amount) => {
    if (amount === null || amount === undefined) return '-';
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
    }).format(amount);
  };

  const getStatusLabel = (status) => {
    const labels = {
      pending: 'Pending',
      shipping: 'Shipping',
      delivered: 'Delivered',
      approved: 'Approved',
      received: 'Received',
      draft: 'Draft'
    };
    return labels[status] || status;
  };

  const getPaymentStatusBadge = (paymentStatus) => {
    const styles = {
      unpaid: 'bg-red-100 text-red-700',
      pending: 'bg-yellow-100 text-yellow-700',
      partial: 'bg-orange-100 text-orange-700',
      paid: 'bg-green-100 text-green-700'
    };
    const labels = {
      unpaid: 'Unpaid',
      pending: 'Pending',
      partial: 'Partial Paid',
      paid: 'Fully Paid'
    };
    return (
      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${styles[paymentStatus] || 'bg-gray-100 text-gray-700'}`}>
        {labels[paymentStatus] || paymentStatus}
      </span>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 sticky top-0 bg-white z-10">
          <h2 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
            Create New Payment
          </h2>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
              {error}
            </div>
          )}

          {/* Reference Type */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Payment For <span className="text-red-500">*</span>
            </label>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="referenceType"
                  value="Order"
                  checked={formData.referenceType === 'Order'}
                  onChange={(e) => handleChange('referenceType', e.target.value)}
                  className="w-4 h-4 text-emerald-600 focus:ring-emerald-500"
                />
                <span className="text-[13px] font-['Poppins',sans-serif] text-[#212529]">Order (Sales)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="referenceType"
                  value="PurchaseOrder"
                  checked={formData.referenceType === 'PurchaseOrder'}
                  onChange={(e) => handleChange('referenceType', e.target.value)}
                  className="w-4 h-4 text-emerald-600 focus:ring-emerald-500"
                />
                <span className="text-[13px] font-['Poppins',sans-serif] text-[#212529]">Purchase Order</span>
              </label>
            </div>
          </div>

          {/* Reference Selection */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Select {formData.referenceType === 'Order' ? 'Order' : 'Purchase Order'} <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.referenceId}
              onChange={(e) => handleChange('referenceId', e.target.value)}
              required
              disabled={loadingReferences}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:bg-gray-100"
            >
              <option value="">
                {loadingReferences ? 'Loading...' : `Select ${formData.referenceType === 'Order' ? 'an order' : 'a purchase order'}`}
              </option>
              {references.map((ref) => (
                <option key={ref.id} value={ref.id}>
                  {formData.referenceType === 'Order' ? ref.orderNumber : (ref.poNumber || `PO-${String(ref.id).padStart(4, '0')}`)} - {formatCurrency(ref.total || ref.totalPrice)} - {getStatusLabel(ref.status)}
                </option>
              ))}
            </select>
            {!loadingReferences && references.length === 0 && (
              <p className="mt-1 text-[11px] text-amber-600 font-['Poppins',sans-serif]">
                No available {formData.referenceType === 'Order' ? 'orders' : 'purchase orders'} found
              </p>
            )}
          </div>

          {/* Selected Reference Details with Payment Summary */}
          {selectedReference && (
            <div className="bg-gradient-to-r from-blue-50 to-emerald-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <p className="text-[12px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
                  {formData.referenceType === 'Order' ? 'Order' : 'Purchase Order'} Details
                </p>
                {getPaymentStatusBadge(selectedReference.paymentStatus || 'unpaid')}
              </div>

              {/* Details Grid */}
              <div className="grid grid-cols-2 gap-3 text-[12px] font-['Poppins',sans-serif] mb-4">
                <div>
                  <span className="text-gray-600">Number:</span>
                  <span className="ml-2 font-medium text-[#212529]">
                    {formData.referenceType === 'Order' ? selectedReference.orderNumber : (selectedReference.poNumber || `PO-${String(selectedReference.id).padStart(4, '0')}`)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-600">Status:</span>
                  <span className="ml-2 font-medium text-[#212529]">{getStatusLabel(selectedReference.status)}</span>
                </div>
              </div>

              {/* Payment Summary Section */}
              <div className="bg-white/70 rounded-lg p-3 space-y-2">
                <div className="flex items-center justify-between text-[12px]">
                  <span className="text-gray-600">Total Amount:</span>
                  <span className="font-semibold text-[#212529]">{formatCurrency(paymentSummary.totalPrice)}</span>
                </div>
                <div className="flex items-center justify-between text-[12px]">
                  <span className="text-gray-600">Already Paid ({paymentSummary.paymentsCount} payment{paymentSummary.paymentsCount !== 1 ? 's' : ''}):</span>
                  <span className="font-semibold text-emerald-600">{formatCurrency(paymentSummary.totalPaid)}</span>
                </div>
                <div className="border-t border-gray-200 pt-2 flex items-center justify-between text-[13px]">
                  <span className="font-medium text-gray-700">Remaining Balance:</span>
                  <span className={`font-bold ${paymentSummary.remainingBalance > 0 ? 'text-orange-600' : 'text-emerald-600'}`}>
                    {formatCurrency(paymentSummary.remainingBalance)}
                  </span>
                </div>
              </div>

              {/* Fully Paid Warning */}
              {paymentSummary.remainingBalance === 0 && paymentSummary.totalPaid > 0 && (
                <div className="mt-3 bg-emerald-100 border border-emerald-300 rounded-lg px-3 py-2">
                  <p className="text-[11px] text-emerald-700 font-medium">
                    This {formData.referenceType === 'Order' ? 'order' : 'purchase order'} is fully paid
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Payment Details */}
          <div className="grid grid-cols-2 gap-4">
            {/* Amount - Now Editable with Quick Fill Buttons */}
            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Payment Amount (VND) <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                value={formData.amount}
                onChange={(e) => handleChange('amount', e.target.value)}
                placeholder="Enter payment amount"
                required
                min="1"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
              {formData.amount && (
                <p className="mt-1 text-[11px] text-emerald-600 font-medium font-['Poppins',sans-serif]">
                  {formatCurrency(parseFloat(formData.amount))}
                </p>
              )}

              {/* Quick Fill Button - Show only one based on context */}
              {selectedReference && paymentSummary.totalPrice > 0 && (
                <div className="mt-2">
                  {paymentSummary.totalPaid > 0 && paymentSummary.remainingBalance > 0 ? (
                    // Has partial payment - show "Fill Remaining"
                    <button
                      type="button"
                      onClick={() => handleQuickFill('remaining')}
                      className="px-2 py-1 text-[10px] font-medium bg-orange-100 text-orange-700 rounded hover:bg-orange-200 transition-colors"
                    >
                      Fill Remaining ({formatCurrency(paymentSummary.remainingBalance)})
                    </button>
                  ) : paymentSummary.remainingBalance > 0 ? (
                    // No prior payments - show "Full Amount"
                    <button
                      type="button"
                      onClick={() => handleQuickFill('full')}
                      className="px-2 py-1 text-[10px] font-medium bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
                    >
                      Full Amount ({formatCurrency(paymentSummary.totalPrice)})
                    </button>
                  ) : null}
                </div>
              )}
            </div>

            {/* Payment Method */}
            <div>
              <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
                Payment Method <span className="text-red-500">*</span>
              </label>
              <select
                value={formData.paymentMethod}
                onChange={(e) => handleChange('paymentMethod', e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                <option value="bank_transfer">Bank Transfer</option>
                <option value="cash">Cash</option>
                <option value="card">Card</option>
              </select>
            </div>
          </div>

          {/* Payment Date */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Payment Date <span className="text-red-500">*</span>
            </label>
            <input
              type="date"
              value={formData.paymentDate}
              onChange={(e) => handleChange('paymentDate', e.target.value)}
              required
              max={new Date().toISOString().split('T')[0]}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>

          {/* Complete Immediately Toggle */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <label className="flex items-center gap-3 cursor-pointer">
                  <div className="relative">
                    <input
                      type="checkbox"
                      checked={completeImmediately}
                      onChange={(e) => setCompleteImmediately(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-gray-300 rounded-full peer peer-checked:bg-emerald-500 transition-colors"></div>
                    <div className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow peer-checked:translate-x-5 transition-transform"></div>
                  </div>
                  <div>
                    <span className="text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529]">
                      Complete Immediately
                    </span>
                    <p className="text-[11px] text-gray-500 font-['Poppins',sans-serif] mt-0.5">
                      {completeImmediately
                        ? 'Payment will be completed instantly and trigger order fulfillment'
                        : 'Payment will be created as "Pending" for manual approval'
                      }
                    </p>
                  </div>
                </label>
              </div>
            </div>
            {completeImmediately && formData.referenceType === 'Order' && (
              <div className="mt-3 bg-amber-100 border border-amber-300 rounded px-3 py-2">
                <p className="text-[10px] text-amber-800 font-medium font-['Poppins',sans-serif]">
                  Warning: This will automatically update order status:
                  {selectedReference?.deliveryType === 'delivery'
                    ? ' Draft → Shipping (stock reserved)'
                    : ' Draft → Delivered (stock deducted)'
                  }
                </p>
              </div>
            )}
          </div>

          {/* Status Display */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Payment Status
            </label>
            <div className={`w-full px-3 py-2 border rounded-lg text-[13px] font-['Poppins',sans-serif] ${
              completeImmediately
                ? 'bg-emerald-50 border-emerald-300 text-emerald-700 font-medium'
                : 'bg-gray-50 border-gray-300 text-gray-600'
            }`}>
              {completeImmediately ? 'Completed (auto)' : 'Pending (manual approval)'}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-[13px] font-medium font-['Poppins',sans-serif] text-[#212529] mb-2">
              Notes (Optional)
            </label>
            <textarea
              value={formData.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              placeholder="Enter payment notes (e.g., Partial payment 1 of 3)"
              rows={3}
              maxLength={500}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-[13px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
            />
            <div className="flex items-center justify-between mt-1">
              <p className="text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                Maximum 500 characters
              </p>
              <p className="text-[11px] text-gray-500 font-['Poppins',sans-serif]">
                {formData.notes.length}/500
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !formData.referenceId}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-medium disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  {completeImmediately ? 'Processing...' : 'Creating...'}
                </>
              ) : (
                completeImmediately ? 'Pay & Complete' : 'Create Payment'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
