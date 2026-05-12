import { useState, useEffect } from 'react';

import { Breadcrumb } from '../../components/Breadcrumb';
import {
  ProfitSummaryCards,
  ProfitComparisonChart,
  MonthlyBreakdownChart,
  ProfitProductList
} from '../../components/ProfitReport';
import { TrendingUp, Calendar } from 'lucide-react';
import api from '../../services/api';

const ProfitReports = () => {
  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Reports', href: '/reports' },
    { label: 'Profit', href: null },
  ];

  // State management
  const [profitData, setProfitData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filter state
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

  // Generate year options (current year and 5 years back)
  const currentYear = new Date().getFullYear();
  const yearOptions = Array.from({ length: 6 }, (_, i) => currentYear - i);

  // Fetch profit report
  const fetchProfitReport = async (year) => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get('/statistics/profit', {
        params: { year }
      });

      if (response.data.success) {
        setProfitData(response.data.data);
      } else {
        setError('Failed to load profit report');
      }
    } catch (err) {
      console.error('Error fetching profit report:', err);
      setError(err.response?.data?.error || err.message || 'Failed to load profit report');
    } finally {
      setLoading(false);
    }
  };

  // Fetch data when year changes
  useEffect(() => {
    fetchProfitReport(selectedYear);
  }, [selectedYear]);

  const handleYearChange = (year) => {
    setSelectedYear(year);
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-[24px] font-semibold text-gray-900">
                Profit & Loss Analysis
              </h1>
              <p className="text-[13px] text-gray-600 mt-1">
                Compare revenue vs costs to analyze profitability
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Year Selector */}
      <div className="bg-white rounded-lg shadow-sm p-6">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[13px] font-medium text-gray-700 mb-2 flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Select Year
              </label>
              <div className="relative">
                <input
                  type="number"
                  value={selectedYear}
                  onChange={(e) => {
                    const year = parseInt(e.target.value);
                    if (year >= 2000 && year <= currentYear + 1) {
                      handleYearChange(year);
                    }
                  }}
                  min="2000"
                  max={currentYear + 1}
                  className="w-full px-4 py-2.5 border-2 border-gray-300 rounded-lg text-[14px] font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  placeholder="Enter year"
                />
                <Calendar className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="block text-[13px] font-medium text-gray-700 mb-2">
                Quick Select
              </label>
              <div className="flex gap-2">
                {yearOptions.slice(0, 3).map((year) => (
                  <button
                    key={year}
                    type="button"
                    className={`flex-1 px-3 py-2 rounded-lg border text-[12px] font-medium transition-colors ${selectedYear === year
                      ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                      : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                      }`}
                    onClick={() => handleYearChange(year)}
                  >
                    {year}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {profitData && (
            <div className="pt-4 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <p className="text-[12px] text-gray-600">
                  Showing data for: <span className="font-semibold text-gray-900">{profitData.year}</span>
                  <span className="mx-2">•</span>
                  Period: <span className="font-semibold text-gray-900">January 1 - December 31, {profitData.year}</span>
                </p>
                <button
                  onClick={() => fetchProfitReport(selectedYear)}
                  className="px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-[12px] font-medium flex items-center gap-1.5"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Refresh
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-[13px]">
          <p className="font-semibold">Error</p>
          <p className="text-[12px] mt-1">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="bg-white rounded-lg shadow-sm py-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-[13px] text-gray-500">Loading profit analysis...</p>
        </div>
      )}

      {/* Main Content */}
      {!loading && profitData && (
        <>
          {/* Summary Cards */}
          <ProfitSummaryCards summary={profitData.summary} />

          {/* Revenue vs Cost Comparison */}
          <div>
            <h2 className="text-[16px] font-semibold text-gray-900 mb-4">
              Revenue vs Cost Breakdown
            </h2>
            <ProfitComparisonChart
              products={profitData.products}
              summary={profitData.summary}
            />
          </div>

          {/* <div>
              <h2 className="text-[16px] font-semibold text-gray-900 mb-4">
                Monthly Trend Analysis
              </h2>
              <MonthlyBreakdownChart monthlyBreakdown={profitData.monthlyBreakdown} />
            </div> */}

          {/* Product List */}
          <div>
            <h2 className="text-[16px] font-semibold text-gray-900 mb-4">
              Product Profit Details
            </h2>
            <ProfitProductList products={profitData.products} loading={false} />
          </div>
        </>
      )}

      {/* Empty State */}
      {!loading && !profitData && !error && (
        <div className="bg-white rounded-lg shadow-sm py-16 text-center">
          <TrendingUp className="mx-auto h-16 w-16 text-gray-400" />
          <h3 className="mt-4 text-[16px] font-semibold text-gray-900">
            No Data Available
          </h3>
          <p className="mt-2 text-[13px] text-gray-500">
            Select a year to view profit analysis
          </p>
        </div>
      )}
    </div>
  );
};

export default ProfitReports;
