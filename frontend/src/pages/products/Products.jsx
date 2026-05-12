import React, { useState, useEffect } from 'react';
import { Breadcrumb } from '../../components/Breadcrumb';
import { ProductList, ProductListHeader, AddProductModal, EditProductModal } from '../../components/ProductList';
import productService from '../../services/productService';
import categoryService from '../../services/categoryService';

export const Products = () => {
  // ==================== 1. BREADCRUMB ====================
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Products', href: '/products' },
  ];

  // ==================== 2. STATE MANAGEMENT ====================
  // Data states
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [paginatedProducts, setPaginatedProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);

  // Filter & Sort states
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('active');
  const [vendorFilter, setVendorFilter] = useState('');
  const [sortField, setSortField] = useState('id');
  const [sortOrder, setSortOrder] = useState('asc');
  const [itemsPerPage, setItemsPerPage] = useState(10);

  // Pagination state
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    itemsPerPage: 10,
  });

  // ==================== 3. EFFECTS ====================
  // Fetch data on mount
  useEffect(() => {
    fetchProducts();
    fetchCategories();
  }, []);

  // Apply search, filters, and sorting
  useEffect(() => {
    let result = [...products];

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim();
      result = result.filter(product =>
        product.name?.toLowerCase().includes(query) ||
        product.vendor?.toLowerCase().includes(query)
      );
    }

    // Apply category filter
    if (categoryFilter) {
      result = result.filter(product => {
        const productCategoryId = product.category?.id || product.category;
        return productCategoryId === categoryFilter;
      });
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      const isActiveFilter = statusFilter === 'active';
      result = result.filter(product => (product.isActive !== false) === isActiveFilter);
    }

    // Apply vendor filter
    if (vendorFilter.trim()) {
      const vendorQuery = vendorFilter.toLowerCase().trim();
      result = result.filter(product =>
        product.vendor?.toLowerCase().includes(vendorQuery)
      );
    }

    // Apply sorting
    result.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      // Handle category name sorting
      if (sortField === 'categoryName') {
        aVal = a.category?.name || a.categoryName || '';
        bVal = b.category?.name || b.categoryName || '';
      }

      // Handle null/undefined values
      if (aVal == null) aVal = '';
      if (bVal == null) bVal = '';

      // Handle different data types
      if (sortField === 'id' || sortField === 'unitPrice' || sortField === 'onShelf') {
        aVal = Number(aVal) || 0;
        bVal = Number(bVal) || 0;
      } else {
        aVal = String(aVal).toLowerCase();
        bVal = String(bVal).toLowerCase();
      }

      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    setFilteredProducts(result);

    // Update total pages only (don't reset currentPage here)
    const totalPages = Math.ceil(result.length / itemsPerPage);
    setPagination(prev => {
      // Clamp currentPage if it exceeds new total
      const clampedPage = Math.min(prev.currentPage, totalPages) || 1;
      return {
        ...prev,
        currentPage: clampedPage,
        totalPages,
        itemsPerPage,
      };
    });
  }, [products, searchQuery, categoryFilter, statusFilter, vendorFilter, sortField, sortOrder, itemsPerPage]);

  // Reset to page 1 only when filter/sort criteria actually change
  useEffect(() => {
    setPagination(prev => ({ ...prev, currentPage: 1 }));
  }, [searchQuery, categoryFilter, statusFilter, vendorFilter, sortField, sortOrder, itemsPerPage]);

  // Paginate filtered products
  useEffect(() => {
    const startIndex = (pagination.currentPage - 1) * pagination.itemsPerPage;
    const endIndex = startIndex + pagination.itemsPerPage;
    setPaginatedProducts(filteredProducts.slice(startIndex, endIndex));
  }, [filteredProducts, pagination.currentPage, pagination.itemsPerPage]);

  // ==================== 4. API HANDLERS ====================
  const fetchProducts = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const response = await productService.getAllProducts();

      if (response.success && response.data && response.data.products) {
        setProducts(response.data.products);
      } else if (Array.isArray(response)) {
        setProducts(response);
      } else {
        setProducts([]);
      }
    } catch (err) {
      console.error('Error fetching products:', err);
      setError(err.message || 'Failed to load products');
      setProducts([]);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await categoryService.getAllCategories();
      if (response.success && response.data && response.data.categories) {
        setCategories(response.data.categories);
      } else if (Array.isArray(response)) {
        setCategories(response);
      }
    } catch (err) {
      console.error('Error fetching categories:', err);
    }
  };

  // ==================== 5. EVENT HANDLERS ====================
  const handleSearch = (query) => setSearchQuery(query);
  const handleSearchChange = (query) => setSearchQuery(query);
  const handleItemsPerPageChange = (value) => setItemsPerPage(value);
  const handleCategoryFilterChange = (value) => setCategoryFilter(value);
  const handleStatusFilterChange = (value) => setStatusFilter(value);
  const handleVendorFilterChange = (value) => setVendorFilter(value);

  const handleColumnSort = (field, order) => {
    setSortField(field);
    setSortOrder(order);
  };

  const handlePageChange = (newPage) => {
    setPagination(prev => ({ ...prev, currentPage: newPage }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // CRUD handlers
  const handleAddProduct = () => setShowAddModal(true);

  const handleEdit = (product) => {
    setSelectedProduct(product);
    setShowEditModal(true);
  };

  const handleDelete = async (product) => {
    if (product.isActive !== false) {
      alert('Cannot delete active product. Please deactivate it first.');
      return;
    }

    if (!window.confirm(`Are you sure you want to delete "${product.name}"?`)) {
      return;
    }

    try {
      await productService.deleteProduct(product.id);
      alert('Product deleted successfully!');
      fetchProducts();
    } catch (err) {
      console.error('Error deleting product:', err);
      alert(err.response?.data?.error?.message || err.message || 'Failed to delete product');
    }
  };

  const handleToggleActive = async (product, newStatus) => {
    const isCurrentlyActive = product.isActive !== false;

    // If newStatus is not provided, toggle it
    if (newStatus === undefined) {
      newStatus = !isCurrentlyActive;
    }

    try {
      await productService.updateProduct(product.id, {
        isActive: newStatus
      });
      fetchProducts();
    } catch (err) {
      console.error('Error toggling product status:', err);
      alert(err.response?.data?.error?.message || err.message || 'Failed to update product status');
    }
  };

  const handleAddSuccess = (response) => {
    console.log('Product created:', response);
    fetchProducts();
  };

  const handleEditSuccess = (response) => {
    console.log('Product updated:', response);
    fetchProducts();
    setSelectedProduct(null);
  };

  // ==================== 6. RENDER ====================
  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Product List Header */}
      <ProductListHeader
        itemsPerPage={itemsPerPage}
        onItemsPerPageChange={handleItemsPerPageChange}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        onSearch={handleSearch}
        onAddProduct={handleAddProduct}
        categoryFilter={categoryFilter}
        onCategoryFilterChange={handleCategoryFilterChange}
        categories={categories}
        statusFilter={statusFilter}
        onStatusFilterChange={handleStatusFilterChange}
        vendorFilter={vendorFilter}
        onVendorFilterChange={handleVendorFilterChange}
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
          <p className="font-medium">Error loading products</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={fetchProducts}
            className="mt-2 text-sm underline hover:no-underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Product List Table */}
      {!isLoading && !error && (
        <>
          <ProductList
            products={paginatedProducts}
            onSort={handleColumnSort}
            sortField={sortField}
            sortOrder={sortOrder}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onToggleActive={handleToggleActive}
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
                        <span key="ellipsis-start" className="px-2 text-gray-400 text-[12px]">
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
                        className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${page === currentPage
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
                        <span key="ellipsis-end" className="px-2 text-gray-400 text-[12px]">
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
          {paginatedProducts.length > 0 && (
            <div className="text-center text-sm text-gray-600 font-['Poppins',sans-serif] mt-4">
              Showing {((pagination.currentPage - 1) * pagination.itemsPerPage) + 1} to{' '}
              {Math.min(pagination.currentPage * pagination.itemsPerPage, filteredProducts.length)} of{' '}
              {filteredProducts.length} products
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!isLoading && !error && filteredProducts.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 bg-white rounded-lg">
          <p className="text-gray-500 text-sm">No products found</p>
          {(searchQuery || categoryFilter || statusFilter !== 'all') && (
            <button
              onClick={() => {
                setSearchQuery('');
                setCategoryFilter('');
                setStatusFilter('all');
              }}
              className="mt-2 text-sm text-emerald-600 hover:underline"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}

      {/* Add Product Modal */}
      <AddProductModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={handleAddSuccess}
      />

      {/* Edit Product Modal */}
      <EditProductModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setSelectedProduct(null);
        }}
        onSuccess={handleEditSuccess}
        product={selectedProduct}
      />
    </div>
  );
};

export default Products;