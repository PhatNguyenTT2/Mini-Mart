import { useState, useRef, useEffect } from 'react';
import { InvoiceStockOutModal } from './InvoiceStockOutModal';
import { EditStockOutOrderModal } from './EditStockOutOrderModal';
import employeeService from '../../services/employeeService';

const StockOutList = ({
  stockOutOrders = [],
  onSort,
  sortField,
  sortOrder,
  onRefresh,
}) => {
  const [activeDropdown, setActiveDropdown] = useState(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 });
  const dropdownRef = useRef(null);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [invoiceModal, setInvoiceModal] = useState(null);
  const [editingOrder, setEditingOrder] = useState(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [employeeMap, setEmployeeMap] = useState({});

  // Resolve employee names (batch fetch)
  useEffect(() => {
    const ids = [...new Set(stockOutOrders.map(o => o.createdBy).filter(Boolean))];
    if (ids.length === 0) return;

    const unresolvedIds = ids.filter(id => !employeeMap[id]);
    if (unresolvedIds.length === 0) return;

    const resolve = async () => {
      const map = {};
      await Promise.all(unresolvedIds.map(async (id) => {
        try {
          const res = await employeeService.getEmployeeById(id);
          const emp = res.data || res;
          map[id] = emp.full_name || emp.fullName || emp.username || `User #${id}`;
        } catch {
          map[id] = `User #${id}`;
        }
      }));
      setEmployeeMap(prev => ({ ...prev, ...map }));
    };
    resolve();
  }, [stockOutOrders]);

  // Sort handler
  const handleSortClick = (field) => {
    if (onSort) onSort(field);
  };

  // Sort icon (matches PurchaseOrderList pattern)
  const getSortIcon = (field) => {
    if (sortField !== field) {
      return (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="ml-1">
          <path d="M6 3V9M6 3L4 5M6 3L8 5" stroke="#6B7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    }
    if (sortOrder === 'asc') {
      return (
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="ml-1">
          <path d="M6 9V3M6 3L4 5M6 3L8 5" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    }
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="ml-1">
        <path d="M6 3V9M6 9L4 7M6 9L8 7" stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  };

  // Toggle dropdown (matches PurchaseOrderList pattern)
  const toggleDropdown = (dropdownId, event) => {
    if (activeDropdown === dropdownId) {
      setActiveDropdown(null);
    } else {
      const buttonRect = event.currentTarget.getBoundingClientRect();
      let leftPosition;

      if (dropdownId.startsWith('status-')) {
        leftPosition = buttonRect.left;
      } else {
        leftPosition = buttonRect.right - 180;
      }

      setDropdownPosition({
        top: buttonRect.bottom + 4,
        left: leftPosition
      });
      setActiveDropdown(dropdownId);
    }
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setActiveDropdown(null);
      }
    };

    if (activeDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [activeDropdown]);

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' });
  };

  const formatCurrency = (amount) => {
    if (amount === null || amount === undefined) return '₫0';
    return `₫${Number(amount).toLocaleString('vi-VN')}`;
  };

  const getStatusStyles = (status) => {
    const map = {
      draft: 'bg-[#6b7280]',
      pending: 'bg-[#f59e0b]',
      completed: 'bg-[#10b981]',
      cancelled: 'bg-[#ef4444]'
    };
    return map[(status || '').toLowerCase()] || 'bg-[#6b7280]';
  };

  const getReasonBadge = (reason) => ({
    sales: 'Sales', transfer: 'Transfer', damage: 'Damage', expired: 'Expired',
    return_to_supplier: 'Return', internal_use: 'Internal', other: 'Other'
  }[reason] || reason);

  // --- Action Handlers (matches PurchaseOrderList pattern) ---

  const handleEdit = (wo) => {
    if (wo.status === 'cancelled' || wo.status === 'completed') {
      alert('Cannot edit completed or cancelled orders.');
      return;
    }
    setEditingOrder(wo);
    setEditModalOpen(true);
  };

  const handleDelete = async (wo) => {
    if (wo.status !== 'draft') {
      alert('Only draft orders can be deleted.');
      return;
    }

    const confirmed = window.confirm(
      `Are you sure you want to delete Stock Out Order SO-${wo.id}?\n\nThis action cannot be undone.`
    );
    if (!confirmed) return;

    try {
      const stockOutOrderService = (await import('../../services/stockOutOrderService')).default;
      await stockOutOrderService.deleteStockOutOrder(wo.id);
      alert('Stock out order deleted successfully');
      if (onRefresh) {
        onRefresh();
      }
    } catch (error) {
      console.error('Error deleting stock out order:', error);
      alert(error.response?.data?.error?.message || error.message || 'Failed to delete order');
    }
  };

  // Handle status change (matches PurchaseOrderList pattern)
  const handleStatusChange = async (wo, newStatus) => {
    if (updatingStatus) return;

    const oldStatus = wo.status;

    // Prevent changing status if already completed or cancelled
    if (oldStatus === 'completed' || oldStatus === 'cancelled') {
      alert(`Cannot change status. Stock Out Order is already ${oldStatus}.`);
      setActiveDropdown(null);
      return;
    }

    // Confirm critical status changes
    if (newStatus === 'pending') {
      const confirmed = window.confirm(
        `Are you sure you want to submit SO-${wo.id} for review?\n\nThis will lock the items from editing.`
      );
      if (!confirmed) {
        setActiveDropdown(null);
        return;
      }
    }

    if (newStatus === 'completed') {
      const confirmed = window.confirm(
        `Are you sure you want to complete SO-${wo.id}?\n\nThis will deduct inventory and create movement logs.\nThis action cannot be undone.`
      );
      if (!confirmed) {
        setActiveDropdown(null);
        return;
      }
    }

    if (newStatus === 'cancelled') {
      const warningText = oldStatus === 'pending'
        ? `\n\nWarning: This order was already PENDING.`
        : '';
      const confirmed = window.confirm(
        `Are you sure you want to cancel SO-${wo.id}?${warningText}\n\nThis action cannot be undone.`
      );
      if (!confirmed) {
        setActiveDropdown(null);
        return;
      }
    }

    setUpdatingStatus(true);
    setActiveDropdown(null);

    try {
      const stockOutOrderService = (await import('../../services/stockOutOrderService')).default;
      await stockOutOrderService.updateStockOutOrderStatus(wo.id, newStatus);

      if (onRefresh) {
        await onRefresh();
      }

      let message = `Stock Out Order status updated to ${newStatus}`;
      if (newStatus === 'pending') {
        message += '\n\nOrder is now locked for review. Only header fields can be edited.';
      } else if (newStatus === 'completed') {
        message += '\n\nInventory has been deducted and movement logs created.';
      } else if (newStatus === 'cancelled') {
        message += '\n\nStock Out Order has been cancelled.';
      }
      alert(message);
    } catch (error) {
      console.error('Error updating stock out order status:', error);
      alert(error.response?.data?.error?.message || error.message || 'Failed to update status');
    } finally {
      setUpdatingStatus(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm">
      {/* Scrollable Container */}
      <div className="overflow-x-auto rounded-lg">
        <div className="min-w-[1000px]">
          {/* Table Header */}
          <div className="flex items-center h-[34px] bg-gray-50 border-b border-gray-200">
            {/* SO ID Column - Sortable */}
            <div
              className="w-[100px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('id')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                SO ID
                {getSortIcon('id')}
              </p>
            </div>

            {/* Reason Column - Sortable */}
            <div
              className="w-[100px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('reason')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                REASON
                {getSortIcon('reason')}
              </p>
            </div>

            {/* Destination Column */}
            <div className="flex-1 min-w-[120px] px-3 flex items-center">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                DESTINATION
              </p>
            </div>

            {/* Total Column - Sortable */}
            <div
              className="w-[120px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('totalPrice')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                TOTAL
                {getSortIcon('totalPrice')}
              </p>
            </div>

            {/* Order Date Column - Sortable */}
            <div
              className="w-[100px] px-3 flex items-center flex-shrink-0 cursor-pointer hover:bg-gray-100 transition-colors"
              onClick={() => handleSortClick('orderDate')}
            >
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px] flex items-center">
                DATE
                {getSortIcon('orderDate')}
              </p>
            </div>

            {/* Status Column */}
            <div className="w-[100px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                STATUS
              </p>
            </div>

            {/* Created By Column */}
            <div className="w-[120px] px-3 flex items-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                CREATED BY
              </p>
            </div>

            {/* Actions Column */}
            <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
              <p className="text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px] leading-[18px]">
                ACTIONS
              </p>
            </div>
          </div>

          {/* Table Body */}
          <div className="flex flex-col">
            {stockOutOrders.map((wo, index) => {
              return (
                <div
                  key={wo.id}
                  className={`flex items-center h-[60px] hover:bg-gray-50 transition-colors ${index !== stockOutOrders.length - 1 ? 'border-b border-gray-100' : ''
                    }`}
                >
                  {/* SO ID */}
                  <div className="w-[100px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-emerald-600 leading-[20px]">
                      SO-{wo.id}
                    </p>
                  </div>

                  {/* Reason */}
                  <div className="w-[100px] px-3 flex items-center flex-shrink-0">
                    <span className="text-[11px] font-normal font-['Poppins',sans-serif] bg-gray-100 px-2 py-1 rounded text-gray-700">
                      {getReasonBadge(wo.reason)}
                    </span>
                  </div>

                  {/* Destination */}
                  <div className="flex-1 min-w-[120px] px-3 flex items-center">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px] truncate">
                      {wo.destination || '-'}
                    </p>
                  </div>

                  {/* Total */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                      {formatCurrency(wo.totalPrice)}
                    </p>
                  </div>

                  {/* Order Date */}
                  <div className="w-[100px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[13px] font-normal font-['Poppins',sans-serif] text-[#212529] leading-[20px]">
                      {formatDate(wo.orderDate)}
                    </p>
                  </div>

                  {/* Status - Dropdown for draft & pending */}
                  <div className="w-[100px] px-3 flex items-center flex-shrink-0">
                    {(wo.status === 'draft' || wo.status === 'pending') ? (
                      <button
                        onClick={(e) => toggleDropdown(`status-${wo.id}`, e)}
                        disabled={updatingStatus}
                        className={`${getStatusStyles(wo.status)} px-2 py-1 rounded inline-flex items-center gap-1 cursor-pointer hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed`}
                      >
                        <span className="text-[9px] font-bold font-['Poppins',sans-serif] text-white leading-[10px] uppercase">
                          {wo.status}
                        </span>
                        <svg width="8" height="5" viewBox="0 0 8 5" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M1 1L4 4L7 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      </button>
                    ) : (
                      <div className={`${getStatusStyles(wo.status)} px-2 py-1 rounded inline-flex items-center`}>
                        <span className="text-[9px] font-bold font-['Poppins',sans-serif] text-white leading-[10px] uppercase">
                          {wo.status}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Created By */}
                  <div className="w-[120px] px-3 flex items-center flex-shrink-0">
                    <p className="text-[12px] font-['Poppins',sans-serif] text-[#6c757d] leading-[18px] truncate">
                      {employeeMap[wo.createdBy] || (wo.createdBy ? `User #${wo.createdBy}` : 'N/A')}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="w-[100px] px-3 flex items-center justify-center flex-shrink-0">
                    <button
                      onClick={(e) => toggleDropdown(`action-${wo.id}`, e)}
                      className="p-2 hover:bg-gray-200 rounded-full transition-colors"
                      title="Actions"
                    >
                      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="3" cy="8" r="1.5" fill="#6B7280" />
                        <circle cx="8" cy="8" r="1.5" fill="#6B7280" />
                        <circle cx="13" cy="8" r="1.5" fill="#6B7280" />
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Empty State */}
          {stockOutOrders.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-gray-500 text-[13px] font-['Poppins',sans-serif]">
                No stock out orders found
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Position Dropdown Menus (matches PurchaseOrderList pattern) */}
      {activeDropdown && (() => {
        const wo = stockOutOrders.find(o =>
          activeDropdown === `action-${o.id}` || activeDropdown === `status-${o.id}`
        );

        if (!wo) return null;

        const isAction = activeDropdown === `action-${wo.id}`;
        const isStatus = activeDropdown === `status-${wo.id}`;

        // Status Dropdown
        if (isStatus) {
          let statusOptions = [];

          if (wo.status === 'draft') {
            statusOptions = [
              { value: 'draft', label: 'Draft', color: 'bg-[#6b7280]' },
              { value: 'pending', label: 'Pending', color: 'bg-[#f59e0b]' },
              { value: 'cancelled', label: 'Cancelled', color: 'bg-[#ef4444]' }
            ];
          } else if (wo.status === 'pending') {
            statusOptions = [
              { value: 'pending', label: 'Pending', color: 'bg-[#f59e0b]' },
              { value: 'completed', label: 'Completed', color: 'bg-[#10b981]' },
              { value: 'cancelled', label: 'Cancelled', color: 'bg-[#ef4444]' }
            ];
          }

          return (
            <div
              ref={dropdownRef}
              className="fixed min-w-[180px] bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-[9999]"
              style={{
                top: `${dropdownPosition.top}px`,
                left: `${dropdownPosition.left}px`
              }}
            >
              {statusOptions.map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleStatusChange(wo, option.value)}
                  disabled={updatingStatus}
                  className={`w-full px-3 py-2 text-left hover:bg-gray-50 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${wo.status === option.value ? 'bg-gray-50' : ''
                    }`}
                >
                  <span className={`${option.color} w-2 h-2 rounded-full`}></span>
                  <span className={`text-[12px] font-['Poppins',sans-serif] ${wo.status === option.value ? 'text-emerald-600 font-semibold' : 'text-[#212529]'
                    }`}>
                    {option.label}
                  </span>
                  {wo.status === option.value && (
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="ml-auto">
                      <path d="M10 3L4.5 8.5L2 6" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  )}
                </button>
              ))}
            </div>
          );
        }

        // Actions Dropdown
        if (isAction) {
          return (
            <div
              ref={dropdownRef}
              className="fixed w-[180px] bg-white rounded-lg shadow-xl border border-gray-200 py-1 z-[9999]"
              style={{
                top: `${dropdownPosition.top}px`,
                left: `${dropdownPosition.left}px`
              }}
            >
              {/* View Invoice */}
              <button
                onClick={() => {
                  setInvoiceModal(wo);
                  setActiveDropdown(null);
                }}
                className="w-full px-3 py-2 text-left hover:bg-emerald-50 hover:text-emerald-600 transition-colors flex items-center gap-2 text-gray-700"
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="3" y="2" width="10" height="12" rx="1" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M5 5H11M5 8H11M5 11H9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <span className="text-[12px] font-['Poppins',sans-serif]">View Invoice</span>
              </button>

              {/* Edit - allowed for draft and pending */}
              <button
                onClick={() => {
                  handleEdit(wo);
                  setActiveDropdown(null);
                }}
                disabled={wo.status === 'cancelled' || wo.status === 'completed'}
                className={`w-full px-3 py-2 text-left transition-colors flex items-center gap-2 ${wo.status === 'cancelled' || wo.status === 'completed'
                  ? 'text-gray-400 cursor-not-allowed opacity-50'
                  : 'hover:bg-blue-50 hover:text-blue-600 text-gray-700'
                  }`}
                title={
                  wo.status === 'cancelled' || wo.status === 'completed'
                    ? 'Cannot edit completed or cancelled orders'
                    : wo.status === 'pending'
                      ? 'Only header fields can be edited'
                      : 'Edit stock out order'
                }
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M11 2L14 5L5 14H2V11L11 2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
                </svg>
                <span className="text-[12px] font-['Poppins',sans-serif]">Edit</span>
              </button>

              <div className="border-t border-gray-200 my-1"></div>

              {/* Delete - only draft */}
              <button
                onClick={() => {
                  handleDelete(wo);
                  setActiveDropdown(null);
                }}
                disabled={wo.status !== 'draft'}
                className={`w-full px-3 py-2 text-left transition-colors flex items-center gap-2 ${wo.status !== 'draft'
                  ? 'text-gray-400 cursor-not-allowed opacity-50'
                  : 'hover:bg-red-50 hover:text-red-600 text-gray-700'
                  }`}
                title={wo.status !== 'draft' ? 'Only draft orders can be deleted' : 'Delete stock out order'}
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M2 4H3.33333H14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M5.33301 4.00004V2.66671C5.33301 2.31309 5.47348 1.97395 5.72353 1.7239C5.97358 1.47385 6.31272 1.33337 6.66634 1.33337H9.33301C9.68663 1.33337 10.0258 1.47385 10.2758 1.7239C10.5259 1.97395 10.6663 2.31309 10.6663 2.66671V4.00004M12.6663 4.00004V13.3334C12.6663 13.687 12.5259 14.0261 12.2758 14.2762C12.0258 14.5262 11.6866 14.6667 11.333 14.6667H4.66634C4.31272 14.6667 3.97358 14.5262 3.72353 14.2762C3.47348 14.0261 3.33301 13.687 3.33301 13.3334V4.00004H12.6663Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span className="text-[12px] font-['Poppins',sans-serif]">Delete</span>
              </button>
            </div>
          );
        }

        return null;
      })()}

      {/* Invoice Modal */}
      {invoiceModal && (
        <InvoiceStockOutModal
          stockOutOrder={invoiceModal}
          onClose={() => setInvoiceModal(null)}
        />
      )}

      {/* Edit Stock Out Order Modal */}
      {editModalOpen && editingOrder && (
        <EditStockOutOrderModal
          isOpen={editModalOpen}
          onClose={() => {
            setEditModalOpen(false);
            setEditingOrder(null);
          }}
          onSuccess={() => {
            setEditModalOpen(false);
            setEditingOrder(null);
            if (onRefresh) onRefresh();
          }}
          stockOutOrder={editingOrder}
        />
      )}
    </div>
  );
};

export default StockOutList;
