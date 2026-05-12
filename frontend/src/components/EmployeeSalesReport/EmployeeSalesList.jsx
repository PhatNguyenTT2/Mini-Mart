import React, { useState } from 'react';
import { ChevronDown, ChevronUp, TrendingUp, Package, ShoppingBag, Users } from 'lucide-react';

export const EmployeeSalesList = ({ employees = [], loading = false }) => {
  const [expandedEmployee, setExpandedEmployee] = useState(null);
  const [sortBy, setSortBy] = useState('rank');
  const [sortOrder, setSortOrder] = useState('asc');

  const formatCurrency = (amount) => {
    if (!amount && amount !== 0) return '₫0';

    // Handle Mongoose Decimal128
    if (typeof amount === 'object' && amount.$numberDecimal) {
      return `₫${Number(amount.$numberDecimal).toLocaleString('vi-VN')}`;
    }

    return `₫${Number(amount).toLocaleString('vi-VN')}`;
  };

  const formatDate = (date) => {
    return new Date(date).toLocaleDateString('vi-VN');
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

  const sortedEmployees = [...employees].sort((a, b) => {
    let compareValue = 0;

    switch (sortBy) {
      case 'rank':
        compareValue = a.rank - b.rank;
        break;
      case 'totalRevenue':
        compareValue = a.totalRevenue - b.totalRevenue;
        break;
      case 'totalOrders':
        compareValue = a.totalOrders - b.totalOrders;
        break;
      default:
        compareValue = 0;
    }

    return sortOrder === 'asc' ? compareValue : -compareValue;
  });

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

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm py-12 text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-[13px] text-gray-500">
          Loading employee data...
        </p>
      </div>
    );
  }

  if (!employees || employees.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm py-16 text-center">
        <Users className="mx-auto h-16 w-16 text-gray-400" />
        <h3 className="mt-4 text-[16px] font-semibold text-gray-900">
          No employee data found
        </h3>
        <p className="mt-2 text-[13px] text-gray-500">
          There are no employee sales in the selected date range
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
                Employee
              </th>
              <th
                className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('totalOrders')}
              >
                Orders <SortIcon field="totalOrders" />
              </th>
              <th className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                Items Sold
              </th>
              <th
                className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('totalRevenue')}
              >
                Revenue <SortIcon field="totalRevenue" />
              </th>
              <th className="px-6 py-3 text-right text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                Avg Order
              </th>
              <th className="px-6 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                Share %
              </th>
              <th className="px-6 py-3 text-center text-[11px] font-medium text-gray-700 uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>

          {/* Table Body */}
          <tbody className="divide-y divide-gray-100">
            {sortedEmployees.map((employee) => (
              <>
                <tr
                  key={employee.employeeId}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold border ${getRankBadge(employee.rank)}`}>
                      {getRankIcon(employee.rank)}
                      #{employee.rank}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center">
                        <span className="text-blue-600 font-semibold text-[13px]">
                          {employee.employeeName.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="ml-3">
                        <p className="text-[13px] font-semibold text-gray-900">
                          {employee.employeeName}
                        </p>
                        <p className="text-[11px] text-gray-500">
                          {employee.employeeCode}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-[13px] font-semibold text-gray-900">
                    {employee.totalOrders.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-[13px] text-gray-700">
                    {employee.totalQuantity.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-[13px] font-semibold text-blue-600">
                    {formatCurrency(employee.totalRevenue)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-[13px] text-gray-700">
                    {formatCurrency(employee.averageOrderValue)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="flex items-center justify-center">
                      <div className="w-20 bg-gray-200 rounded-full h-2 mr-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full"
                          style={{ width: `${employee.revenuePercentage}%` }}
                        ></div>
                      </div>
                      <span className="text-[12px] font-semibold text-gray-700">
                        {employee.revenuePercentage}%
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <button
                      onClick={() => setExpandedEmployee(
                        expandedEmployee === employee.employeeId ? null : employee.employeeId
                      )}
                      className="inline-flex items-center px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors text-[12px] font-medium"
                    >
                      {expandedEmployee === employee.employeeId ? (
                        <>
                          <ChevronUp className="w-4 h-4 mr-1" />
                          Hide
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-4 h-4 mr-1" />
                          View
                        </>
                      )}
                    </button>
                  </td>
                </tr>

                {/* Expanded Orders */}
                {expandedEmployee === employee.employeeId && (
                  <tr>
                    <td colSpan="8" className="px-6 py-4 bg-gray-50">
                      <div className="space-y-3">
                        <div className="flex items-center gap-2 text-[13px] font-semibold text-gray-900 mb-3">
                          <ShoppingBag className="w-4 h-4" />
                          Order History ({employee.orders.length} orders)
                        </div>
                        <div className="max-h-64 overflow-y-auto">
                          <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-white">
                              <tr>
                                <th className="px-4 py-2 text-left text-[11px] font-semibold text-gray-600 uppercase">
                                  Order #
                                </th>
                                <th className="px-4 py-2 text-left text-[11px] font-semibold text-gray-600 uppercase">
                                  Customer
                                </th>
                                <th className="px-4 py-2 text-left text-[11px] font-semibold text-gray-600 uppercase">
                                  Phone
                                </th>
                                <th className="px-4 py-2 text-center text-[11px] font-semibold text-gray-600 uppercase">
                                  Items
                                </th>
                                <th className="px-4 py-2 text-right text-[11px] font-semibold text-gray-600 uppercase">
                                  Total
                                </th>
                                <th className="px-4 py-2 text-right text-[11px] font-semibold text-gray-600 uppercase">
                                  Date
                                </th>
                              </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-100">
                              {employee.orders.map((order) => (
                                <tr key={order.orderId} className="hover:bg-gray-50">
                                  <td className="px-4 py-3 text-[12px] font-medium text-blue-600">
                                    {order.orderNumber}
                                  </td>
                                  <td className="px-4 py-3 text-[12px] text-gray-900">
                                    {order.customer}
                                  </td>
                                  <td className="px-4 py-3 text-[12px] text-gray-600">
                                    {order.phone}
                                  </td>
                                  <td className="px-4 py-3 text-center text-[12px] text-gray-700">
                                    {order.itemCount}
                                  </td>
                                  <td className="px-4 py-3 text-right text-[12px] font-semibold text-gray-900">
                                    {formatCurrency(order.total)}
                                  </td>
                                  <td className="px-4 py-3 text-right text-[12px] text-gray-600">
                                    {formatDate(order.orderDate)}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
