import React, { useState, useEffect } from 'react';
import { Breadcrumb } from '../../components/Breadcrumb';
import { PermissionAlert } from '../../components/PermissionAlert';
import {
  InventoryReportSummaryCards,
  StockStatusOverview,
  StockDistributionChart,
  StockMovementChart,
  InventoryProductList
} from '../../components/InventoryReport';
import api from '../../services/api';

export const InventoryReport = () => {
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    categoryId: '',
    view: 'all'
  });

  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Inventory Report', href: '/inventory-report' }
  ];

  useEffect(() => {
    fetchReportData();
  }, [filters]);

  const fetchReportData = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = {};
      if (filters.categoryId) params.categoryId = filters.categoryId;
      if (filters.view !== 'all') params.view = filters.view;

      const response = await api.get('/statistics/inventory', { params });

      if (response.data.success) {
        setReportData(response.data.data);
      } else {
        throw new Error('Failed to fetch inventory report');
      }
    } catch (err) {
      console.error('Error fetching inventory report:', err);
      setError(err.message || 'Failed to load inventory report');
    } finally {
      setLoading(false);
    }
  };

  const handleViewChange = (view) => {
    setFilters(prev => ({ ...prev, view }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <Breadcrumb items={breadcrumbItems} />
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <p className="text-red-800 font-medium">{error}</p>
          <button
            onClick={fetchReportData}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Breadcrumb items={breadcrumbItems} />
      <PermissionAlert requiredPermission="view_inventory_report" />

      <div className="space-y-6">
        {/* Header with Filters */}
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900">Inventory Report</h1>

          <div className="flex items-center gap-3">
            {/* View Filter */}
            <div className="flex items-center gap-2 bg-white rounded-lg shadow-sm p-1">
              <button
                onClick={() => handleViewChange('all')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${filters.view === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
                  }`}
              >
                All
              </button>
              <button
                onClick={() => handleViewChange('low-stock')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${filters.view === 'low-stock'
                  ? 'bg-yellow-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
                  }`}
              >
                Low Stock
              </button>
              <button
                onClick={() => handleViewChange('out-of-stock')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${filters.view === 'out-of-stock'
                  ? 'bg-red-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
                  }`}
              >
                Out of Stock
              </button>
              <button
                onClick={() => handleViewChange('needs-reorder')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${filters.view === 'needs-reorder'
                  ? 'bg-orange-600 text-white'
                  : 'text-gray-600 hover:bg-gray-100'
                  }`}
              >
                Needs Reorder
              </button>
            </div>
          </div>
        </div>

        {/* Summary Cards */}
        <InventoryReportSummaryCards summary={reportData?.summary} />

        {/* Status Overview + Distribution Chart */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <StockStatusOverview stockStatus={reportData?.stockStatus} />
          <div className="lg:col-span-2">
            <StockDistributionChart data={reportData?.categoryDistribution} />
          </div>
        </div>

        {/* Stock Movement Chart */}
        <StockMovementChart data={reportData?.stockMovement} />

        {/* Products Table */}
        <InventoryProductList products={reportData?.products} />
      </div>
    </div>
  );
};

export default InventoryReport;