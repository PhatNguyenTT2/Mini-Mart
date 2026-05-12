import React, { useState } from 'react';
import { PackageOpen } from 'lucide-react';

export const ProfitProductList = ({ products = [], loading = false }) => {
  const [sortBy, setSortBy] = useState('profit'); // profit, revenue, cost, margin
  const [sortOrder, setSortOrder] = useState('desc');

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₫0';
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const sortedProducts = [...products].sort((a, b) => {
    let compareValue = 0;

    switch (sortBy) {
      case 'profit':
        compareValue = a.profit - b.profit;
        break;
      case 'revenue':
        compareValue = a.totalRevenue - b.totalRevenue;
        break;
      case 'cost':
        compareValue = a.totalCost - b.totalCost;
        break;
      case 'margin':
        compareValue = a.profitMargin - b.profitMargin;
        break;
      default:
        compareValue = 0;
    }

    return sortOrder === 'asc' ? compareValue : -compareValue;
  });

  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm py-12 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-600 mx-auto"></div>
        <p className="mt-4 text-sm text-gray-500">Loading profit data...</p>
      </div>
    );
  }

  if (!products || products.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm py-16 text-center">
        <PackageOpen className="mx-auto h-16 w-16 text-gray-400" />
        <h3 className="mt-4 text-base font-semibold text-gray-900">No product data found</h3>
        <p className="mt-2 text-sm text-gray-500">
          There are no products with sales or purchases in the selected period
        </p>
      </div>
    );
  }

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

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden hover:shadow-md transition-shadow">
      <div className="overflow-x-auto">
        <table className="w-full">
          {/* Table Header */}
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                Product
              </th>
              <th
                className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('revenue')}
              >
                Sold / Revenue <SortIcon field="revenue" />
              </th>
              <th className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                Stock Out
              </th>
              <th
                className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('cost')}
              >
                Purchased / Cost <SortIcon field="cost" />
              </th>
              <th
                className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('profit')}
              >
                Profit <SortIcon field="profit" />
              </th>
              <th
                className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('margin')}
              >
                Margin <SortIcon field="margin" />
              </th>
            </tr>
          </thead>

          {/* Table Body */}
          <tbody className="divide-y divide-gray-100">
            {sortedProducts.map((product, index) => {
              const isProfitable = product.profit >= 0;
              const profitColor = isProfitable ? 'text-green-600' : 'text-red-600';
              const profitBgColor = isProfitable ? 'bg-green-50' : 'bg-red-50';

              return (
                <tr
                  key={product.productId || index}
                  className="hover:bg-gray-50 transition-colors"
                >
                  {/* Product Info */}
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      {product.image && (
                        <img
                          src={product.image}
                          alt={product.productName}
                          className="w-12 h-12 object-cover rounded-lg"
                        />
                      )}
                      <div>
                        <p className="text-[13px] font-medium text-gray-900">
                          {product.productName}
                        </p>
                        <p className="text-[11px] text-gray-500">
                          {product.productCode} • {product.categoryName}
                        </p>
                      </div>
                    </div>
                  </td>

                  {/* Sales Data */}
                  <td className="px-6 py-4 text-right">
                    <p className="text-[13px] font-semibold text-green-700">
                      {formatCurrency(product.totalRevenue)}
                    </p>
                    <p className="text-[11px] text-gray-600">
                      {product.quantitySold} units • {product.salesOrders} orders
                    </p>
                    <p className="text-[10px] text-gray-500">
                      Avg: {formatCurrency(product.averageSellingPrice)}
                    </p>
                  </td>

                  {/* Stock Out Data */}
                  <td className="px-6 py-4 text-right">
                    {/* Stock Out Sales */}
                    {product.stockOutSalesQuantity > 0 && (
                      <div className="mb-2">
                        <p className="text-[12px] font-semibold text-emerald-600">
                          +{formatCurrency(product.stockOutSalesRevenue)}
                        </p>
                        <p className="text-[10px] text-gray-600">
                          {product.stockOutSalesQuantity} units • {product.stockOutSalesOrders} SO sales
                        </p>
                      </div>
                    )}
                    {/* Stock Out Losses */}
                    {product.stockOutLossQuantity > 0 && (
                      <div>
                        <p className="text-[12px] font-semibold text-rose-600">
                          -{formatCurrency(product.stockOutLossValue)}
                        </p>
                        <p className="text-[10px] text-gray-600">
                          {product.stockOutLossQuantity} units • {product.stockOutLossOrders} SO losses
                        </p>
                      </div>
                    )}
                    {/* No stock out activity */}
                    {product.stockOutSalesQuantity === 0 && product.stockOutLossQuantity === 0 && (
                      <p className="text-[11px] text-gray-400">No stock out</p>
                    )}
                  </td>

                  {/* Purchase Data */}
                  <td className="px-6 py-4 text-right">
                    <p className="text-[13px] font-semibold text-red-700">
                      {formatCurrency(product.totalCost)}
                    </p>
                    <p className="text-[11px] text-gray-600">
                      {product.quantityPurchased} units • {product.purchaseOrders} POs
                    </p>
                    <p className="text-[10px] text-gray-500">
                      Avg: {formatCurrency(product.averageCostPrice)}
                    </p>
                  </td>

                  {/* Profit */}
                  <td className="px-6 py-4 text-right">
                    <div className={`inline-flex flex-col items-end px-3 py-2 rounded-lg ${profitBgColor}`}>
                      <p className={`text-[14px] font-bold ${profitColor}`}>
                        {formatCurrency(product.profit)}
                      </p>
                      <p className="text-[10px] text-gray-600">
                        {formatCurrency(product.profitPerUnit)}/unit
                      </p>
                    </div>
                  </td>

                  {/* Margin */}
                  <td className="px-6 py-4 text-right">
                    <div className="inline-flex items-center gap-2">
                      <div
                        className="w-16 bg-gray-200 rounded-full h-2"
                        title={`${product.profitMargin.toFixed(1)}%`}
                      >
                        <div
                          className={`h-2 rounded-full ${product.profitMargin >= 0 ? 'bg-blue-500' : 'bg-orange-500'
                            }`}
                          style={{
                            width: `${Math.min(Math.abs(product.profitMargin), 100)}%`
                          }}
                        />
                      </div>
                      <span className={`text-[13px] font-semibold ${profitColor} min-w-[3rem] text-right`}>
                        {product.profitMargin.toFixed(1)}%
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer Summary */}
      <div className="bg-gray-50 border-t border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between text-[12px]">
          <span className="text-gray-600">
            Showing {sortedProducts.length} product{sortedProducts.length !== 1 ? 's' : ''}
          </span>
          <span className="text-gray-500">
            Click column headers to sort
          </span>
        </div>
      </div>
    </div>
  );
};