import React, { useState, useEffect } from 'react';
import orderService from '../../services/orderService';
import orderDetailService from '../../services/orderDetailService';
import customerService from '../../services/customerService';
import employeeService from '../../services/employeeService';
/**
 * InvoiceOrderModal Component
 * Hiển thị chi tiết hóa đơn của order với đầy đủ thông tin
 * 
 * Logic Flow (tương tự InvoicePurchaseModal):
 * 1. Nhận order từ props
 * 2. Fetch full order data với populated fields (customer, createdBy)
 * 3. Fetch order details từ orderDetailService.getDetailsByOrder()
 * 4. Hiển thị invoice với:
 *    - Order info (orderNumber, orderDate)
 *    - Customer info (fullName, phone, customerType, shipping address)
 *    - Items table (product, quantity, unitPrice, total)
 *    - Subtotal, discount (auto from customerType), shipping fee, total
 *    - Created by (employee fullName)
 * 5. Hỗ trợ print invoice
 */
export const InvoiceOrderModal = ({ order, onClose, onViewItems }) => {
  const [fullOrder, setFullOrder] = useState(null);
  const [orderDetails, setOrderDetails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [customerInfo, setCustomerInfo] = useState(null);
  const [createdByName, setCreatedByName] = useState('');

  useEffect(() => {
    const fetchFullOrder = async () => {
      if (!order) return;

      try {
        setLoading(true);

        // Fetch full order
        const orderResponse = await orderService.getOrderById(order.id || order._id);

        let orderData = null;
        if (orderResponse.status === 'success' && orderResponse.data?.order) {
          orderData = orderResponse.data.order;
        } else if (orderResponse.data?.order) {
          orderData = orderResponse.data.order;
        } else if (orderResponse.order) {
          orderData = orderResponse.order;
        } else {
          orderData = order;
        }

        setFullOrder(orderData);

        // Customer enrichment
        const custId = orderData?.customerId || orderData?.customer_id;
        if (custId && typeof custId === 'number') {
          try {
            const custRes = await customerService.getCustomerById(custId);
            const cust = custRes.data?.customer || custRes.data || custRes;
            setCustomerInfo({
              fullName: cust.full_name || cust.fullName || `Customer #${custId}`,
              phone: cust.phone || '',
              email: cust.email || '',
              customerType: cust.customer_type || cust.customerType || 'guest'
            });
          } catch { setCustomerInfo({ fullName: `Customer #${custId}`, phone: '', email: '', customerType: 'guest' }); }
        }

        // Employee enrichment for createdBy
        const empId = orderData?.createdBy;
        if (empId === -1) {
          setCreatedByName('Customer (Online)');
        } else if (empId && typeof empId === 'number') {
          try {
            const empRes = await employeeService.getEmployeeById(empId);
            const emp = empRes.data?.employee || empRes.data || empRes;
            setCreatedByName(emp.full_name || emp.fullName || emp.username || `User #${empId}`);
          } catch { setCreatedByName(`User #${empId}`); }
        }

        // Fetch order details
        const detailsResponse = await orderDetailService.getDetailsByOrder(order.id || order._id);

        let detailsData = [];
        if (detailsResponse.data?.details) {
          detailsData = detailsResponse.data.details;
        } else if (detailsResponse.data?.orderDetails) {
          detailsData = detailsResponse.data.orderDetails;
        } else if (Array.isArray(detailsResponse.data)) {
          detailsData = detailsResponse.data;
        } else if (Array.isArray(detailsResponse)) {
          detailsData = detailsResponse;
        }

        setOrderDetails(detailsData);
      } catch (error) {
        console.error('Error fetching order data:', error);
        setFullOrder(order);
        setOrderDetails([]);
      } finally {
        setLoading(false);
      }
    };

    fetchFullOrder();
  }, [order]);

  if (!order) return null;

  if (loading || !fullOrder) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <p className="text-[14px] font-['Poppins',sans-serif] text-gray-600">Loading invoice...</p>
        </div>
      </div>
    );
  }

  // Use fullOrder instead of order
  const ord = fullOrder;

  // Tính toán các giá trị từ orderDetails
  // Backend structure: orderDetails[] với mỗi detail có {quantity, unitPrice}
  const details = orderDetails || [];

  // Subtotal = tổng của tất cả detail (quantity * unitPrice)
  const subtotal = details.reduce((sum, detail) => {
    const unitPrice = detail.unitPrice || detail.unit_price || 0;
    const itemTotal = detail.quantity * unitPrice;
    return sum + parseFloat(itemTotal);
  }, 0);

  // Discount percentage từ customer type (đã được backend tính sẵn)
  const discountPercentage = parseFloat(ord.discountPercentage) || 0;
  const discountAmount = subtotal * (discountPercentage / 100);

  // Shipping fee từ backend
  const shippingFee = parseFloat(ord.shippingFee) || 0;

  // Total = subtotal - discount + shipping
  const total = ord.totalAmount
    ? parseFloat(ord.totalAmount)
    : (ord.total ? parseFloat(ord.total) : subtotal - discountAmount + shippingFee);

  const invoiceValues = {
    subtotal,
    discount: discountAmount,
    discountPercentage,
    shippingFee,
    total
  };

  // Format currency VND
  const formatCurrency = (amount) => {
    if (amount === null || amount === undefined) return '₫0';
    return `₫${amount.toLocaleString('vi-VN')}`;
  };

  const handlePrintInvoice = () => {
    const printContent = document.getElementById('order-invoice-content');
    if (printContent) {
      const printWindow = window.open('', '', 'width=800,height=600');
      printWindow.document.write('<html><head><title>Order Invoice</title>');
      printWindow.document.write('<style>body{font-family:Arial,sans-serif;padding:20px;}</style>');
      printWindow.document.write('</head><body>');
      printWindow.document.write(printContent.innerHTML);
      printWindow.document.write('</body></html>');
      printWindow.document.close();
      printWindow.print();
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-gray-200">
          <h3 className="text-[16px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
            Order Invoice
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M15 5L5 15M5 5L15 15" stroke="#6B7280" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Invoice Body */}
        <div className="overflow-y-auto max-h-[calc(90vh-180px)] p-8 bg-white" id="order-invoice-content">
          {/* Invoice Header */}
          <div className="text-center mb-6 border-b-2 border-blue-600 pb-4">
            <h1 className="text-[24px] font-bold font-['Poppins',sans-serif] text-blue-600 uppercase tracking-wider">
              SALES INVOICE
            </h1>
          </div>

          {/* Invoice Info */}
          <div className="grid grid-cols-2 gap-4 mb-6 text-[13px]">
            <div>
              <p className="font-['Poppins',sans-serif]">
                <span className="font-semibold text-blue-600">Order Number:</span> {ord.orderNumber || ord.id}
              </p>
            </div>
            <div className="text-right">
              <p className="font-['Poppins',sans-serif]">
                <span className="font-semibold text-blue-600">Order Date:</span> {formatDate(ord.orderDate)}
              </p>
            </div>
          </div>

          {/* Customer Info (Enriched) */}
          <div className="mb-6 space-y-2">
            <p className="text-[14px] font-['Poppins',sans-serif]">
              <span className="font-semibold text-blue-600">Customer Name:</span> {customerInfo?.fullName || ord.customer?.fullName || 'N/A'}
            </p>
            {(customerInfo?.phone || ord.customer?.phone) && (
              <p className="text-[13px] font-['Poppins',sans-serif]">
                <span className="font-semibold text-blue-600">Phone:</span> {customerInfo?.phone || ord.customer?.phone}
              </p>
            )}
            {(customerInfo?.email || ord.customer?.email) && (
              <p className="text-[13px] font-['Poppins',sans-serif]">
                <span className="font-semibold text-blue-600">Email:</span> {customerInfo?.email || ord.customer?.email}
              </p>
            )}
            {(customerInfo?.customerType || ord.customer?.customerType) && (
              <p className="text-[13px] font-['Poppins',sans-serif]">
                <span className="font-semibold text-blue-600">Customer Type:</span>
                <span className={`ml-2 capitalize font-medium ${
                  (customerInfo?.customerType || ord.customer?.customerType) === 'vip' ? 'text-amber-600' :
                  (customerInfo?.customerType || ord.customer?.customerType) === 'wholesale' ? 'text-emerald-600' :
                  (customerInfo?.customerType || ord.customer?.customerType) === 'retail' ? 'text-blue-600' :
                    'text-gray-600'
                }`}>
                  {customerInfo?.customerType || ord.customer?.customerType}
                </span>
              </p>
            )}
            <p className="text-[13px] font-['Poppins',sans-serif]">
              <span className="font-semibold text-blue-600">Delivery Type:</span>
              <span className={`ml-2 capitalize ${ord.deliveryType === 'delivery' ? 'text-emerald-600' : 'text-blue-600'
                }`}>
                {ord.deliveryType || 'N/A'}
              </span>
            </p>
            {ord.deliveryType === 'delivery' && ord.shippingAddress && (
              <p className="text-[13px] font-['Poppins',sans-serif]">
                <span className="font-semibold text-blue-600">Shipping Address:</span>
                <span className="ml-2 text-gray-700">{ord.shippingAddress}</span>
              </p>
            )}
            <p className="text-[13px] font-['Poppins',sans-serif]">
              <span className="font-semibold text-blue-600">Status:</span>
              <span className={`ml-2 capitalize font-medium ${ord.status === 'pending' ? 'text-amber-600' :
                ord.status === 'processing' ? 'text-blue-600' :
                  ord.status === 'shipping' ? 'text-purple-600' :
                    ord.status === 'delivered' ? 'text-emerald-600' :
                      'text-red-600'
                }`}>
                {ord.status || 'N/A'}
              </span>
            </p>
          </div>

          {/* Items Table */}
          <div className="mb-6">
            <table className="w-full border-collapse border border-gray-300">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-center">
                    No.
                  </th>
                  <th className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-left">
                    Product Name
                  </th>
                  <th className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-center">
                    Batch
                  </th>
                  <th className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-center">
                    Quantity
                  </th>
                  <th className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-right">
                    Unit Price
                  </th>
                  <th className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-right">
                    Amount
                  </th>
                </tr>
              </thead>
              <tbody>
                {details && details.length > 0 ? (
                  details.map((detail, idx) => {
                    // Microservice: flat fields (productName, batchId, unit_price)
                    // Monolith: nested (product.name, batch.batchCode)
                    const productName = detail.productName || detail.product_name || detail.product?.name || 'N/A';
                    const batchLabel = detail.batchId ? `Batch #${detail.batchId}` : (detail.batch?.batchCode || 'N/A');
                    const quantity = detail.quantity || 0;
                    const unitPrice = detail.unitPrice || detail.unit_price || 0;
                    const itemTotal = quantity * unitPrice;

                    return (
                      <tr key={detail._id || detail.id || idx}>
                        <td className="border border-gray-300 px-3 py-2 text-[12px] font-['Poppins',sans-serif] text-center">
                          {idx + 1}
                        </td>
                        <td className="border border-gray-300 px-3 py-2 text-[12px] font-['Poppins',sans-serif]">
                          {productName}
                        </td>
                        <td className="border border-gray-300 px-3 py-2 text-[11px] font-['Poppins',sans-serif] text-center text-gray-600">
                          {batchLabel}
                        </td>
                        <td className="border border-gray-300 px-3 py-2 text-[12px] font-['Poppins',sans-serif] text-center">
                          {quantity}
                        </td>
                        <td className="border border-gray-300 px-3 py-2 text-[12px] font-['Poppins',sans-serif] text-right">
                          {formatCurrency(unitPrice)}
                        </td>
                        <td className="border border-gray-300 px-3 py-2 text-[12px] font-['Poppins',sans-serif] text-right">
                          {formatCurrency(itemTotal)}
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="6" className="border border-gray-300 px-3 py-4 text-center text-[12px] text-gray-500">
                      No items found
                    </td>
                  </tr>
                )}
                {/* Subtotal Row */}
                <tr className="bg-gray-50">
                  <td colSpan="5" className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-right">
                    Subtotal:
                  </td>
                  <td className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-right">
                    {formatCurrency(invoiceValues.subtotal)}
                  </td>
                </tr>
                {/* Discount Row - Chỉ hiển thị khi có discount */}
                {invoiceValues.discountPercentage > 0 && (
                  <tr className="bg-gray-50">
                    <td colSpan="5" className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-right text-green-600">
                      Discount ({invoiceValues.discountPercentage}%) - {(customerInfo?.customerType || ord.customer?.customerType || 'N/A').toUpperCase()}:
                    </td>
                    <td className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-right text-green-600">
                      -{formatCurrency(invoiceValues.discount)}
                    </td>
                  </tr>
                )}
                {/* Shipping Row */}
                <tr className="bg-gray-50">
                  <td colSpan="5" className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-right">
                    Shipping Fee:
                  </td>
                  <td className="border border-gray-300 px-3 py-2 text-[12px] font-semibold font-['Poppins',sans-serif] text-right">
                    {invoiceValues.shippingFee > 0 ? (
                      formatCurrency(invoiceValues.shippingFee)
                    ) : (
                      <span className="text-green-600">FREE</span>
                    )}
                  </td>
                </tr>
                {/* Total Row */}
                <tr className="bg-blue-50">
                  <td colSpan="5" className="border border-gray-300 px-3 py-2 text-[14px] font-bold font-['Poppins',sans-serif] text-right text-blue-600">
                    TOTAL:
                  </td>
                  <td className="border border-gray-300 px-3 py-2 text-[14px] font-bold font-['Poppins',sans-serif] text-right text-blue-600">
                    {formatCurrency(invoiceValues.total)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Payment Status */}
          {ord.paymentStatus && (
            <div className="mb-6 p-3 bg-gray-50 rounded-lg">
              <div className="flex justify-between items-center text-[13px] font-['Poppins',sans-serif]">
                <span className="font-semibold text-gray-700">Payment Status:</span>
                <span className={`font-semibold uppercase ${ord.paymentStatus === 'paid' ? 'text-green-600' :
                  ord.paymentStatus === 'partial' ? 'text-amber-600' :
                    'text-red-600'
                  }`}>
                  {ord.paymentStatus}
                </span>
              </div>
            </div>
          )}

          {/* Notes */}
          {ord.notes && (
            <div className="mb-6">
              <p className="text-[13px] font-semibold font-['Poppins',sans-serif] text-gray-700 mb-2">
                Notes:
              </p>
              <p className="text-[12px] font-['Poppins',sans-serif] text-gray-600 p-3 bg-gray-50 rounded-lg">
                {ord.notes}
              </p>
            </div>
          )}

          {/* Signature Section */}
          <div className="mt-8 text-center">
            <p className="text-[13px] font-['Poppins',sans-serif] text-gray-600 mb-12">
              Created by
            </p>
            <p className="text-[14px] font-semibold font-['Poppins',sans-serif] text-blue-600">
              {(() => {
                if (!ord.createdBy) return 'N/A';
                // Microservice: createdBy is a BIGINT (number)
                if (typeof ord.createdBy === 'number') return createdByName || `User #${ord.createdBy}`;
                // Monolith: createdBy is a populated object
                if (typeof ord.createdBy === 'object') {
                  return ord.createdBy.fullName || ord.createdBy.employeeCode || 'N/A';
                }
                return String(ord.createdBy);
              })()}
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-between items-center gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-[13px] font-['Poppins',sans-serif] font-medium transition-colors"
          >
            Close
          </button>
          <div className="flex gap-3">
            <button
              onClick={handlePrintInvoice}
              className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif] font-medium transition-colors flex items-center gap-2"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="2" width="10" height="3" stroke="currentColor" strokeWidth="1.5" />
                <rect x="2" y="5" width="12" height="6" rx="1" stroke="currentColor" strokeWidth="1.5" />
                <rect x="4" y="9" width="8" height="5" stroke="currentColor" strokeWidth="1.5" />
              </svg>
              Print Invoice
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
