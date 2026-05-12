import { useState, useCallback } from 'react';
import posDataService from '../services/posDataService';

/**
 * POS Payment Processing Hook.
 * Handles Cash/Card/VNPay payment flows, invoice modal.
 */
export function usePOSPayment({ existingOrder, setExistingOrder, setCart, setSelectedCustomer, showToast }) {
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [vnpayProcessing, setVnpayProcessing] = useState(false);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [invoiceOrder, setInvoiceOrder] = useState(null);

  // ========== PAYMENT METHOD SELECT ==========

  const handlePaymentMethodSelect = useCallback(async (paymentMethod) => {
    if (!existingOrder) {
      showToast('error', 'Order not found!');
      return;
    }

    const orderId = existingOrder.id;

    try {
      setShowPaymentModal(false);

      if (paymentMethod === 'bank_transfer') {
        console.log('VNPay flow selected');
        setExistingOrder(prev => ({
          ...prev,
          selectedPaymentMethod: 'bank_transfer',
          vnpayProcessing: true
        }));
        await handleVNPayPayment(orderId);
        return;
      }

      await handleCashCardPayment(orderId, paymentMethod);
    } catch (error) {
      console.error('Payment error:', error);
      const errorMessage = error.response?.data?.error?.message
        || error.error?.message
        || error.message
        || 'Failed to process payment';
      showToast('error', errorMessage);
      alert(`Payment failed: ${errorMessage}`);
      setShowPaymentModal(true);
    }
  }, [existingOrder, showToast, setExistingOrder]);

  // ========== VNPAY ==========

  const handleVNPayPayment = useCallback(async (orderId) => {
    try {
      setVnpayProcessing(true);
      console.log('Creating VNPay payment URL for order:', existingOrder.orderNumber);

      const result = await posDataService.createVNPayUrl(
        orderId,
        existingOrder.total,
        `Thanh toán ${existingOrder.orderNumber}`
      );

      const paymentUrl = result?.paymentUrl || result;

      if (!paymentUrl || typeof paymentUrl !== 'string') {
        throw new Error('Failed to get VNPay payment URL');
      }

      console.log('VNPay URL created, redirecting...');
      showToast('success', 'Chuyển đến VNPay...');

      setTimeout(() => {
        window.location.href = paymentUrl;
      }, 1500);
    } catch (error) {
      console.error('VNPay error:', error);
      setVnpayProcessing(false);
      throw error;
    }
  }, [existingOrder, showToast]);

  // ========== CASH/CARD ==========

  const handleCashCardPayment = useCallback(async (orderId, paymentMethod) => {
    try {
      console.log(`Processing ${paymentMethod} payment for order:`, existingOrder.orderNumber);

      // Fetch full order to get items[] for Saga inventory deduction
      const fullOrderResponse = await posDataService.getOrderById(orderId);
      if (fullOrderResponse.status !== 'success') throw new Error('Failed to fetch order details');

      const fullOrder = fullOrderResponse.data?.order || fullOrderResponse.data;
      const orderItems = (fullOrder.details || []).map(d => ({
        batchId: d.batchId,
        locationId: null,
        quantity: d.quantity
      }));

      // Create payment with full Saga payload
      const paymentResponse = await posDataService.createDirectPayment({
        orderId,
        amount: fullOrder.total,
        method: paymentMethod,
        items: orderItems,
        deliveryType: 'pickup',
        notes: `POS Payment - ${existingOrder.orderNumber}`
      });

      if (paymentResponse.status !== 'success') {
        throw new Error(paymentResponse.error?.message || 'Failed to create payment');
      }

      console.log('Payment created:', paymentResponse.data.payment.paymentNumber);
      // Note: Saga choreography auto-updates order status via payment.completed event

      fullOrder.paymentMethod = paymentMethod;

      setInvoiceOrder(fullOrder);
      setShowInvoiceModal(true);
      setCart([]);
      setSelectedCustomer(null);
      setExistingOrder(null);

      showToast('success', `Payment completed! Order: ${existingOrder.orderNumber}`);
    } catch (error) {
      console.error('Cash/Card error:', error);
      throw error;
    }
  }, [existingOrder, setCart, setSelectedCustomer, setExistingOrder, showToast]);

  // ========== VNPAY RETURN HANDLERS ==========

  const handleVNPayComplete = useCallback(async (order) => {
    setVnpayProcessing(false);

    try {
      const orderId = order.id;
      console.log('VNPay return callback - Processing order:', order.orderNumber);

      const fullOrderResponse = await posDataService.getOrderById(orderId);
      if (fullOrderResponse.status !== 'success') throw new Error('Failed to fetch order');

      const completeOrder = fullOrderResponse.data?.order || fullOrderResponse.data;

      if (completeOrder.paymentStatus === 'paid' || completeOrder.paymentStatus === 'completed') {
        console.log('Payment already processed');

        if (completeOrder.status !== 'delivered') {
          await posDataService.updateOrder(orderId, { status: 'delivered' });
        }

        completeOrder.paymentMethod = 'bank_transfer';
        setInvoiceOrder(completeOrder);
        setShowInvoiceModal(true);
        setShowPaymentModal(false);
        setCart([]);
        setSelectedCustomer(null);
        setExistingOrder(null);
        showToast('success', `Thanh toán VNPay thành công! Đơn hàng: ${order.orderNumber}`);
        return;
      }

      // Payment not created yet — create now via Saga-aware direct payment
      console.log('Creating payment record for VNPay transaction...');
      const orderItems = (completeOrder.details || []).map(d => ({
        batchId: d.batchId,
        locationId: null,
        quantity: d.quantity
      }));

      const paymentResponse = await posDataService.createDirectPayment({
        orderId,
        amount: completeOrder.total,
        method: 'bank_transfer',
        items: orderItems,
        deliveryType: 'pickup',
        notes: `VNPay Payment - ${order.orderNumber}`
      });

      if (paymentResponse.status !== 'success') {
        throw new Error(paymentResponse.error?.message || 'Failed to create payment');
      }

      await posDataService.updateOrder(orderId, { status: 'delivered', paymentStatus: 'paid' });

      const finalOrderResponse = await posDataService.getOrderById(orderId);
      const finalOrder = finalOrderResponse.data.order;
      finalOrder.paymentMethod = 'bank_transfer';

      setInvoiceOrder(finalOrder);
      setShowInvoiceModal(true);
      setShowPaymentModal(false);
      setCart([]);
      setSelectedCustomer(null);
      setExistingOrder(null);
      showToast('success', `Thanh toán VNPay thành công! Đơn hàng: ${order.orderNumber}`);
    } catch (error) {
      console.error('VNPay complete error:', error);
      if (existingOrder) {
        setExistingOrder(prev => ({ ...prev, vnpayProcessing: false }));
      }
      showToast('error', error.message || 'Có lỗi xảy ra khi xử lý thanh toán VNPay');
    }
  }, [existingOrder, setCart, setSelectedCustomer, setExistingOrder, showToast]);

  const handleVNPayFailed = useCallback(async (error) => {
    setVnpayProcessing(false);

    if (existingOrder && !existingOrder.wasHeldOrder) {
      console.log('Deleting new draft order...');
      try {
        await posDataService.deleteOrder(existingOrder.id);
        setExistingOrder(null);
      } catch (deleteError) {
        console.error('Failed to delete draft:', deleteError);
      }
    } else if (existingOrder) {
      setExistingOrder(prev => ({ ...prev, vnpayProcessing: false }));
    }

    showToast('error', error.message || 'Thanh toán VNPay thất bại');
  }, [existingOrder, setExistingOrder, showToast]);

  // ========== MODAL CLOSE ==========

  const handlePaymentModalClose = useCallback(() => {
    setShowPaymentModal(false);

    if (existingOrder && !existingOrder.wasHeldOrder) {
      console.log(`Payment cancelled - Order ${existingOrder.orderNumber} kept as draft`);
      showToast('info', `Order ${existingOrder.orderNumber} saved as held order`);
    }
  }, [existingOrder, showToast]);

  return {
    showPaymentModal,
    setShowPaymentModal,
    vnpayProcessing,
    showInvoiceModal,
    setShowInvoiceModal,
    invoiceOrder,
    setInvoiceOrder,
    handlePaymentMethodSelect,
    handleVNPayComplete,
    handleVNPayFailed,
    handlePaymentModalClose
  };
}
