import React, { useState, useEffect } from 'react';
import { Breadcrumb } from '../components/Breadcrumb';
import {
  PurchaseOrderList,
  PurchaseOrderListHeader,
  AddPurchaseOrderModal,
  EditPurchaseOrderModal,
  ReceivePurchaseOrderModal,
  InvoicePurchaseModal
} from '../components/PurchaseOrderList';
import purchaseOrderService from '../services/purchaseOrderService';
import supplierService from '../services/supplierService';
import employeeService from '../services/employeeService';

export const PurchaseOrders = () => {
  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Purchase Orders', href: '/purchase-orders' },
  ];

  const [purchaseOrders, setPurchaseOrders] = useState([]);
  const [filteredPurchaseOrders, setFilteredPurchaseOrders] = useState([]);
  const [paginatedPurchaseOrders, setPaginatedPurchaseOrders] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showReceiveModal, setShowReceiveModal] = useState(false);
  const [showInvoiceModal, setShowInvoiceModal] = useState(false);
  const [selectedPurchaseOrder, setSelectedPurchaseOrder] = useState(null);

  // Filters and sorting
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('orderDate');
  const [sortOrder, setSortOrder] = useState('desc');
  const [statusFilter, setStatusFilter] = useState('all');
  const [paymentStatusFilter, setPaymentStatusFilter] = useState('all');
  const [supplierFilter, setSupplierFilter] = useState('all');

  // Pagination state
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    itemsPerPage: 10,
  });

  // Fetch data on component mount
  useEffect(() => {
    fetchPurchaseOrders();
    fetchSuppliers();
  }, []);

  // Apply filters, search and sorting when data or filters change
  useEffect(() => {
    let result = [...purchaseOrders];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      result = result.filter(po =>
        po.poNumber?.toLowerCase().includes(query) ||
        po.supplier?.companyName?.toLowerCase().includes(query) ||
        po.notes?.toLowerCase().includes(query)
      );
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      result = result.filter(po => po.status === statusFilter);
    }

    // Apply payment status filter
    if (paymentStatusFilter !== 'all') {
      result = result.filter(po => po.paymentStatus === paymentStatusFilter);
    }

    // Apply supplier filter
    if (supplierFilter !== 'all') {
      result = result.filter(po => po.supplier?.id === supplierFilter);
    }

    // Apply sorting
    result.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      // Handle nested fields
      if (sortField === 'supplier') {
        aVal = a.supplier?.companyName;
        bVal = b.supplier?.companyName;
      }

      // Handle null/undefined values
      if (aVal == null) aVal = '';
      if (bVal == null) bVal = '';

      // Handle different data types
      if (sortField === 'totalPrice' || sortField === 'shippingFee') {
        aVal = Number(aVal) || 0;
        bVal = Number(bVal) || 0;
      } else if (sortField === 'orderDate' || sortField === 'receivedDate') {
        aVal = new Date(aVal).getTime() || 0;
        bVal = new Date(bVal).getTime() || 0;
      } else {
        aVal = String(aVal).toLowerCase();
        bVal = String(bVal).toLowerCase();
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    setFilteredPurchaseOrders(result);

    // Update pagination
    const totalPages = Math.ceil(result.length / itemsPerPage);
    setPagination(prev => ({
      ...prev,
      currentPage: 1, // Reset to first page on filter change
      totalPages,
      itemsPerPage,
    }));
  }, [purchaseOrders, searchQuery, sortField, sortOrder, itemsPerPage, statusFilter, paymentStatusFilter, supplierFilter]);

  // Paginate filtered purchase orders
  useEffect(() => {
    const startIndex = (pagination.currentPage - 1) * pagination.itemsPerPage;
    const endIndex = startIndex + pagination.itemsPerPage;
    setPaginatedPurchaseOrders(filteredPurchaseOrders.slice(startIndex, endIndex));
  }, [filteredPurchaseOrders, pagination.currentPage, pagination.itemsPerPage]);

  const fetchPurchaseOrders = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Fetch POs and employees in parallel
      const [poResponse, empResponse] = await Promise.all([
        purchaseOrderService.getAllPurchaseOrders(),
        employeeService.getAllEmployees().catch(() => null)
      ]);

      // Build userId → fullName lookup map from employees
      // Auth service employee.findAll() returns rows with: id (=user_account.id), full_name (snake_case)
      let employeeMap = {};
      if (empResponse?.success) {
        // Handle various response shapes from paginated() or success()
        let employees = [];
        if (Array.isArray(empResponse.data)) {
          employees = empResponse.data;
        } else if (empResponse.data?.employees) {
          employees = empResponse.data.employees;
        } else if (empResponse.data?.rows) {
          employees = empResponse.data.rows;
        }

        employees.forEach(emp => {
          // employee.findAll() SELECT u.id, e.full_name
          const uid = emp.id || emp.user_id || emp.userId;
          const name = emp.full_name || emp.fullName || emp.username || `Employee #${uid}`;
          if (uid) {
            employeeMap[uid] = name;
          }
        });
      }

      // API returns { success: true, data: [...] }
      let poList = [];
      if (poResponse.success && Array.isArray(poResponse.data)) {
        poList = poResponse.data;
      } else if (Array.isArray(poResponse)) {
        poList = poResponse;
      }

      // Enrich createdBy from raw user_id to {id, fullName} object
      const enriched = poList.map(po => {
        if (po.createdBy && typeof po.createdBy !== 'object') {
          const userId = po.createdBy;
          const fullName = employeeMap[userId] || `User #${userId}`;
          return { ...po, createdBy: { id: userId, fullName } };
        }
        return po;
      });

      setPurchaseOrders(enriched);
    } catch (err) {
      console.error('Error fetching purchase orders:', err);
      setError(err.message || 'Failed to load purchase orders');
      setPurchaseOrders([]);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchSuppliers = async () => {
    try {
      const response = await supplierService.getActiveSuppliers();
      // Updated supplier API returns { success: true, data: [...] }
      if (response.success && Array.isArray(response.data)) {
        setSuppliers(response.data);
      } else if (Array.isArray(response)) {
        setSuppliers(response);
      } else {
        setSuppliers([]);
      }
    } catch (err) {
      console.error('Error fetching suppliers:', err);
      setSuppliers([]);
    }
  };

  const handleColumnSort = (field) => {
    if (sortField === field) {
      // Toggle sort order if same field
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      // Default to ascending for new field
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const handleSearch = (query) => {
    setSearchQuery(query);
  };

  const handleSearchChange = (query) => {
    setSearchQuery(query);
  };

  const handleItemsPerPageChange = (value) => {
    setItemsPerPage(value);
  };

  const handleStatusFilterChange = (status) => {
    setStatusFilter(status);
  };

  const handlePaymentStatusFilterChange = (paymentStatus) => {
    setPaymentStatusFilter(paymentStatus);
  };

  const handleSupplierFilterChange = (supplierId) => {
    setSupplierFilter(supplierId);
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({
      ...prev,
      currentPage: newPage
    }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleEdit = (purchaseOrder) => {
    setSelectedPurchaseOrder(purchaseOrder);
    setShowEditModal(true);
  };

  const handleReceive = (purchaseOrder) => {
    setSelectedPurchaseOrder(purchaseOrder);
    setShowReceiveModal(true);
  };

  const handleViewInvoice = (purchaseOrder) => {
    setSelectedPurchaseOrder(purchaseOrder);
    setShowInvoiceModal(true);
  };

  const handleEditSuccess = (response) => {
    console.log('Purchase order updated:', response);
    fetchPurchaseOrders();
    setSelectedPurchaseOrder(null);
  };

  const handleReceiveSuccess = (response) => {
    console.log('Purchase order received:', response);
    fetchPurchaseOrders();
    setSelectedPurchaseOrder(null);
  };

  const handleApprove = async (purchaseOrder) => {
    if (!window.confirm(`Are you sure you want to approve purchase order #${purchaseOrder.id}?`)) {
      return;
    }

    try {
      await purchaseOrderService.approvePurchaseOrder(purchaseOrder.id);
      alert('Purchase order approved successfully!');
      fetchPurchaseOrders();
    } catch (err) {
      console.error('Error approving purchase order:', err);
      alert(err.response?.data?.error?.message || err.message || 'Failed to approve purchase order');
    }
  };

  const handleCancel = async (purchaseOrder) => {
    if (!window.confirm(`Are you sure you want to cancel purchase order #${purchaseOrder.id}?`)) {
      return;
    }

    try {
      await purchaseOrderService.cancelPurchaseOrder(purchaseOrder.id);
      alert('Purchase order cancelled successfully!');
      fetchPurchaseOrders();
    } catch (err) {
      console.error('Error cancelling purchase order:', err);
      alert(err.response?.data?.error?.message || err.message || 'Failed to cancel purchase order');
    }
  };

  const handleDelete = async (purchaseOrder) => {
    const deletableStatuses = ['draft', 'cancelled', 'received'];
    if (!deletableStatuses.includes(purchaseOrder.status)) {
      alert(`Cannot delete purchase order with status '${purchaseOrder.status}'. Only draft, cancelled, and received orders can be deleted.`);
      return;
    }

    if (!window.confirm(`Are you sure you want to delete purchase order #${purchaseOrder.id}?`)) {
      return;
    }

    try {
      await purchaseOrderService.deletePurchaseOrder(purchaseOrder.id);
      alert('Purchase order deleted successfully!');
      fetchPurchaseOrders();
    } catch (err) {
      console.error('Error deleting purchase order:', err);
      alert(err.response?.data?.error?.message || err.message || 'Failed to delete purchase order');
    }
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Purchase Order List Header */}
      <PurchaseOrderListHeader
        itemsPerPage={itemsPerPage}
        onItemsPerPageChange={handleItemsPerPageChange}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        onSearch={handleSearch}
        statusFilter={statusFilter}
        onStatusFilterChange={handleStatusFilterChange}
        paymentStatusFilter={paymentStatusFilter}
        onPaymentStatusFilterChange={handlePaymentStatusFilterChange}
        supplierFilter={supplierFilter}
        onSupplierFilterChange={handleSupplierFilterChange}
        suppliers={suppliers}
        onAddClick={() => setShowAddModal(true)}
      />

      {/* Loading State */}
      {isLoading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p className="font-medium">Error loading purchase orders</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={fetchPurchaseOrders}
            className="mt-2 text-sm underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Purchase Order List Table */}
      {!isLoading && !error && (
        <>
          <PurchaseOrderList
            purchaseOrders={paginatedPurchaseOrders}
            onSort={handleColumnSort}
            sortField={sortField}
            sortOrder={sortOrder}
            onRefresh={fetchPurchaseOrders}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onApprove={handleApprove}
            onReceive={handleReceive}
            onCancel={handleCancel}
            onViewInvoice={handleViewInvoice}
          />

          {/* Pagination */}
          {pagination.totalPages > 1 && (
            <div className="flex items-center justify-center mt-6">
              <div className="flex items-center gap-2">
                {/* Previous button */}
                <button
                  onClick={() => handlePageChange(pagination.currentPage - 1)}
                  disabled={pagination.currentPage === 1}
                  className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${pagination.currentPage === 1
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-[#3bb77e] hover:bg-[#def9ec]'
                    }`}
                >
                  ‹ Previous
                </button>

                {/* Page numbers */}
                {(() => {
                  const maxPagesToShow = 5;
                  const { totalPages, currentPage } = pagination;

                  let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
                  let endPage = Math.min(totalPages, startPage + maxPagesToShow - 1);

                  if (endPage - startPage < maxPagesToShow - 1) {
                    startPage = Math.max(1, endPage - maxPagesToShow + 1);
                  }

                  const pages = [];

                  // First page + ellipsis
                  if (startPage > 1) {
                    pages.push(
                      <button
                        key={1}
                        onClick={() => handlePageChange(1)}
                        className="px-3 py-2 rounded text-[#3bb77e] hover:bg-[#def9ec] transition-colors text-[12px] font-['Poppins',sans-serif]"
                      >
                        1
                      </button>
                    );
                    if (startPage > 2) {
                      pages.push(
                        <span key="ellipsis-start" className="px-2 text-gray-400">
                          ...
                        </span>
                      );
                    }
                  }

                  // Page numbers
                  for (let page = startPage; page <= endPage; page++) {
                    pages.push(
                      <button
                        key={page}
                        onClick={() => handlePageChange(page)}
                        className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${currentPage === page
                          ? 'bg-[#3bb77e] text-white'
                          : 'text-[#3bb77e] hover:bg-[#def9ec]'
                          }`}
                      >
                        {page}
                      </button>
                    );
                  }

                  // Ellipsis + last page
                  if (endPage < totalPages) {
                    if (endPage < totalPages - 1) {
                      pages.push(
                        <span key="ellipsis-end" className="px-2 text-gray-400">
                          ...
                        </span>
                      );
                    }
                    pages.push(
                      <button
                        key={totalPages}
                        onClick={() => handlePageChange(totalPages)}
                        className="px-3 py-2 rounded text-[#3bb77e] hover:bg-[#def9ec] transition-colors text-[12px] font-['Poppins',sans-serif]"
                      >
                        {totalPages}
                      </button>
                    );
                  }

                  return pages;
                })()}

                {/* Next button */}
                <button
                  onClick={() => handlePageChange(pagination.currentPage + 1)}
                  disabled={pagination.currentPage === pagination.totalPages}
                  className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${pagination.currentPage === pagination.totalPages
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-[#3bb77e] hover:bg-[#def9ec]'
                    }`}
                >
                  Next ›
                </button>
              </div>
            </div>
          )}

          {/* Results Summary */}
          {paginatedPurchaseOrders.length > 0 && (
            <div className="text-center text-sm text-gray-600 font-['Poppins',sans-serif] mt-4">
              Showing {((pagination.currentPage - 1) * pagination.itemsPerPage) + 1} to {Math.min(pagination.currentPage * pagination.itemsPerPage, filteredPurchaseOrders.length)} of {filteredPurchaseOrders.length} purchase orders
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!isLoading && !error && filteredPurchaseOrders.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 bg-white rounded-lg">
          <p className="text-gray-500 text-sm">No purchase orders found</p>
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="mt-2 text-sm text-emerald-600 hover:underline"
            >
              Clear search
            </button>
          )}
        </div>
      )}

      {/* Add Purchase Order Modal */}
      <AddPurchaseOrderModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={() => {
          setShowAddModal(false);
          fetchPurchaseOrders(); // Refresh list
        }}
      />

      {/* Edit Purchase Order Modal */}
      <EditPurchaseOrderModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedPurchaseOrder(null);
        }}
        onSuccess={handleEditSuccess}
        purchaseOrder={selectedPurchaseOrder}
        suppliers={suppliers}
      />

      {/* Receive Purchase Order Modal */}
      <ReceivePurchaseOrderModal
        isOpen={showReceiveModal}
        onClose={() => {
          setShowReceiveModal(false);
          setSelectedPurchaseOrder(null);
        }}
        onSuccess={handleReceiveSuccess}
        purchaseOrder={selectedPurchaseOrder}
      />

      {/* Invoice Modal */}
      <InvoicePurchaseModal
        isOpen={showInvoiceModal}
        onClose={() => {
          setShowInvoiceModal(false);
          setSelectedPurchaseOrder(null);
        }}
        purchaseOrder={selectedPurchaseOrder}
      />
    </div>
  );
};

export default PurchaseOrders;
