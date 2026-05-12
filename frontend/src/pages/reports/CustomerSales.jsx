import { useState, useEffect } from 'react';
import { Breadcrumb } from '../../components/Breadcrumb';
import {
  CustomerSalesSummaryCards,
  CustomerSalesComparisonChart,
  CustomerSalesList
} from '../../components/CustomerSalesReport';
import { Users, Calendar } from 'lucide-react';
import api from '../../services/api';

const CustomerSalesReport = () => {
  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Reports', href: '/reports' },
    { label: 'Customer Sales', href: null }
  ];

  // State management
  const [salesData, setSalesData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filter state
  const [periodType, setPeriodType] = useState('month');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [includeGuests, setIncludeGuests] = useState(false);

  // Initialize dates based on period type
  useEffect(() => {
    handlePeriodTypeChange(periodType);
  }, []);

  const handlePeriodTypeChange = (type) => {
    const now = new Date();
    let start, end;

    switch (type) {
      case 'today':
        start = end = now.toISOString().split('T')[0];
        break;
      case 'week':
        const weekAgo = new Date(now);
        weekAgo.setDate(weekAgo.getDate() - 7);
        start = weekAgo.toISOString().split('T')[0];
        end = now.toISOString().split('T')[0];
        break;
      case 'month':
        start = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().split('T')[0];
        end = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().split('T')[0];
        break;
      case 'quarter':
        const quarter = Math.floor(now.getMonth() / 3);
        start = new Date(now.getFullYear(), quarter * 3, 1).toISOString().split('T')[0];
        end = new Date(now.getFullYear(), quarter * 3 + 3, 0).toISOString().split('T')[0];
        break;
      case 'year':
        start = new Date(now.getFullYear(), 0, 1).toISOString().split('T')[0];
        end = new Date(now.getFullYear(), 11, 31).toISOString().split('T')[0];
        break;
      case 'custom':
        start = end = '';
        break;
      default:
        start = end = '';
    }

    setPeriodType(type);
    setStartDate(start);
    setEndDate(end);
  };

  // Fetch customer sales report
  const fetchCustomerSales = async () => {
    if (!startDate || !endDate) {
      setError('Please select a date range');
      return;
    }

    if (new Date(startDate) > new Date(endDate)) {
      setError('Start date must be before end date');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await api.get('/statistics/customer-sales', {
        params: {
          startDate,
          endDate,
          includeGuests: includeGuests.toString()
        }
      });

      if (response.data.success) {
        setSalesData(response.data.data);
      } else {
        setError('Failed to load customer sales report');
      }
    } catch (err) {
      console.error('Error fetching customer sales report:', err);
      setError(err.response?.data?.error || err.message || 'Failed to load customer sales report');
    } finally {
      setLoading(false);
    }
  };

  // Auto fetch when dates change (but not on initial render with empty dates)
  useEffect(() => {
    if (startDate && endDate) {
      fetchCustomerSales();
    }
  }, [startDate, endDate, includeGuests]);

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-[24px] font-semibold text-gray-900">
              Customer Sales Reports
            </h1>
            <p className="text-[13px] text-gray-600 mt-1">
              Track and analyze customer purchase behavior by date range
            </p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="space-y-4">
          {/* Period Type Selection */}
          <div>
            <label className="block text-[13px] font-medium text-gray-700 mb-2">
              Report Period
            </label>
            <div className="grid grid-cols-6 gap-2">
              {[
                { value: 'today', label: 'Today' },
                { value: 'week', label: 'This Week' },
                { value: 'month', label: 'This Month' },
                { value: 'quarter', label: 'This Quarter' },
                { value: 'year', label: 'This Year' },
                { value: 'custom', label: 'Custom Range' }
              ].map(period => (
                <button
                  key={period.value}
                  type="button"
                  className={`px-4 py-2 rounded-lg border text-[13px] font-medium transition-colors ${periodType === period.value
                      ? 'bg-purple-600 text-white border-purple-600 shadow-sm'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                    }`}
                  onClick={() => handlePeriodTypeChange(period.value)}
                >
                  {period.label}
                </button>
              ))}
            </div>
          </div>

          {/* Date Range and Guest Toggle */}
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-[13px] font-medium text-gray-700 mb-2 flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                max={new Date().toISOString().split('T')[0]}
                className="w-full px-3 py-2 border-2 border-gray-300 rounded-lg text-[13px] focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium text-gray-700 mb-2 flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                max={new Date().toISOString().split('T')[0]}
                className="w-full px-3 py-2 border-2 border-gray-300 rounded-lg text-[13px] focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-lg border-2 border-gray-300 cursor-pointer hover:bg-gray-100 transition-colors w-full">
                <input
                  type="checkbox"
                  checked={includeGuests}
                  onChange={(e) => setIncludeGuests(e.target.checked)}
                  className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                />
                <span className="text-[13px] font-medium text-gray-700">
                  Include Walk-in Guests
                </span>
              </label>
            </div>
            <div className="flex items-end">
              <button
                onClick={fetchCustomerSales}
                disabled={loading || !startDate || !endDate}
                className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-[13px] font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-sm hover:shadow-md"
              >
                {loading ? (
                  <>
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Loading...
                  </>
                ) : (
                  <>
                    View Report
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
          <p className="font-semibold">Error</p>
          <p className="text-[12px] mt-1">{error}</p>
        </div>
      )}

      {/* Summary Cards */}
      {salesData && salesData.summary && (
        <CustomerSalesSummaryCards summary={salesData.summary} />
      )}

      {/* Comparison Chart */}
      {salesData && salesData.customers && salesData.customers.length > 0 && (
        <CustomerSalesComparisonChart customers={salesData.customers} />
      )}

      {/* Customer List */}
      <CustomerSalesList
        customers={salesData?.customers || []}
        loading={loading}
      />
    </div>
  );
};

export default CustomerSalesReport;
