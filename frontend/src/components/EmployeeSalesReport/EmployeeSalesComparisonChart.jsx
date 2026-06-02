import React, { useEffect, useRef } from 'react';
import { TrendingUp } from 'lucide-react';
import { Chart, registerables } from 'chart.js';
import { formatEmployeeCode } from '../../utils/formatters';

Chart.register(...registerables);

export const EmployeeSalesComparisonChart = ({ employees = [] }) => {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !employees || employees.length === 0) return;

    if (chartRef.current) {
      chartRef.current.destroy();
    }

    // Take top 10 employees by revenue
    const topEmployees = employees.slice(0, 10);

    const ctx = canvasRef.current.getContext('2d');
    chartRef.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: topEmployees.map(e => formatEmployeeCode(e)),
        datasets: [
          {
            label: 'Revenue',
            data: topEmployees.map(e => e.totalRevenue),
            backgroundColor: 'rgba(59, 130, 246, 0.8)',
            borderColor: 'rgb(59, 130, 246)',
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
                const employee = topEmployees[index];
                return employee.employeeName + ' (' + formatEmployeeCode(employee) + ')';
              },
              label: function (context) {
                const value = context.parsed.y;
                return 'Revenue: ₫' + Number(value).toLocaleString('vi-VN');
              },
              afterLabel: function (context) {
                const index = context.dataIndex;
                const employee = topEmployees[index];
                return [
                  'Orders: ' + employee.totalOrders.toLocaleString(),
                  'Items Sold: ' + employee.totalQuantity.toLocaleString()
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
  }, [employees]);

  if (!employees || employees.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm py-16 text-center">
        <TrendingUp className="mx-auto h-16 w-16 text-gray-400" />
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
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-[16px] font-semibold text-gray-900 flex items-center gap-2">
            Employee Revenue Comparison
          </h3>
          <p className="text-[12px] text-gray-600 mt-1">
            Top {Math.min(10, employees.length)} employees by revenue
          </p>
        </div>
      </div>

      <div className="relative h-80">
        <canvas ref={canvasRef}></canvas>
      </div>
    </div>
  );
};
