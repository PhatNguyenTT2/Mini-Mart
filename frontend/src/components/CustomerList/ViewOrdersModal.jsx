import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { X, ShoppingCart, FileText } from 'lucide-react';
import orderService from '../../services/orderService';
import { InvoiceOrderModal } from '../OrderList/InvoiceOrderModal';

export const ViewOrdersModal = ({ customer, onClose }) => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [showInvoice, setShowInvoice] = useState(false);

  useEffect(() => {
    if (customer) {
      loadCustomerOrders();
    }
  }, [customer]);

  const loadCustomerOrders = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch orders from Order microservice: GET /orders?customer=ID
      const response = await orderService.getOrdersByCustomer(customer.id);

      const ordersData = response?.data?.orders || [];
      console.log('Customer orders loaded:', ordersData.length);

      setOrders(ordersData);
    } catch (err) {
      console.error('Error loading customer orders:', err);
      setError(err.response?.data?.error?.message || err.response?.data?.message || 'Failed to load orders');
    } finally {
      setLoading(false);
    }
  };

  if (!customer) return null;

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₫0';

    // Handle Mongoose Decimal128
    if (typeof amount === 'object' && amount.$numberDecimal) {
      return `₫${Number(amount.$numberDecimal).toLocaleString('vi-VN')}`;
    }

    if (typeof amount === 'object') {
      console.error('formatCurrency received unexpected object:', amount);
      return '₫0';
    }

    return `₫${Number(amount).toLocaleString('vi-VN')}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      draft: { bg: 'bg-gray-100', text: 'text-gray-800', label: 'Draft' },
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Pending' },
      shipping: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Shipping' },
      delivered: { bg: 'bg-green-100', text: 'text-green-800', label: 'Delivered' },
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

  const getPaymentStatusBadge = (status) => {
    const statusMap = {
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Pending' },
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

  const getCustomerTypeBadge = (type) => {
    const typeMap = {
      guest: { bg: 'bg-gray-100', text: 'text-gray-800', label: 'Guest' },
      retail: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Retail' },
      wholesale: { bg: 'bg-purple-100', text: 'text-purple-800', label: 'Wholesale' },
      vip: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'VIP' },
    };
    const config = typeMap[type?.toLowerCase()] || { bg: 'bg-gray-100', text: 'text-gray-800', label: type };
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
        className="bg-white rounded-lg shadow-xl max-w-7xl w-full mx-4 max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-center gap-4">
            <div>
              <h3 className="text-[18px] font-semibold text-gray-900">
                Customer Order History
              </h3>
              <div className="flex items-center gap-4 mt-1">
                <p className="text-[13px] text-gray-700">
                  <span className="font-semibold">{customer.fullName}</span>
                </p>
                <span className="text-[12px] text-gray-500">
                  {customer.customerCode}
                </span>
                {getCustomerTypeBadge(customer.customerType)}
                {customer.phone && (
                  <span className="text-[12px] text-gray-600">
                    {customer.phone}
                  </span>
                )}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

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
                <p className="font-medium">Error loading orders</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Orders List */}
          {!loading && !error && (
            <div className="p-6">
              {orders.length > 0 ? (
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Order Number
                        </th>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Payment
                        </th>
                        <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Items
                        </th>
                        <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Discount
                        </th>
                        <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Shipping
                        </th>
                        <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Total
                        </th>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Created By
                        </th>
                        <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {orders.map((order) => (
                        <tr key={order.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3">
                            <span className="text-[13px] font-semibold text-blue-600">
                              {order.orderNumber}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-[12px] text-gray-600">
                              {formatDate(order.orderDate)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">{getStatusBadge(order.status)}</td>
                          <td className="px-4 py-3 text-center">
                            {getPaymentStatusBadge(order.paymentStatus)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-indigo-100 text-[12px] font-semibold text-indigo-700">
                              {order.details?.length || 0}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-[12px] text-green-600 font-medium">
                              {order.discountPercentage}%
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-[13px] text-gray-700">
                              {formatCurrency(order.shippingFee)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-[14px] font-semibold text-blue-600">
                              {formatCurrency(order.total)}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div>
                              <p className="text-[12px] text-gray-700">
                                {typeof order.createdBy === 'object'
                                  ? (order.createdBy?.fullName || 'N/A')
                                  : order.createdBy ? `Staff #${order.createdBy}` : 'N/A'}
                              </p>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <button
                              onClick={() => {
                                setSelectedOrder(order);
                                setShowInvoice(true);
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-[11px] font-medium"
                              title="View Invoice"
                            >
                              <FileText className="w-3.5 h-3.5" />
                              Invoice
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-16 text-center">
                  <ShoppingCart className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-4 text-[13px] text-gray-500">No orders found for this customer</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Invoice Modal */}
      {showInvoice && selectedOrder && (
        <InvoiceOrderModal
          order={selectedOrder}
          onClose={() => {
            setShowInvoice(false);
            setSelectedOrder(null);
          }}
        />
      )}
    </div>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};
