import React, { useState, useEffect } from 'react';
import { ProductCard } from './ProductCard';
import productService from '../../services/productService';
import inventoryService from '../../services/inventoryService';

/**
 * ProductGrid Component
 * Hiển thị danh sách sản phẩm dạng grid layout
 * Tự động fetch data từ API và handle pagination
 * 
 * Props:
 * - onProductClick: Optional handler for product card clicks (for batch modal)
 */
export const ProductGrid = ({ filters = {}, sortBy = 'newest', onPaginationChange, onProductClick }) => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    totalItems: 0,
    perPage: 20
  });

  useEffect(() => {
    fetchProducts();
  }, [filters, sortBy, pagination.currentPage]);

  // Reset to page 1 when filters or sort change
  useEffect(() => {
    setPagination(prev => ({ ...prev, currentPage: 1 }));
  }, [filters, sortBy]);

  const fetchProducts = async () => {
    setLoading(true);
    setError(null);

    // Notify parent about loading state
    if (onPaginationChange) {
      onPaginationChange({ isLoading: true });
    }

    try {
      // Build query parameters
      const params = {
        page: pagination.currentPage,
        per_page: pagination.perPage,
        ...filters
      };

      // Handle categories array → send as categoryId param for backend
      if (params.categories && Array.isArray(params.categories) && params.categories.length > 0) {
        params.categoryId = params.categories.join(',');
        delete params.categories;
      }

      // Add sort parameter
      if (sortBy === 'price-low') {
        params.sort = 'unitPrice';
        params.order = 'asc';
      } else if (sortBy === 'price-high') {
        params.sort = 'unitPrice';
        params.order = 'desc';
      } else if (sortBy === 'name') {
        params.sort = 'name';
        params.order = 'asc';
      } else {
        // newest - sort by id descending (no created_at column)
        params.sort = 'id';
        params.order = 'desc';
      }

      // Fetch products + inventory in parallel
      const [response, invResponse] = await Promise.all([
        productService.getAllProducts(params),
        inventoryService.getInventorySummary()
      ]);

      if (response.success) {
        // Build inventory map: productId → inventory data
        const inventoryMap = {};
        const invData = invResponse?.data || [];
        (Array.isArray(invData) ? invData : []).forEach(item => {
          inventoryMap[item.productId] = {
            quantityOnHand: item.quantityOnHand || 0,
            quantityOnShelf: item.quantityOnShelf || 0,
            quantityReserved: item.quantityReserved || 0,
            quantityAvailable: item.quantityAvailable || 0
          };
        });

        // Merge inventory into products
        const productsWithInventory = (response.data.products || []).map(product => {
          const inv = inventoryMap[product.id] || {
            quantityOnHand: 0, quantityOnShelf: 0, quantityReserved: 0, quantityAvailable: 0
          };
          return { ...product, inventory: inv };
        });

        setProducts(productsWithInventory);

        // Update pagination info if available
        if (response.data.pagination) {
          const newPagination = {
            ...pagination,
            totalPages: response.data.pagination.pages || 1,
            totalItems: response.data.pagination.total || 0
          };
          setPagination(newPagination);

          // Notify parent component about pagination changes
          if (onPaginationChange) {
            onPaginationChange({
              totalItems: newPagination.totalItems,
              currentCount: productsWithInventory.length,
              isLoading: false
            });
          }
        }
      } else {
        throw new Error(response.message || 'Failed to fetch products');
      }
    } catch (err) {
      console.error('Error fetching products:', err);
      setError(err.message || 'Failed to load products');
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (page) => {
    setPagination(prev => ({ ...prev, currentPage: page }));
    // Scroll to top of grid
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {[...Array(pagination.perPage)].map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="bg-gray-200 h-48 rounded-t-lg"></div>
            <div className="bg-white border border-gray-200 p-4 rounded-b-lg">
              <div className="h-3 bg-gray-200 rounded mb-2 w-1/3"></div>
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-2/3 mb-3"></div>
              <div className="h-6 bg-gray-200 rounded w-1/2"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <svg className="w-16 h-16 text-red-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 className="text-lg font-semibold text-gray-800 mb-2">Error Loading Products</h3>
        <p className="text-gray-600 mb-4">{error}</p>
        <button
          onClick={fetchProducts}
          className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  // Empty state
  if (products.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <svg className="w-16 h-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <h3 className="text-lg font-semibold text-gray-800 mb-2">No Products Found</h3>
        <p className="text-gray-600">Try adjusting your filters or search criteria</p>
      </div>
    );
  }

  return (
    <div>
      {/* Product Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {products.map(product => (
          <ProductCard
            key={product.id || product._id}
            product={product}
            onClick={onProductClick ? () => onProductClick(product) : undefined}
          />
        ))}
      </div>

      {/* Pagination */}
      {pagination.totalPages > 1 && (
        <div className="flex flex-col items-center mt-8 gap-3">
          {/* Page buttons */}
          <div className="flex items-center gap-1">
            {/* Previous button */}
            <button
              onClick={() => handlePageChange(pagination.currentPage - 1)}
              disabled={pagination.currentPage === 1}
              className="px-3 py-2 rounded-lg text-sm text-emerald-600 hover:bg-emerald-50 disabled:text-gray-400 disabled:hover:bg-transparent transition-colors"
            >
              ‹ Previous
            </button>

            {/* Page numbers */}
            {Array.from({ length: pagination.totalPages }, (_, i) => i + 1).map(pageNum => (
              <button
                key={pageNum}
                onClick={() => handlePageChange(pageNum)}
                className={`w-9 h-9 rounded-lg text-sm font-medium transition-colors ${pagination.currentPage === pageNum
                  ? 'bg-emerald-500 text-white shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100'
                  }`}
              >
                {pageNum}
              </button>
            ))}

            {/* Next button */}
            <button
              onClick={() => handlePageChange(pagination.currentPage + 1)}
              disabled={pagination.currentPage === pagination.totalPages}
              className="px-3 py-2 rounded-lg text-sm text-emerald-600 hover:bg-emerald-50 disabled:text-gray-400 disabled:hover:bg-transparent transition-colors"
            >
              Next ›
            </button>
          </div>

          {/* Showing info */}
          <div className="text-sm text-gray-500">
            Showing {((pagination.currentPage - 1) * pagination.perPage) + 1} to {Math.min(pagination.currentPage * pagination.perPage, pagination.totalItems)} of {pagination.totalItems} products
          </div>
        </div>
      )}
    </div>
  );
};
