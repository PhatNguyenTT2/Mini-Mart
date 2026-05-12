import React, { useState } from 'react';
import { Eye, Package, TrendingUp } from 'lucide-react';
import { ViewPurchaseDetailsModal } from './ViewPurchaseDetailsModal';

export const PurchaseList = ({ purchaseData = [], summary = null, loading = false }) => {
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [viewDetailsModal, setViewDetailsModal] = useState(false);
  const [sortBy, setSortBy] = useState('rank');
  const [sortOrder, setSortOrder] = useState('asc');

  const handleViewDetails = (product) => {
    setSelectedProduct(product);
    setViewDetailsModal(true);
  };

  const handleCloseModal = () => {
    setViewDetailsModal(false);
    setSelectedProduct(null);
  };

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const SortIcon = ({ field }) => {
    if (sortBy !== field) return null;
    return sortOrder === 'asc' ? (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline ml-1">
        <path d="M6 3V9M6 3L4 5M6 3L8 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ) : (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg" className="inline ml-1">
        <path d="M6 9V3M6 9L4 7M6 9L8 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  };

  const getRankBadge = (rank) => {
    if (rank === 1) return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    if (rank === 2) return 'bg-gray-100 text-gray-800 border-gray-300';
    if (rank === 3) return 'bg-orange-100 text-orange-800 border-orange-300';
    return 'bg-blue-50 text-blue-700 border-blue-200';
  };

  const getRankIcon = (rank) => {
    if (rank <= 3) {
      return <TrendingUp className="w-3 h-3 mr-1" />;
    }
    return null;
  };

  // Add rank to products and sort
  const rankedProducts = [...purchaseData].map((product, index) => ({
    ...product,
    rank: index + 1
  }));

  const sortedProducts = [...rankedProducts].sort((a, b) => {
    let compareValue = 0;

    switch (sortBy) {
      case 'rank':
        compareValue = a.rank - b.rank;
        break;
      case 'totalCost':
        compareValue = a.totalCost - b.totalCost;
        break;
      case 'totalQuantity':
        compareValue = a.totalQuantity - b.totalQuantity;
        break;
      case 'totalOrders':
        compareValue = a.totalOrders - b.totalOrders;
        break;
      default:
        compareValue = 0;
    }

    return sortOrder === 'asc' ? compareValue : -compareValue;
  });

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₫0';

    // Handle Mongoose Decimal128
    if (typeof amount === 'object' && amount.$numberDecimal) {
      return `₫${Number(amount.$numberDecimal).toLocaleString('vi-VN')}`;
    }

    return `₫${Number(amount).toLocaleString('vi-VN')}`;
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm py-12 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-[13px] text-gray-500">
          Loading purchase data...
        </p>
      </div>
    );
  }

  if (!purchaseData || purchaseData.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm py-16 text-center">
        <Package className="mx-auto h-16 w-16 text-gray-400" />
        <h3 className="mt-4 text-[16px] font-semibold text-gray-900">
          No purchase data found
        </h3>
        <p className="mt-2 text-[13px] text-gray-500">
          There are no purchase orders in the selected date range
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm overflow-hidden">
      {/* Table Container */}
      <div className="overflow-x-auto">
        <table className="w-full">
          {/* Table Header */}
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th
                className="px-6 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('rank')}
              >
                Rank <SortIcon field="rank" />
              </th>
              <th className="px-6 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                Product
              </th>
              <th className="px-6 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                Category
              </th>
              <th
                className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('totalQuantity')}
              >
                Qty Purchased <SortIcon field="totalQuantity" />
              </th>
              <th className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                Cost
              </th>
              <th
                className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('totalCost')}
              >
                Total Cost <SortIcon field="totalCost" />
              </th>
              <th
                className="px-6 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('totalOrders')}
              >
                Orders <SortIcon field="totalOrders" />
              </th>
              <th className="px-6 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>

          {/* Table Body */}
          <tbody className="divide-y divide-gray-100">
            {sortedProducts.map((product) => (
              <tr
                key={product.productId || product.rank}
                className="hover:bg-gray-50 transition-colors"
              >
                {/* Rank */}
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold border ${getRankBadge(product.rank)}`}>
                    {getRankIcon(product.rank)}
                    #{product.rank}
                  </span>
                </td>

                {/* Product */}
                <td className="px-6 py-4">
                  <div>
                    <p className="text-[13px] font-medium text-gray-900">
                      {product.productName}
                    </p>
                    <p className="text-[11px] text-gray-500">
                      {product.productCode}
                    </p>
                  </div>
                </td>

                {/* Category */}
                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-purple-100 text-purple-800">
                    {product.categoryName}
                  </span>
                </td>

                {/* Quantity Purchased */}
                <td className="px-6 py-4 text-right">
                  <p className="text-[13px] font-semibold text-purple-600">
                    {product.totalQuantity.toLocaleString()}
                  </p>
                </td>

                {/* Average Cost */}
                <td className="px-6 py-4 text-right">
                  <p className="text-[13px] text-gray-700">
                    {formatCurrency(product.averageCost)}
                  </p>
                </td>

                {/* Total Cost */}
                <td className="px-6 py-4 text-right">
                  <p className="text-[14px] font-semibold text-blue-600">
                    {formatCurrency(product.totalCost)}
                  </p>
                </td>

                {/* Total Orders */}
                <td className="px-6 py-4 text-center">
                  <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-[12px] font-semibold text-gray-700">
                    {product.totalOrders}
                  </span>
                </td>

                {/* Actions */}
                <td className="px-6 py-4 text-center">
                  <button
                    onClick={() => handleViewDetails(product)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-600 hover:text-blue-700 rounded-lg transition-colors text-[12px] font-medium"
                    title="View details"
                  >
                    <Eye className="w-4 h-4" />
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>

          {/* Table Footer with Summary */}
          {summary && (
            <tfoot className="bg-gray-50 border-t-2 border-gray-300">
              <tr>
                <td colSpan="3" className="px-6 py-4">
                  <div className="space-y-1">
                    <p className="text-[13px] font-semibold text-gray-900">
                      Summary Statistics
                    </p>
                    <p className="text-[12px] text-gray-600">
                      {summary.totalProducts} products • {summary.totalOrders} purchase orders
                    </p>
                  </div>
                </td>
                <td className="px-6 py-4 text-right">
                  <p className="text-[11px] text-gray-500 uppercase">Total Qty</p>
                  <p className="text-[14px] font-bold text-purple-600">
                    {summary.totalQuantity.toLocaleString()}
                  </p>
                </td>
                <td className="px-6 py-4 text-right">
                  <p className="text-[11px] text-gray-500 uppercase">PO</p>
                  <p className="text-[13px] font-semibold text-gray-700">
                    {formatCurrency(summary.averageOrderValue)}
                  </p>
                </td>
                <td colSpan="3" className="px-6 py-4 text-right">
                  <p className="text-[11px] text-gray-500 uppercase mb-1">Total Cost</p>
                  <p className="text-[18px] font-bold text-blue-600">
                    {formatCurrency(summary.totalCost)}
                  </p>
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>

      {/* View Purchase Details Modal */}
      {viewDetailsModal && (
        <ViewPurchaseDetailsModal
          product={selectedProduct}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
};
