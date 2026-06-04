import React, { useState, useEffect } from 'react';
import posDataService from '../../services/posDataService';

export const POSHeldOrdersModal = ({ isOpen, onClose, onLoadOrder, currentEmployee }) => {
  const [heldOrders, setHeldOrders] = useState([]);
  const [loading, setLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState({});
  const [error, setError] = useState(null);
  const [customerNames, setCustomerNames] = useState({});
  const [employeeNames, setEmployeeNames] = useState({});

  useEffect(() => {
    if (isOpen) {
      fetchHeldOrders();
    }
  }, [isOpen]);

  const fetchHeldOrders = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await posDataService.getOrdersByStatus('draft', currentEmployee?.id);

      if (result.status === 'success' || result.success) {
        const orders = result.data?.orders || result.data || [];

        // List endpoint returns orders WITHOUT details — fetch each order's details
        const enrichedOrders = await Promise.all(
          orders.map(async (order) => {
            try {
              const detailRes = await posDataService.getOrderById(order.id);
              const fullOrder = detailRes.data?.order || detailRes.data;
              return fullOrder || order;
            } catch {
              return order; // Fallback to list data if detail fetch fails
            }
          })
        );

        setHeldOrders(enrichedOrders);

        // Enrich customer names — batch fetch unique customerIds
        const uniqueCustomerIds = [...new Set(
          enrichedOrders.map(o => o.customerId).filter(id => id && id !== 'virtual-guest')
        )];

        if (uniqueCustomerIds.length > 0) {
          const customerResults = await Promise.all(
            uniqueCustomerIds.map(cid =>
              posDataService.getCustomerById(cid)
                .then(res => {
                  const c = res.data?.customer || res.data;
                  return c ? { id: cid, name: c.fullName, type: c.customerType } : null;
                })
                .catch(() => null)
            )
          );

          const names = {};
          customerResults.forEach(c => {
            if (c) names[c.id] = c;
          });
          setCustomerNames(names);
        }

        // Enrich employee names — batch fetch unique createdBy IDs
        const uniqueEmployeeIds = [...new Set(
          enrichedOrders.map(o => o.createdBy).filter(Boolean)
        )];

        if (uniqueEmployeeIds.length > 0) {
          const employeeResults = await Promise.all(
            uniqueEmployeeIds.map(eid =>
              posDataService.getEmployeeById(eid)
                .then(res => {
                  const emp = res.data?.employee || res.data;
                  return emp ? { id: eid, name: emp.fullName } : null;
                })
                .catch(() => null)
            )
          );

          const empNames = {};
          employeeResults.forEach(e => {
            if (e) empNames[e.id] = e;
          });
          setEmployeeNames(empNames);
        }
      } else {
        throw new Error(result.error?.message || 'Failed to fetch orders');
      }
    } catch (err) {
      console.error('Error fetching held orders:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatVND = (amount) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount);
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('vi-VN', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleLoadOrder = (order) => {
    onLoadOrder(order);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 bg-amber-50">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-bold text-gray-900 font-['Poppins',sans-serif]">
                Held Orders (Draft)
              </h2>
              <p className="text-sm text-gray-600 mt-1 font-['Poppins',sans-serif]">
                Click on an order to load it back to cart
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-200 rounded-full transition-colors"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-600"></div>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <svg className="w-16 h-16 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-red-600 font-semibold mb-2 font-['Poppins',sans-serif]">Failed to load orders</p>
              <p className="text-gray-600 text-sm mb-4 font-['Poppins',sans-serif]">{error}</p>
              <button
                onClick={fetchHeldOrders}
                className="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors font-['Poppins',sans-serif]"
              >
                Try Again
              </button>
            </div>
          ) : heldOrders.length === 0 ? (
            <div className="text-center py-12">
              <svg className="w-16 h-16 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-gray-600 font-semibold font-['Poppins',sans-serif]">No held orders</p>
              <p className="text-gray-500 text-sm mt-2 font-['Poppins',sans-serif]">Use "Hold" button (F8) to save orders for later</p>
            </div>
          ) : (
            <div className="space-y-3">
              {heldOrders.map((order) => (
                <div
                  key={order._id || order.id}
                  onClick={() => handleLoadOrder(order)}
                  className="bg-white border-2 border-gray-200 rounded-lg p-4 hover:border-amber-500 hover:shadow-lg transition-all cursor-pointer group"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold text-gray-900 font-['Poppins',sans-serif] group-hover:text-amber-600 transition-colors">
                          {order.orderNumber}
                        </span>
                        <span className="px-2 py-1 bg-amber-100 text-amber-700 rounded text-xs font-semibold font-['Poppins',sans-serif]">
                          DRAFT
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 mt-1 font-['Poppins',sans-serif]">
                        {formatDate(order.orderDate)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-amber-600 font-['Poppins',sans-serif]">
                        {formatVND(order.total)}
                      </p>
                      {order.discountPercentage > 0 && (
                        <p className="text-xs text-green-600 font-semibold font-['Poppins',sans-serif]">
                          -{order.discountPercentage}% discount
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="border-t border-gray-200 pt-3 mt-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-600 font-['Poppins',sans-serif]">Customer:</span>
                      <span className="text-sm font-semibold text-gray-900 font-['Poppins',sans-serif]">
                        {customerNames[order.customerId]
                          ? `${customerNames[order.customerId].name} (${customerNames[order.customerId].type})`
                          : !order.customerId
                            ? 'Walk-in Customer'
                            : `Customer #${order.customerId}`
                        }
                      </span>
                    </div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-gray-600 font-['Poppins',sans-serif]">Created by:</span>
                      <span className="text-sm font-semibold text-gray-900 font-['Poppins',sans-serif]">
                        {employeeNames[order.createdBy]?.name || `Employee #${order.createdBy || 'N/A'}`}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 font-['Poppins',sans-serif]">Items:</span>
                      <span className="text-sm font-semibold text-gray-900 font-['Poppins',sans-serif]">
                        {order.details?.length || 0} item(s)
                      </span>
                    </div>
                  </div>

                  {/* Order Items Preview */}
                  {order.details && order.details.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-gray-200">
                      <p className="text-xs text-gray-600 font-semibold mb-2 font-['Poppins',sans-serif]">Items:</p>
                      <div className="space-y-1">
                        {order.details.slice(0, 3).map((detail, index) => (
                          <div key={index} className="flex justify-between text-xs text-gray-700 font-['Poppins',sans-serif]">
                            <span className="truncate flex-1">
                              • {detail.productName || `Product #${detail.productId}`}
                              {detail.batchId && (
                                <span className="ml-1 text-orange-600">
                                  (Batch #{detail.batchId})
                                </span>
                              )}
                            </span>
                            <span className="ml-2 font-semibold">
                              x{detail.quantity}
                            </span>
                          </div>
                        ))}
                        {order.details.length > 3 && (
                          <p className="text-xs text-gray-500 italic font-['Poppins',sans-serif]">
                            +{order.details.length - 3} more...
                          </p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Click indicator & Actions */}
                  <div className="mt-3 pt-3 border-t border-gray-200 flex items-center justify-between">
                    <span className="text-xs text-gray-400 font-['Poppins',sans-serif] group-hover:text-amber-600 transition-colors">
                      Click to load this order
                    </span>
                    <button
                      onClick={async (e) => {
                        e.stopPropagation();
                        if (window.confirm(`Are you sure you want to delete draft order ${order.orderNumber}?`)) {
                          try {
                            setDeleteLoading(prev => ({ ...prev, [order.id]: true }));
                            await posDataService.deleteOrder(order.id);
                            setHeldOrders(prev => prev.filter(o => o.id !== order.id));
                          } catch (err) {
                            alert(err.message || 'Failed to delete draft order');
                          } finally {
                            setDeleteLoading(prev => ({ ...prev, [order.id]: false }));
                          }
                        }
                      }}
                      disabled={deleteLoading[order.id]}
                      className="p-1 px-2 bg-red-50 text-red-650 text-red-600 border border-red-200 rounded text-xs hover:bg-red-100 disabled:opacity-50 transition-colors flex items-center gap-1 font-['Poppins',sans-serif]"
                      title="Delete Draft"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2M10 11v6M14 11v6" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                      <span>{deleteLoading[order.id] ? 'Deleting...' : 'Delete'}</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 flex justify-between items-center">
          <span className="text-sm text-gray-600 font-['Poppins',sans-serif]">
            {heldOrders.length} held order(s)
          </span>
          <button
            onClick={onClose}
            className="px-6 py-2 border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-100 transition-colors font-['Poppins',sans-serif]"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
