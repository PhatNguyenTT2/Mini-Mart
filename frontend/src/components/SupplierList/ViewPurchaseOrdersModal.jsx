import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { X, ShoppingBag, FileText } from 'lucide-react';
import supplierService from '../../services/supplierService';
import { InvoicePurchaseModal } from '../PurchaseOrderList/InvoicePurchaseModal';

export const ViewPurchaseOrdersModal = ({ supplier, onClose }) => {
  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPurchaseOrder, setSelectedPurchaseOrder] = useState(null);
  const [showInvoice, setShowInvoice] = useState(false);

  useEffect(() => {
    if (supplier) {
      loadSupplierPurchaseOrders();
    }
  }, [supplier]);

  const loadSupplierPurchaseOrders = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch supplier with purchase orders populated
      const response = await supplierService.getSupplierById(supplier.id);
      const supplierData = response?.data?.supplier || {};
      const poData = supplierData.purchaseOrders || [];

      console.log('Supplier purchase orders loaded:', poData.length);

      setPurchaseOrders(poData);
    } catch (err) {
      console.error('Error loading purchase orders:', err);
      setError(err.response?.data?.error?.message || err.response?.data?.message || 'Failed to load purchase orders');
    } finally {
      setLoading(false);
    }
  };

  if (!supplier) return null;

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
      day: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      draft: { bg: 'bg-gray-100', text: 'text-gray-800', label: 'Draft' },
      pending: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Pending' },
      approved: { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Approved' },
      received: { bg: 'bg-green-100', text: 'text-green-800', label: 'Received' },
      cancelled: { bg: 'bg-red-100', text: 'text-red-800', label: 'Cancelled' },
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
      unpaid: { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Unpaid' },
      partial: { bg: 'bg-orange-100', text: 'text-orange-800', label: 'Partial' },
      paid: { bg: 'bg-green-100', text: 'text-green-800', label: 'Paid' },
    };
    const config = statusMap[status?.toLowerCase()] || { bg: 'bg-gray-100', text: 'text-gray-800', label: status };
    return (
      <span className={`px-2.5 py-1 rounded-full text-[11px] font-semibold uppercase ${config.bg} ${config.text}`}>
        {config.label}
      </span>
    );
  };

  const getPaymentTermsBadge = (terms) => {
    const termsMap = {
      cod: { bg: 'bg-green-50', text: 'text-green-700', label: 'COD' },
      net15: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Net 15' },
      net30: { bg: 'bg-indigo-50', text: 'text-indigo-700', label: 'Net 30' },
      net60: { bg: 'bg-purple-50', text: 'text-purple-700', label: 'Net 60' },
      net90: { bg: 'bg-pink-50', text: 'text-pink-700', label: 'Net 90' },
    };
    const config = termsMap[terms?.toLowerCase()] || { bg: 'bg-gray-50', text: 'text-gray-700', label: terms };
    return (
      <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${config.bg} ${config.text}`}>
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
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-purple-50 to-indigo-50">
          <div className="flex items-center gap-4">
            <div>
              <h3 className="text-[18px] font-semibold text-gray-900">
                Supplier Purchase Order History
              </h3>
              <div className="flex items-center gap-4 mt-1">
                <p className="text-[13px] text-gray-700">
                  <span className="font-semibold">{supplier.companyName}</span>
                </p>
                <span className="text-[12px] text-gray-500">
                  {supplier.supplierCode}
                </span>
                {getPaymentTermsBadge(supplier.paymentTerms)}
                {supplier.phone && (
                  <span className="text-[12px] text-gray-600">
                    {supplier.phone}
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
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
            </div>
          )}

          {error && (
            <div className="p-6">
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                <p className="font-medium">Error loading purchase orders</p>
                <p className="text-sm mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Purchase Orders Table */}
          {!loading && !error && (
            <div className="p-6">
              {purchaseOrders.length > 0 ? (
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          PO Number
                        </th>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Order Date
                        </th>
                        <th className="px-4 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Expected Delivery
                        </th>
                        <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Payment Status
                        </th>
                        <th className="px-4 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Total Price
                        </th>
                        <th className="px-4 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {purchaseOrders.map((po) => (
                        <tr key={po._id || po.id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-3">
                            <span className="text-[13px] font-semibold text-purple-600">
                              {po.poNumber}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-[12px] text-gray-600">
                              {formatDate(po.orderDate)}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-[12px] text-gray-600">
                              {formatDate(po.expectedDeliveryDate)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">{getStatusBadge(po.status)}</td>
                          <td className="px-4 py-3 text-center">
                            {getPaymentStatusBadge(po.paymentStatus)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <span className="text-[14px] font-semibold text-purple-600">
                              {formatCurrency(po.totalPrice)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center">
                            <button
                              onClick={() => {
                                setSelectedPurchaseOrder(po);
                                setShowInvoice(true);
                              }}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-[11px] font-medium"
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
                  <ShoppingBag className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-4 text-[13px] text-gray-500">No purchase orders found for this supplier</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Invoice Modal */}
      {showInvoice && selectedPurchaseOrder && (
        <InvoicePurchaseModal
          purchaseOrder={selectedPurchaseOrder}
          onClose={() => {
            setShowInvoice(false);
            setSelectedPurchaseOrder(null);
          }}
        />
      )}
    </div>
  );

  return ReactDOM.createPortal(modalContent, document.body);
};
