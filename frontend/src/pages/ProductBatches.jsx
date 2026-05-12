import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Breadcrumb } from '../components/Breadcrumb';
import { ProductBatchListHeader, ProductBatchList } from '../components/ProductBatchList';
import { BulkDiscountModal } from '../components/ProductBatchList/BulkDiscountModal';
import productBatchService from '../services/productBatchService';
import productService from '../services/productService';

const ProductBatches = () => {
  const { productId } = useParams();
  const navigate = useNavigate();

  // State management
  const [batches, setBatches] = useState([]);
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    currentPage: 1,
    limit: 20,
    total: 0,
    totalPages: 0
  });

  // Filters
  const [filters, setFilters] = useState({
    page: 1,
    limit: 20,
    status: 'active'
  });

  // Search state
  const [searchQuery, setSearchQuery] = useState('');

  // Sort state
  const [sortField, setSortField] = useState('createdAt');
  const [sortOrder, setSortOrder] = useState('desc');

  // Modal states
  const [addBatchModal, setAddBatchModal] = useState(false);
  const [editBatchModal, setEditBatchModal] = useState(false);
  const [bulkDiscountModal, setBulkDiscountModal] = useState(false);
  const [selectedBatch, setSelectedBatch] = useState(null);

  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Products', href: '/products' },
    { label: product?.name || 'Product Batches', href: null },
  ];

  // Fetch product details
  const fetchProduct = async () => {
    if (!productId) return;

    try {
      const response = await productService.getProductById(productId);
      if (response.success) {
        setProduct(response.data.product);
      }
    } catch (err) {
      console.error('Error fetching product:', err);
      setError('Failed to fetch product details');
    }
  };

  // Fetch batches from API
  const fetchBatches = async () => {
    try {
      setLoading(true);
      setError(null);

      // Build query params
      const params = {
        product: productId,
        page: filters.page,
        limit: filters.limit
      };

      // Add status filter if exists
      if (filters.status) {
        params.status = filters.status;
      }

      // Add search if exists
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }

      const response = await productBatchService.getAllBatches(params);

      if (response.success) {
        // Debug: Check batch data structure with discount fields
        console.log('Fetched batches:', response.data.batches.map(b => ({
          batchCode: b.batchCode,
          costPrice: b.costPrice,
          unitPrice: b.unitPrice,
          quantity: b.quantity,
          status: b.status,
          promotionApplied: b.promotionApplied,
          discountPercentage: b.discountPercentage,
          expiryDate: b.expiryDate
        })));

        setBatches(response.data.batches || []);
        // Map API response pagination (page, pages) to component state (currentPage, totalPages)
        const apiPagination = response.data.pagination || {};
        setPagination({
          currentPage: apiPagination.page || apiPagination.currentPage || 1,
          limit: apiPagination.limit || 20,
          total: apiPagination.total || 0,
          totalPages: apiPagination.pages || apiPagination.totalPages || 0
        });
      }
    } catch (err) {
      console.error('Error fetching batches:', err);
      setError(err.response?.data?.error?.message || 'Failed to fetch batches');
    } finally {
      setLoading(false);
    }
  };

  // Fetch product and batches on component mount
  useEffect(() => {
    fetchProduct();
  }, [productId]);

  useEffect(() => {
    if (productId) {
      fetchBatches();
    }
  }, [productId, filters.page, filters.limit, filters.status, searchQuery]);

  // Handle filter changes
  const handleItemsPerPageChange = (newLimit) => {
    setFilters({ ...filters, limit: newLimit, page: 1 });
  };

  const handleStatusFilterChange = (status) => {
    setFilters({ ...filters, status, page: 1 });
  };

  // Handle column sort
  const handleColumnSort = (field, order) => {
    setSortField(field);
    setSortOrder(order);
    // Sort locally since API doesn't support sorting yet
    const sorted = [...batches].sort((a, b) => {
      let aVal = a[field];
      let bVal = b[field];

      if (field === 'batchCode' || field === 'status') {
        aVal = aVal?.toString().toLowerCase() || '';
        bVal = bVal?.toString().toLowerCase() || '';
      }

      if (order === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });
    setBatches(sorted);
  };

  // Handle add batch
  const handleAddBatch = () => {
    setAddBatchModal(true);
  };

  // Handle edit batch
  const handleEditBatch = (batch) => {
    setSelectedBatch(batch);
    setEditBatchModal(true);
  };

  // Handle batch created successfully
  const handleBatchSuccess = () => {
    fetchBatches();
  };

  // Handle batch updated successfully
  const handleBatchUpdateSuccess = () => {
    fetchBatches();
    setSelectedBatch(null);
  };

  // Handle delete batch
  const handleDeleteBatch = async (batch) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete batch ${batch.batchCode}?\n\nThis action cannot be undone.`
    );

    if (!confirmed) return;

    try {
      await productBatchService.deleteBatch(batch.id);
      fetchBatches();
    } catch (error) {
      console.error('Error deleting batch:', error);
      alert(error.response?.data?.error?.message || 'Failed to delete batch');
    }
  };

  // Handle update batch status
  const handleUpdateStatus = async (batch, newStatus) => {
    try {
      await productBatchService.updateBatchStatus(batch.id, newStatus);
      fetchBatches();
    } catch (error) {
      console.error('Error updating batch status:', error);
      alert(error.response?.data?.error?.message || 'Failed to update batch status');
    }
  };

  // Handle configure discount
  const handleConfigureDiscount = () => {
    setBulkDiscountModal(true);
  };

  // Handle bulk discount success
  const handleBulkDiscountSuccess = () => {
    fetchBatches();
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Product Info Card */}
      {product && (
        <div className="bg-white rounded-lg shadow-sm p-6">
          <div className="flex items-center gap-4">
            {product.image && (
              <img
                src={product.image}
                alt={product.name}
                className="w-20 h-20 object-cover rounded-lg border border-gray-200"
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            )}
            <div>
              <h1 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529]">
                {product.name}
              </h1>
              <p className="text-[13px] text-gray-600 font-['Poppins',sans-serif]">
                Product Code: {product.productCode}
              </p>
            </div>
            <button
              onClick={() => navigate('/products')}
              className="ml-auto px-4 py-2 text-[13px] font-['Poppins',sans-serif] text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline mr-1 align-text-bottom">
                <path d="M10 12L6 8L10 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Back to Products
            </button>
          </div>
        </div>
      )}

      {/* Batch List Header */}
      <ProductBatchListHeader
        itemsPerPage={filters.limit}
        onItemsPerPageChange={handleItemsPerPageChange}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onSearch={setSearchQuery}
        statusFilter={filters.status}
        onStatusFilterChange={handleStatusFilterChange}
        onAddBatch={handleAddBatch}
        onConfigureDiscount={handleConfigureDiscount}
      />

      {/* Bulk Discount Modal */}
      <BulkDiscountModal
        isOpen={bulkDiscountModal}
        onClose={() => setBulkDiscountModal(false)}
        onSuccess={handleBulkDiscountSuccess}
        productId={productId}
        productName={product?.name}
      />

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600"></div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          <p className="font-medium">Error loading batches</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={fetchBatches}
            className="mt-2 text-sm underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Batch List Table */}
      {!loading && !error && (
        <>
          <ProductBatchList
            batches={batches}
            onSort={handleColumnSort}
            sortField={sortField}
            sortOrder={sortOrder}
            onEdit={handleEditBatch}
            onDelete={handleDeleteBatch}
            onUpdateStatus={handleUpdateStatus}
            addModalOpen={addBatchModal}
            onCloseAddModal={() => setAddBatchModal(false)}
            onAddSuccess={handleBatchSuccess}
            editModalOpen={editBatchModal}
            editBatch={selectedBatch}
            onCloseEditModal={() => {
              setEditBatchModal(false);
              setSelectedBatch(null);
            }}
            onEditSuccess={handleBatchUpdateSuccess}
            productId={productId}
          />

          {/* Pagination */}
          {pagination.totalPages > 1 && (
            <div className="flex items-center justify-center mt-6">
              <div className="flex items-center gap-2">
                {/* Previous button */}
                <button
                  onClick={() => setFilters({ ...filters, page: pagination.currentPage - 1 })}
                  disabled={pagination.currentPage === 1}
                  className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${pagination.currentPage === 1
                    ? 'text-gray-400 cursor-not-allowed'
                    : 'text-[#3bb77e] hover:bg-[#def9ec]'
                    }`}
                >
                  ‹ Previous
                </button>

                {/* Page numbers */}
                {Array.from({ length: Math.min(5, pagination.totalPages) }, (_, i) => {
                  const page = i + 1;
                  return (
                    <button
                      key={page}
                      onClick={() => setFilters({ ...filters, page })}
                      className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${pagination.currentPage === page
                        ? 'bg-[#3bb77e] text-white'
                        : 'text-[#3bb77e] hover:bg-[#def9ec]'
                        }`}
                    >
                      {page}
                    </button>
                  );
                })}

                {/* Next button */}
                <button
                  onClick={() => setFilters({ ...filters, page: pagination.currentPage + 1 })}
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
          {batches.length > 0 && (
            <div className="text-center text-sm text-gray-600 font-['Poppins',sans-serif] mt-4">
              Showing {((pagination.currentPage - 1) * pagination.limit) + 1} to{' '}
              {Math.min(pagination.currentPage * pagination.limit, pagination.total)} of{' '}
              {pagination.total} batches
            </div>
          )}

          {/* Empty State */}
          {batches.length === 0 && !loading && (
            <div className="bg-white rounded-lg shadow-sm p-12 text-center">
              <p className="text-gray-500 text-[14px] font-['Poppins',sans-serif]">
                No batches found for this product
              </p>
              <button
                onClick={handleAddBatch}
                className="mt-4 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-[13px] font-['Poppins',sans-serif]"
              >
                Add First Batch
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default ProductBatches;
