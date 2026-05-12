import React from 'react';
import { Package, Package2, ShoppingBag, AlertTriangle } from 'lucide-react';

export const InventoryReportSummaryCards = ({ summary }) => {
  if (!summary) return null;

  const formatNumber = (num) => {
    if (!num && num !== 0) return '0';
    return new Intl.NumberFormat('vi-VN').format(num);
  };

  const cards = [
    {
      title: 'Total Stock',
      value: summary.totalQuantity,
      icon: Package,
      color: 'cyan',
      iconBgColor: 'bg-cyan-100',
      iconTextColor: 'text-cyan-600',
      borderColor: 'border-cyan-500',
      subtitle: `${summary.totalProducts} products`
    },
    {
      title: 'Warehouse Stock',
      value: summary.totalWarehouseStock,
      icon: Package2,
      color: 'blue',
      iconBgColor: 'bg-blue-100',
      iconTextColor: 'text-blue-600',
      borderColor: 'border-blue-500',
      subtitle: `${summary.warehouseUtilization}% of total`
    },
    {
      title: 'Shelf Stock',
      value: summary.totalShelfStock,
      icon: ShoppingBag,
      color: 'purple',
      iconBgColor: 'bg-purple-100',
      iconTextColor: 'text-purple-600',
      borderColor: 'border-purple-500',
      subtitle: `${summary.shelfUtilization}% of total`
    },
    {
      title: 'Low Stock Items',
      value: summary.lowStockItems,
      icon: AlertTriangle,
      color: 'orange',
      iconBgColor: 'bg-orange-100',
      iconTextColor: 'text-orange-600',
      borderColor: 'border-orange-500',
      subtitle: `${summary.needsReorderItems} needs reorder`,
      alert: summary.lowStockItems > 0
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {cards.map((card, index) => {
        const Icon = card.icon;

        return (
          <div
            key={index}
            className={`bg-white rounded-xl p-6 border-l-4 ${card.borderColor} shadow-sm hover:shadow-md transition-shadow ${card.alert ? 'ring-2 ring-orange-200' : ''}`}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="text-xs font-semibold text-gray-600 uppercase tracking-wider">
                {card.title}
              </div>
              <div className={`w-10 h-10 rounded-lg ${card.iconBgColor} flex items-center justify-center`}>
                <Icon className={`w-5 h-5 ${card.iconTextColor}`} />
              </div>
            </div>

            <div className="text-3xl font-semibold text-gray-900 mb-3">
              {formatNumber(card.value)}
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
