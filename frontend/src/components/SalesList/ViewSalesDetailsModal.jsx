import React, { useState } from 'react';
import ReactDOM from 'react-dom';
import { X, TrendingUp, ShoppingCart, Layers } from 'lucide-react';

export const ViewSalesDetailsModal = ({ product, onClose }) => {
  const [activeTab, setActiveTab] = useState('batches'); // 'batches' or 'orders'

  if (!product) return null;

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
    return new Date(dateString).toLocaleDateString('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
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

  const modalContent = (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]"
      onClick={onClose}
      style={{ zIndex: 9999 }}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-[85vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-green-50 to-blue-50">
          <div className="flex items-center gap-3">
            <div>
              <h3 className="text-[18px] font-semibold text-gray-900">
                Sales Details
              </h3>
              <div className="flex items-center gap-4 mt-1">
                <p className="text-[12px] text-gray-600">
                  <span className="font-medium">{product.productCode}</span> • {product.productName}
                </p>
                <span className="px-2 py-0.5 bg-green-100 text-green-800 text-[11px] font-medium rounded">
                  {product.categoryName}
                </span>
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

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4 px-6 py-4 bg-gray-50 border-b border-gray-200">
          <div className="bg-white rounded-lg p-3 shadow-sm">
            <p className="text-[11px] text-gray-500 uppercase tracking-wide">Total Sold</p>
            <p className="text-[20px] font-bold text-green-600 mt-1">
              {product.totalQuantity.toLocaleString()}
            </p>
          </div>
          <div className="bg-white rounded-lg p-3 shadow-sm">
            <p className="text-[11px] text-gray-500 uppercase tracking-wide">Avg Price</p>
            <p className="text-[16px] font-bold text-gray-900 mt-1">
              {formatCurrency(product.averagePrice)}
            </p>
          </div>
          <div className="bg-white rounded-lg p-3 shadow-sm">
            <p className="text-[11px] text-gray-500 uppercase tracking-wide">Total Revenue</p>
            <p className="text-[18px] font-bold text-blue-600 mt-1">
              {formatCurrency(product.totalRevenue)}
            </p>
          </div>
          <div className="bg-white rounded-lg p-3 shadow-sm">
            <p className="text-[11px] text-gray-500 uppercase tracking-wide">Total Orders</p>
            <p className="text-[20px] font-bold text-indigo-600 mt-1">
              {product.totalOrders}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 px-6 bg-white">
          <button
            onClick={() => setActiveTab('batches')}
            className={`flex items-center gap-2 px-4 py-3 text-[13px] font-medium transition-colors relative ${activeTab === 'batches'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
              }`}
          >
            <Layers className="w-4 h-4" />
            Batch Breakdown
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${activeTab === 'batches' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
              }`}>
              {product.batches?.length || 0}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('orders')}
            className={`flex items-center gap-2 px-4 py-3 text-[13px] font-medium transition-colors relative ${activeTab === 'orders'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-900'
              }`}
          >
            <ShoppingCart className="w-4 h-4" />
            Order History
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${activeTab === 'orders' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
              }`}>
              {product.orders?.length || 0}
            </span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto">
          {/* Batch Breakdown Tab */}
          {activeTab === 'batches' && (
            <div className="p-6">
              {product.batches && product.batches.length > 0 ? (
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Batch Code
                        </th>
                        <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Qty Sold
                        </th>
                        <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Unit Price
                        </th>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Expiry Date
                        </th>
                        <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Total Revenue
                        </th>
                        <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Orders
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {product.batches.map((batch, idx) => (
                        <tr key={batch.batchId || idx} className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3">
                            <span className="text-[13px] font-medium text-gray-900">
                              {batch.batchCode}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-[13px] font-semibold text-green-600">
                              {batch.quantitySold.toLocaleString()}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-[13px] text-gray-700">
                              {formatCurrency(batch.unitPrice)}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-[12px] text-gray-600">
                              {batch.expiryDate ? formatDate(batch.expiryDate) : 'N/A'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-[14px] font-semibold text-blue-600">
                              {formatCurrency(batch.revenue)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-indigo-100 text-[12px] font-semibold text-indigo-700">
                              {batch.orderCount}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-16 text-center">
                  <Layers className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-4 text-[13px] text-gray-500">
                    No batch data available
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Order History Tab */}
          {activeTab === 'orders' && (
            <div className="p-6">
              {product.orders && product.orders.length > 0 ? (
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Order Number
                        </th>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Customer
                        </th>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Order Date
                        </th>
                        <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Payment
                        </th>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Batch
                        </th>
                        <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Qty
                        </th>
                        <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Unit Price
                        </th>
                        <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Subtotal
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {product.orders.map((order, idx) => (
                        <tr key={order.orderId || idx} className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3">
                            <span className="text-[13px] font-semibold text-blue-600">
                              {order.orderNumber}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <div>
                              <p className="text-[13px] font-medium text-gray-900">
                                {order.customerName}
                              </p>
                              <p className="text-[11px] text-gray-500">
                                {order.customerPhone}
                              </p>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-[12px] text-gray-600">
                              {formatDate(order.orderDate)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            {getStatusBadge(order.status)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            {getPaymentStatusBadge(order.paymentStatus)}
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-[12px] font-mono text-gray-700 bg-gray-100 px-2 py-1 rounded">
                              {order.batchCode}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-[13px] font-semibold text-green-600">
                              {order.quantitySold}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-[13px] text-gray-700">
                              {formatCurrency(order.unitPrice)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-[14px] font-semibold text-blue-600">
                              {formatCurrency(order.subtotal)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-16 text-center">
                  <ShoppingCart className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-4 text-[13px] text-gray-500">
                    No order history available
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return ReactDOM.createPortal(
    modalContent,
    document.body
  );
};
