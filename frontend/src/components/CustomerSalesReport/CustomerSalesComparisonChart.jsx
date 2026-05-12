import React, { useEffect, useRef } from 'react';
import { TrendingUp } from 'lucide-react';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

export const CustomerSalesComparisonChart = ({ customers = [] }) => {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !customers || customers.length === 0) return;

    if (chartRef.current) {
      chartRef.current.destroy();
    }

    // Take top 10 customers by revenue
    const topCustomers = customers.slice(0, 10);

    const ctx = canvasRef.current.getContext('2d');
    chartRef.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: topCustomers.map(c => c.customerCode),
        datasets: [
          {
            label: 'Revenue',
            data: topCustomers.map(c => c.totalRevenue),
            backgroundColor: 'rgba(168, 85, 247, 0.8)',
            borderColor: 'rgb(168, 85, 247)',
            borderWidth: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: 12,
            titleFont: { size: 13, weight: 'bold' },
            bodyFont: { size: 12 },
            callbacks: {
              title: function (context) {
                const index = context[0].dataIndex;
                const customer = topCustomers[index];
                return customer.customerName + ' (' + customer.customerCode + ')';
              },
              label: function (context) {
                const value = context.parsed.y;
                return 'Revenue: ₫' + Number(value).toLocaleString('vi-VN');
              },
              afterLabel: function (context) {
                const index = context.dataIndex;
                const customer = topCustomers[index];
                return [
                  'Orders: ' + customer.totalOrders.toLocaleString(),
                  'Items: ' + customer.totalQuantity.toLocaleString(),
                  'Type: ' + customer.customerType.toUpperCase()
                ];
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function (value) {
                if (value >= 1000000) {
                  return '₫' + (value / 1000000).toFixed(1) + 'M';
                } else if (value >= 1000) {
                  return '₫' + (value / 1000).toFixed(0) + 'K';
                }
                return '₫' + value;
              },
              color: '#626c7c',
              font: { size: 12 }
            },
            border: { display: false },
            grid: { color: 'rgba(0, 0, 0, 0.05)' }
          },
          x: {
            ticks: {
              color: '#626c7c',
              font: { size: 12 }
            },
            border: { display: false },
            grid: { display: false }
          }
        }
      }
    });

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [customers]);

  if (!customers || customers.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm py-16 text-center">
        <TrendingUp className="mx-auto h-16 w-16 text-gray-400" />
        <h3 className="mt-4 text-[16px] font-semibold text-gray-900">
          No customer data found
        </h3>
        <p className="mt-2 text-[13px] text-gray-500">
          There are no customer sales in the selected date range
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-[16px] font-semibold text-gray-900 flex items-center gap-2">
            Customer Revenue Comparison
          </h3>
          <p className="text-[12px] text-gray-600 mt-1">
            Top {Math.min(10, customers.length)} customers by revenue
          </p>
        </div>
      </div>

      <div className="relative h-80">
        <canvas ref={canvasRef}></canvas>
      </div>
    </div>
  );
};
