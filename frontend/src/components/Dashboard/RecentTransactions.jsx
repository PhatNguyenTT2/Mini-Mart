import React from 'react';
import { Clock } from 'lucide-react';

export const RecentTransactions = ({ data, loading }) => {
  const formatCurrency = (value) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      delivered: {
        label: 'Delivered',
        className: 'bg-emerald-100 text-emerald-700'
      },
      pending: {
        label: 'Pending',
        className: 'bg-orange-100 text-orange-700'
      },
      cancelled: {
        label: 'Cancelled',
        className: 'bg-red-100 text-red-700'
      },
      processing: {
        label: 'Processing',
        className: 'bg-blue-100 text-blue-700'
      }
    };

    const config = statusConfig[status] || {
      label: status,
      className: 'bg-gray-100 text-gray-700'
    };

    return (
      <span className={`inline-block px-3 py-1 rounded-md text-xs font-semibold ${config.className}`}>
        {config.label}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <div className="h-6 bg-gray-200 rounded w-48 mb-4 animate-pulse"></div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 bg-gray-100 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-6">
          <Clock size={20} className="text-gray-600" />
          <h3 className="text-base font-semibold text-gray-900">Recent Transactions</h3>
          <span className="bg-emerald-500 text-white text-xs font-semibold px-2 py-1 rounded-full">
            0
          </span>
        </div>
        <div className="py-12 flex items-center justify-center text-gray-500 text-sm">
          No transactions found
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-6">
        <Clock size={20} className="text-gray-600" />
        <h3 className="text-base font-semibold text-gray-900">Recent Transactions</h3>
        <span className="bg-emerald-500 text-white text-xs font-semibold px-2 py-1 rounded-full">
          {data.length}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Order ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Customer Name
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Phone Number
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Total Amount
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Date
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.map((transaction, index) => (
              <tr key={index} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-4 whitespace-nowrap">
                  <span className="text-sm font-semibold text-blue-600">
                    {transaction.id}
                  </span>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <span className="text-sm text-gray-900">
                    {transaction.customer}
                  </span>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <span className="text-sm text-gray-600">
                    {transaction.phone}
                  </span>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <span className="text-sm font-medium text-gray-900">
                    {formatCurrency(transaction.amount)}
                  </span>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <span className="text-sm text-gray-600">
                    {transaction.date}
                  </span>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  {getStatusBadge(transaction.status)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
