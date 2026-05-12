import React from 'react';
import {
  TrendingUp,
  TrendingDown,
  ShoppingCart,
  Package,
  Users,
  DollarSign
} from 'lucide-react';

const SummaryCard = ({ label, value, change, icon: Icon, color, isRevenue = false }) => {
  const isNegative = change < 0;
  const colorClasses = {
    cyan: 'border-cyan-500 bg-cyan-50',
    blue: 'border-blue-500 bg-blue-50',
    purple: 'border-purple-500 bg-purple-50',
    orange: 'border-orange-500 bg-orange-50'
  };

  const iconColorClasses = {
    cyan: 'bg-cyan-100 text-cyan-600',
    blue: 'bg-blue-100 text-blue-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600'
  };

  const formatValue = (val) => {
    if (isRevenue) {
      return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(val);
    }
    return val?.toLocaleString() || '0';
  };

  return (
    <div className={`bg-white rounded-xl p-6 border-l-4 ${colorClasses[color]} shadow-sm hover:shadow-md transition-shadow`}>
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs font-semibold text-gray-600 uppercase tracking-wider">
          {label}
        </div>
        <div className={`w-10 h-10 rounded-lg ${iconColorClasses[color]} flex items-center justify-center`}>
          <Icon size={20} />
        </div>
      </div>

      <div className="text-3xl font-semibold text-gray-900 mb-3">
        {formatValue(value)}
      </div>

      <div className={`flex items-center gap-1 text-xs font-medium ${isNegative ? 'text-red-600' : 'text-emerald-600'}`}>
        {isNegative ? <TrendingDown size={14} /> : <TrendingUp size={14} />}
        <span>{Math.abs(change)}%</span>
        <span className="text-gray-500 ml-1">vs previous period</span>
      </div>
    </div>
  );
};

export const SummaryCards = ({ summary, loading }) => {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white rounded-xl p-6 border-l-4 border-gray-200 shadow-sm animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-24 mb-4"></div>
            <div className="h-8 bg-gray-200 rounded w-32 mb-3"></div>
            <div className="h-4 bg-gray-200 rounded w-28"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!summary) {
    return null;
  }

  const cards = [
    {
      label: 'Total Orders',
      value: summary.totalOrders,
      change: summary.changes?.totalOrders || 0,
      icon: ShoppingCart,
      color: 'cyan'
    },
    {
      label: 'Total Sales',
      value: summary.totalSales,
      change: summary.changes?.totalSales || 0,
      icon: Package,
      color: 'blue'
    },
    {
      label: 'New Customers',
      value: summary.newCustomers,
      change: summary.changes?.newCustomers || 0,
      icon: Users,
      color: 'purple'
    },
    {
      label: 'Total Revenue',
      value: summary.totalRevenue,
      change: summary.changes?.totalRevenue || 0,
      icon: DollarSign,
      color: 'orange',
      isRevenue: true
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {cards.map((card, index) => (
        <SummaryCard key={index} {...card} />
      ))}
    </div>
  );
};
