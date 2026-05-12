import React from 'react';
import { TrendingUp, TrendingDown, DollarSign, Percent, ShoppingBag, Package2, PackageX, PackagePlus } from 'lucide-react';

export const ProfitSummaryCards = ({ summary }) => {
  if (!summary) return null;

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₫0';
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount);
  };

  const cards = [
    {
      title: 'Total Revenue',
      value: summary.totalRevenue,
      icon: ShoppingBag,
      color: 'cyan',
      iconBgColor: 'bg-cyan-100',
      iconTextColor: 'text-cyan-600',
      borderColor: 'border-cyan-500',
      valueColor: 'text-gray-900',
      subtitle: `${summary.totalSalesOrders} orders`
    },
    {
      title: 'Stock Out Sales',
      value: summary.stockOutSalesRevenue,
      icon: PackagePlus,
      color: 'emerald',
      iconBgColor: 'bg-emerald-100',
      iconTextColor: 'text-emerald-600',
      borderColor: 'border-emerald-500',
      valueColor: 'text-gray-900',
      subtitle: `${summary.totalStockOutSalesOrders} stock outs`
    },
    {
      title: 'Total Cost',
      value: summary.totalCost,
      icon: Package2,
      color: 'orange',
      iconBgColor: 'bg-orange-100',
      iconTextColor: 'text-orange-600',
      borderColor: 'border-orange-500',
      valueColor: 'text-gray-900',
      subtitle: `${summary.totalPurchaseOrders} POs`
    },
    {
      title: 'Stock Out Losses',
      value: summary.stockOutLossValue,
      icon: PackageX,
      color: 'rose',
      iconBgColor: 'bg-rose-100',
      iconTextColor: 'text-rose-600',
      borderColor: 'border-rose-500',
      valueColor: 'text-gray-900',
      subtitle: `${summary.totalStockOutLossOrders} loss events`
    },
    {
      title: 'Combined Revenue',
      value: summary.combinedRevenue,
      icon: TrendingUp,
      color: 'blue',
      iconBgColor: 'bg-blue-100',
      iconTextColor: 'text-blue-600',
      borderColor: 'border-blue-500',
      valueColor: 'text-gray-900',
      subtitle: 'Orders + Stock Out Sales'
    },
    {
      title: 'Combined Cost',
      value: summary.combinedCost,
      icon: TrendingDown,
      color: 'amber',
      iconBgColor: 'bg-amber-100',
      iconTextColor: 'text-amber-600',
      borderColor: 'border-amber-500',
      valueColor: 'text-gray-900',
      subtitle: 'Purchases + Losses'
    },
    {
      title: 'Gross Profit',
      value: summary.grossProfit,
      icon: summary.grossProfit >= 0 ? TrendingUp : TrendingDown,
      color: summary.grossProfit >= 0 ? 'blue' : 'red',
      iconBgColor: summary.grossProfit >= 0 ? 'bg-blue-100' : 'bg-red-100',
      iconTextColor: summary.grossProfit >= 0 ? 'text-blue-600' : 'text-red-600',
      borderColor: summary.grossProfit >= 0 ? 'border-blue-500' : 'border-red-500',
      valueColor: summary.grossProfit >= 0 ? 'text-gray-900' : 'text-gray-900',
      subtitle: 'Combined Revenue - Cost'
    },
    {
      title: 'Profit Margin',
      value: `${summary.profitMargin.toFixed(1)}%`,
      icon: Percent,
      color: 'purple',
      iconBgColor: 'bg-purple-100',
      iconTextColor: 'text-purple-600',
      borderColor: 'border-purple-500',
      valueColor: 'text-gray-900',
      subtitle: 'Profit / Combined Revenue',
      isPercentage: true
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {cards.map((card, index) => {
        const Icon = card.icon;
        const displayValue = card.isPercentage ? card.value : formatCurrency(card.value);

        return (
          <div
            key={index}
            className={`bg-white rounded-xl p-6 border-l-4 ${card.borderColor} shadow-sm hover:shadow-md transition-shadow`}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="text-xs font-semibold text-gray-600 uppercase tracking-wider">
                {card.title}
              </div>
              <div className={`w-10 h-10 rounded-lg ${card.iconBgColor} flex items-center justify-center`}>
                <Icon className={`w-5 h-5 ${card.iconTextColor}`} />
              </div>
            </div>

            <div className={`text-3xl font-semibold ${card.valueColor} mb-3`}>
              {displayValue}
            </div>

            <div className="text-xs text-gray-500">
              {card.subtitle}
            </div>
          </div>
        );
      })}
    </div>
  );
};