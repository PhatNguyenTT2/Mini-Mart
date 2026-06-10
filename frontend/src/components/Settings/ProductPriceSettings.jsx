import React, { useState, useEffect } from 'react';
import productService from '../../services/productService';
import { Search, Save, History, DollarSign, ArrowRight, AlertCircle } from 'lucide-react';

export const ProductPriceSettings = () => {
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [priceHistory, setPriceHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [totalProducts, setTotalProducts] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Form state
  const [newPrice, setNewPrice] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Fetch products when searchQuery, page, or limit changes
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      searchProducts();
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery, currentPage, limit]);

  // Fetch history when product selected
  useEffect(() => {
    if (selectedProduct) {
      fetchPriceHistory(selectedProduct.id);
      setNewPrice(selectedProduct.unitPrice);
      setReason('');
      setError('');
      setSuccess('');
    }
  }, [selectedProduct]);

  const searchProducts = async () => {
    setLoading(true);
    try {
      const params = {
        page: currentPage,
        per_page: limit
      };
      if (searchQuery.trim()) {
        params.search = searchQuery.trim();
      }
      const response = await productService.getAllProducts(params);
      if (response && response.success && response.data) {
        const data = response.data;
        if (data.products) {
          setProducts(data.products);
          if (data.pagination) {
            setTotalProducts(data.pagination.total || 0);
            setTotalPages(data.pagination.pages || 1);
          } else {
            setTotalProducts(data.products.length);
            setTotalPages(1);
          }
        } else if (Array.isArray(data)) {
          setProducts(data);
          setTotalProducts(data.length);
          setTotalPages(1);
        }
      }
    } catch (err) {
      console.error('Failed to search products', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPriceHistory = async (productId) => {
    setHistoryLoading(true);
    try {
      const response = await productService.getProductPriceHistory(productId);
      if (response.success) {
        // API returns { data: { history: [...] } } with snake_case fields
        const rawHistory = response.data?.history || response.data || [];
        setPriceHistory(rawHistory);
      }
    } catch (err) {
      console.error('Failed to fetch history', err);
      setPriceHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedProduct) return;

    if (parseFloat(newPrice) < 0) {
      setError('Price cannot be negative');
      return;
    }

    if (parseFloat(newPrice) === parseFloat(selectedProduct.unitPrice)) {
      setError('New price is same as current price');
      return;
    }

    setSubmitting(true);
    setError('');
    setSuccess('');

    try {
      const response = await productService.updateProductPrice(selectedProduct.id, {
        newPrice: parseFloat(newPrice),
        reason: reason.trim() || 'Manual update via Settings'
      });

      if (response.success) {
        setSuccess('Price updated successfully');
        // Update local state
        const updatedProduct = {
          ...selectedProduct,
          unitPrice: parseFloat(newPrice)
        };
        setSelectedProduct(updatedProduct);

        // Update product in list as well
        setProducts(products.map(p => p.id === updatedProduct.id ? updatedProduct : p));

        // Refresh history
        fetchPriceHistory(selectedProduct.id);
        setReason('');
      } else {
        setError(response.error?.message || 'Failed to update price');
      }
    } catch (err) {
      console.error('Update price error:', err);
      setError(err.response?.data?.error?.message || 'Failed to update price');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSelectProduct = (product) => {
    setSelectedProduct(product);
  };

  return (
    <div className="space-y-6">
      {/* Product List Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Search className="w-5 h-5 text-emerald-600" />
            Select Product
          </h3>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            {/* Items Per Page Dropdown */}
            <div className="relative w-[80px]">
              <select
                value={limit}
                onChange={(e) => {
                  setLimit(parseInt(e.target.value));
                  setCurrentPage(1);
                }}
                className="w-full h-[36px] bg-white border border-[#ced4da] rounded-lg px-3 py-2 text-[12px] font-['Poppins',sans-serif] text-[#212529] appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
              >
                <option value="10">10</option>
                <option value="20">20</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
              <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                <svg width="10" height="10" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M3 4.5L6 7.5L9 4.5" stroke="#212529" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </div>
            {/* Search Input */}
            <div className="relative flex-1 sm:w-72">
              <input
                type="text"
                className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500 transition-all font-['Poppins',sans-serif]"
                placeholder="Search by name or barcode..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
              />
              <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
            </div>
          </div>
        </div>

        {/* Product Table */}
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200 h-[34px]">
                <th className="w-[100px] px-4 text-left text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">ID</th>
                <th className="w-[80px] px-4 text-left text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Image</th>
                <th className="px-4 text-left text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Name</th>
                <th className="w-[160px] px-4 text-left text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Category</th>
                <th className="w-[140px] px-4 text-right text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Unit Price</th>
                <th className="w-[100px] px-4 text-center text-[11px] font-medium font-['Poppins',sans-serif] text-[#212529] uppercase tracking-[0.5px]">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center">
                    <div className="flex justify-center">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-600"></div>
                    </div>
                  </td>
                </tr>
              ) : products.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-sm text-gray-500 font-['Poppins',sans-serif]">
                    {searchQuery ? 'No products found' : 'Enter a search term to find products'}
                  </td>
                </tr>
              ) : (
                products.map((product) => (
                  <tr
                    key={product.id}
                    className={`hover:bg-emerald-50/50 transition-colors cursor-pointer ${selectedProduct?.id === product.id ? 'bg-emerald-50' : ''}`}
                    onClick={() => handleSelectProduct(product)}
                  >
                    <td className="px-4 py-3 text-[12px] font-medium text-gray-600 font-['Poppins',sans-serif]">#{product.id}</td>
                    <td className="px-4 py-3">
                      {product.image ? (
                        <img
                          src={product.image}
                          alt={product.name}
                          className="w-10 h-10 object-cover rounded border border-gray-200"
                        />
                      ) : (
                        <div className="w-10 h-10 bg-gray-100 rounded border border-gray-200 flex items-center justify-center">
                          <DollarSign className="w-4 h-4 text-gray-400" />
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-[13px] font-medium text-gray-900 font-['Poppins',sans-serif] line-clamp-1" title={product.name}>
                        {product.name}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-[13px] text-gray-600 font-['Poppins',sans-serif]">
                      {product.category?.name || product.categoryName || '-'}
                    </td>
                    <td className="px-4 py-3 text-[13px] font-semibold text-emerald-600 font-['Poppins',sans-serif] text-right">
                      {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(product.unitPrice)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${selectedProduct?.id === product.id
                          ? 'bg-emerald-600 text-white'
                          : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
                          }`}
                      >
                        {selectedProduct?.id === product.id ? 'Selected' : 'Select'}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        {!loading && totalPages > 1 && (
          <div className="flex items-center justify-center mt-6">
            <div className="flex items-center gap-2">
              {/* Previous button */}
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${currentPage === 1
                  ? 'text-gray-400 cursor-not-allowed'
                  : 'text-[#3bb77e] hover:bg-[#def9ec]'
                  }`}
              >
                ‹ Previous
              </button>

              {/* Page numbers */}
              {(() => {
                const maxPagesToShow = 5;
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
                      onClick={() => setCurrentPage(1)}
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
                      onClick={() => setCurrentPage(page)}
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
                      onClick={() => setCurrentPage(totalPages)}
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
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className={`px-3 py-2 rounded transition-colors text-[12px] font-['Poppins',sans-serif] ${currentPage === totalPages
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
        {!loading && products.length > 0 && (
          <div className="text-center text-sm text-gray-600 font-['Poppins',sans-serif] mt-4">
            Showing {((currentPage - 1) * limit) + 1} to{' '}
            {Math.min(currentPage * limit, totalProducts)} of{' '}
            {totalProducts} products
          </div>
        )}
      </div>

      {/* Details & History Section (Visible when product selected) */}
      {selectedProduct && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Price Update Form */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 relative overflow-hidden h-full">
              <div className="absolute top-0 right-0 w-24 h-24 bg-blue-50 rounded-bl-full -mr-4 -mt-4"></div>
              <div className="relative z-10">
                <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
                  <DollarSign className="w-5 h-5 text-blue-600" />
                  Update Price
                </h3>

                <div className="flex items-center gap-4 mb-6 p-4 bg-gray-50 rounded-xl border border-gray-100">
                  {selectedProduct.image ? (
                    <img
                      src={selectedProduct.image}
                      alt={selectedProduct.name}
                      className="w-12 h-12 rounded-lg object-cover"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-lg bg-gray-200 flex items-center justify-center">
                      <DollarSign className="w-6 h-6 text-gray-400" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-gray-900 truncate" title={selectedProduct.name}>{selectedProduct.name}</h4>
                    <p className="text-xs text-gray-500">ID: #{selectedProduct.id} {selectedProduct.barcode ? `| Barcode: ${selectedProduct.barcode}` : ''}</p>
                  </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5">
                  <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Current Unit Price
                    </label>
                    <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                      <p className="text-xl font-bold text-gray-700 font-mono">
                        {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(selectedProduct.unitPrice)}
                      </p>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      New Price (VND) <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <input
                        type="number"
                        value={newPrice}
                        onChange={(e) => setNewPrice(e.target.value)}
                        className="w-full pl-4 pr-12 py-3 bg-white border border-gray-300 rounded-lg text-lg font-bold text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono transition-shadow shadow-sm"
                        min="0"
                        placeholder="0"
                        required
                      />
                      <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 font-medium text-sm">
                        VND
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                      Reason for Change
                    </label>
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      className="w-full px-4 py-3 bg-white border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 min-h-[100px] shadow-sm resize-none"
                      placeholder="e.g., Seasonal adjustment, Supplier price increase..."
                    ></textarea>
                  </div>

                  {error && (
                    <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm flex items-start gap-2 border border-red-100">
                      <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                      <span>{error}</span>
                    </div>
                  )}

                  {success && (
                    <div className="p-3 bg-emerald-50 text-emerald-700 rounded-lg text-sm flex items-start gap-2 border border-emerald-100">
                      <Save className="w-4 h-4 mt-0.5 shrink-0" />
                      <span>{success}</span>
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-all shadow-md shadow-blue-200 mt-2"
                  >
                    {submitting ? <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div> : <Save className="w-5 h-5" />}
                    Update Price
                  </button>
                </form>
              </div>
            </div>
          </div>

          {/* Price History */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 h-full flex flex-col relative overflow-hidden">
              <div className="absolute top-0 left-0 w-1 h-full bg-purple-500"></div>
              <h3 className="text-lg font-semibold text-gray-900 mb-6 flex items-center gap-2">
                <History className="w-5 h-5 text-purple-600" />
                Price History
              </h3>

              {historyLoading ? (
                <div className="flex-1 flex items-center justify-center min-h-[300px]">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                </div>
              ) : priceHistory.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-gray-400 min-h-[300px] bg-gray-50/50 rounded-xl border-2 border-dashed border-gray-200">
                  <History className="w-12 h-12 text-gray-300 mb-3" />
                  <p className="font-medium">No price changes recorded</p>
                  <p className="text-xs mt-1">History will appear here after the first price update</p>
                </div>
              ) : (
                <div className="overflow-hidden rounded-lg border border-gray-100">
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="bg-gray-50 border-b border-gray-200">
                          <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Date</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Old Price</th>
                          <th className="px-6 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Change</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">New Price</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Reason</th>
                          <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">By</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 bg-white">
                        {priceHistory.map((log) => {
                          const oldPrice = parseFloat(log.old_price || log.oldPrice || 0);
                          const newPrice = parseFloat(log.new_price || log.newPrice || 0);
                          const isIncrease = newPrice > oldPrice;
                          const changedAt = log.changed_at || log.createdAt;
                          const logReason = log.reason || '-';

                          // changed_by is just an integer ID from DB
                          const changedById = log.changed_by || log.createdBy?.id;
                          const changedByName = log.createdBy?.employee?.fullName
                            || log.createdBy?.username
                            || (changedById ? `Employee #${changedById}` : 'System');
                          const changedByInitials = changedByName === 'System' ? '?' : changedByName.charAt(0).toUpperCase();

                          return (
                            <tr key={log.id} className="hover:bg-gray-50 transition-colors">
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                {new Date(changedAt).toLocaleDateString('vi-VN', {
                                  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
                                })}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">
                                {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(oldPrice)}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-center">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${isIncrease ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'
                                  }`}>
                                  {isIncrease ? 'Increase' : 'Decrease'}
                                </span>
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm font-bold font-mono text-gray-900">
                                {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(newPrice)}
                              </td>
                              <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate" title={logReason}>
                                {logReason}
                              </td>
                              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                <div className="flex items-center gap-2">
                                  <div className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500 ring-2 ring-white">
                                    {changedByInitials}
                                  </div>
                                  <span className="truncate max-w-[100px]" title={changedByName}>{changedByName}</span>
                                </div>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
