import React, { useEffect, useRef } from 'react';
import { BarChart3 } from 'lucide-react';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

export const MonthlyBreakdownChart = ({ monthlyBreakdown = [] }) => {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !monthlyBreakdown || monthlyBreakdown.length === 0) return;

    if (chartRef.current) {
      chartRef.current.destroy();
    }

    const ctx = canvasRef.current.getContext('2d');
    chartRef.current = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: monthlyBreakdown.map(m => m.monthName),
        datasets: [
          {
            label: 'Revenue',
            data: monthlyBreakdown.map(m => m.revenue),
            backgroundColor: 'rgba(16, 185, 129, 0.8)',
            borderColor: 'rgb(16, 185, 129)',
            borderWidth: 1
          },
          {
            label: 'Cost',
            data: monthlyBreakdown.map(m => m.cost),
            backgroundColor: 'rgba(239, 68, 68, 0.8)',
            borderColor: 'rgb(239, 68, 68)',
            borderWidth: 1
          },
          {
            label: 'Profit',
            data: monthlyBreakdown.map(m => m.profit),
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
              label: function (context) {
                const value = context.parsed.y;
                return context.dataset.label + ': ' + new Intl.NumberFormat('vi-VN', {
                  style: 'currency',
                  currency: 'VND',
                  minimumFractionDigits: 0
                }).format(value);
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
  }, [monthlyBreakdown]);

  if (!monthlyBreakdown || monthlyBreakdown.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-8 text-center">
        <p className="text-gray-500 text-sm">No monthly data available</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-base font-semibold text-gray-900 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            Monthly Trend
          </h3>
          <p className="text-xs text-gray-600 mt-1">Revenue vs Cost comparison by month</p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-emerald-500 rounded-full"></div>
            <span className="text-gray-600">Revenue</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-red-500 rounded-full"></div>
            <span className="text-gray-600">Cost</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span className="text-gray-600">Profit</span>
          </div>
        </div>
      </div>

      <div className="relative h-80">
        <canvas ref={canvasRef}></canvas>
      </div>
    </div>
  );
};
