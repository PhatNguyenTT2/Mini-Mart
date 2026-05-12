import React, { useState } from 'react';
import { ArrowUpDown, Package, MapPin, Calendar } from 'lucide-react';

export const InventoryProductList = ({ products }) => {
  const [sortField, setSortField] = useState('productCode');
  const [sortOrder, setSortOrder] = useState('asc');

  if (!products || products.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-6">Product Inventory</h3>
        <div className="text-center py-12 text-gray-500">
          No products found
        </div>
      </div>
    );
  }

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  };

  const sortedProducts = [...products].sort((a, b) => {
    let aVal = a[sortField];
    let bVal = b[sortField];

    if (aVal == null) aVal = '';
    if (bVal == null) bVal = '';

    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }

    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  const formatNumber = (num) => {
    if (!num && num !== 0) return '0';
    return new Intl.NumberFormat('vi-VN').format(num);
  };

  const getStatusBadge = (product) => {
    if (product.isOutOfStock) {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
          Out of Stock
        </span>
      );
    }
    if (product.needsReorder) {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
          Needs Reorder
        </span>
      );
    }
    if (product.isLowStock) {
      return (
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          Low Stock
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
        In Stock
      </span>
    );
  };

  const SortButton = ({ field, label }) => (
    <button
      onClick={() => handleSort(field)}
      className="flex items-center gap-1 hover:text-gray-900 transition-colors"
    >
      {label}
      <ArrowUpDown className="w-3 h-3" />
    </button>
  );

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">Product Inventory</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                <SortButton field="productCode" label="Code" />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                <SortButton field="productName" label="Product" />
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider">
                <SortButton field="categoryName" label="Category" />
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                <SortButton field="quantityOnHand" label="Warehouse" />
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                <SortButton field="quantityOnShelf" label="Shelf" />
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                <SortButton field="quantityReserved" label="Reserved" />
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-700 uppercase tracking-wider">
                <SortButton field="quantityAvailable" label="Available" />
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-700 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-700 uppercase tracking-wider">
                Info
              </th>
            </tr>
          </thead>

          <tbody className="divide-y divide-gray-100">
            {sortedProducts.map((product, index) => (
              <tr key={product.productId || index} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4">
                  <p className="text-sm font-medium text-gray-900">{product.productCode}</p>
                </td>

                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    {product.image && (
                      <img
                        src={product.image}
                        alt={product.productName}
                        className="w-10 h-10 rounded object-cover"
                      />
                    )}
                    <p className="text-sm font-medium text-gray-900">{product.productName}</p>
                  </div>
                </td>

                <td className="px-6 py-4">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    {product.categoryName}
                  </span>
                </td>

                <td className="px-6 py-4 text-right">
                  <p className="text-sm font-semibold text-blue-600">{formatNumber(product.quantityOnHand)}</p>
                </td>

                <td className="px-6 py-4 text-right">
                  <p className="text-sm font-semibold text-purple-600">{formatNumber(product.quantityOnShelf)}</p>
                </td>

                <td className="px-6 py-4 text-right">
                  <p className="text-sm font-medium text-gray-600">{formatNumber(product.quantityReserved)}</p>
                </td>

                <td className="px-6 py-4 text-right">
                  <p className="text-sm font-bold text-green-600">{formatNumber(product.quantityAvailable)}</p>
                </td>

                <td className="px-6 py-4 text-center">
                  {getStatusBadge(product)}
                </td>

                <td className="px-6 py-4">
                  <div className="flex flex-col gap-1 text-xs text-gray-500">
                    {product.batchCount > 0 && (
                      <div className="flex items-center gap-1">
                        <Package className="w-3 h-3" />
                        <span>{product.batchCount} batches</span>
                      </div>
                    )}
                    {product.warehouseLocation && (
                      <div className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        <span>{product.warehouseLocation}</span>
                      </div>
                    )}
                    {product.oldestBatchDays !== null && (
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        <span>{product.oldestBatchDays}d old</span>
                      </div>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
