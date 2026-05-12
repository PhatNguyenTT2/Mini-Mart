import React from 'react';
import { CheckCircle2, AlertCircle, XCircle, AlertTriangle } from 'lucide-react';

export const StockStatusOverview = ({ stockStatus }) => {
  if (!stockStatus) return null;

  const statuses = [
    {
      label: 'In Stock',
      value: stockStatus.inStock,
      icon: CheckCircle2,
      bgColor: 'bg-green-50',
      textColor: 'text-green-700',
      iconColor: 'text-green-500',
      borderColor: 'border-green-200'
    },
    {
      label: 'Low Stock',
      value: stockStatus.lowStock,
      icon: AlertCircle,
      bgColor: 'bg-yellow-50',
      textColor: 'text-yellow-700',
      iconColor: 'text-yellow-500',
      borderColor: 'border-yellow-200'
    },
    {
      label: 'Out of Stock',
      value: stockStatus.outOfStock,
      icon: XCircle,
      bgColor: 'bg-red-50',
      textColor: 'text-red-700',
      iconColor: 'text-red-500',
      borderColor: 'border-red-200'
    },
    {
      label: 'Needs Reorder',
      value: stockStatus.needsReorder,
      icon: AlertTriangle,
      bgColor: 'bg-orange-50',
      textColor: 'text-orange-700',
      iconColor: 'text-orange-500',
      borderColor: 'border-orange-200'
    }
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-6">Stock Status</h3>

      <div className="space-y-4">
        {statuses.map((status, index) => {
          const Icon = status.icon;
          return (
            <div
              key={index}
              className={`flex items-center justify-between p-4 rounded-lg border ${status.borderColor} ${status.bgColor}`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-5 h-5 ${status.iconColor}`} />
                <span className={`text-sm font-medium ${status.textColor}`}>
                  {status.label}
                </span>
              </div>
              <span className={`text-2xl font-bold ${status.textColor}`}>
                {status.value}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
