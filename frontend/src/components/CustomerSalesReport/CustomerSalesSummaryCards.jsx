import React from 'react';
import { Users, ShoppingCart, TrendingUp, Award } from 'lucide-react';

export const CustomerSalesSummaryCards = ({ summary }) => {
  if (!summary) return null;

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₫0';

    // Handle Mongoose Decimal128
    if (typeof amount === 'object' && amount.$numberDecimal) {
      return `₫${Number(amount.$numberDecimal).toLocaleString('vi-VN')}`;
    }

    return `₫${Number(amount).toLocaleString('vi-VN')}`;
  };

  return (
    <div className="grid grid-cols-4 gap-4">
      {/* Total Customers */}
      <div className="bg-white rounded-lg shadow-sm p-4 border-l-4 border-purple-500">
        <p className="text-[11px] text-gray-600 font-medium uppercase tracking-wider">Total Customers</p>
        <p className="text-[20px] font-bold text-purple-600 mt-1">
          {summary.totalCustomers || 0}
        </p>
      </div>

      {/* Total Orders */}
      <div className="bg-white rounded-lg shadow-sm p-4 border-l-4 border-green-500">
        <p className="text-[11px] text-gray-600 font-medium uppercase tracking-wider">Total Orders</p>
        <p className="text-[20px] font-bold text-green-600 mt-1">
          {(summary.totalOrders || 0).toLocaleString()}
        </p>
      </div>

      {/* Total Revenue */}
      <div className="bg-white rounded-lg shadow-sm p-4 border-l-4 border-indigo-500">
        <p className="text-[11px] text-gray-600 font-medium uppercase tracking-wider">Total Revenue</p>
        <p className="text-[20px] font-bold text-indigo-600 mt-1">
          {formatCurrency(summary.totalRevenue)}
        </p>
      </div>

      {/* Average Order Value */}
      <div className="bg-white rounded-lg shadow-sm p-4 border-l-4 border-orange-500">
        <p className="text-[11px] text-gray-600 font-medium uppercase tracking-wider">Avg Order Value</p>
        <p className="text-[18px] font-bold text-orange-600 mt-1">
          {formatCurrency(summary.averageOrderValue || 0)}
        </p>
      </div>
    </div>
  );
};
