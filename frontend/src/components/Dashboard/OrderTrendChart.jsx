import React, { useEffect, useRef } from 'react';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

export const OrderTrendChart = ({ data, loading, periodLabel, comparisonLabel }) => {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !data || loading) return;

    // Destroy previous chart if exists
    if (chartRef.current) {
      chartRef.current.destroy();
    }

    const ctx = canvasRef.current.getContext('2d');
    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.labels || [],
        datasets: [
          {
            label: periodLabel || 'Current Period',
            data: data.current || [],
            borderColor: '#1eb988',
            backgroundColor: 'rgba(30, 185, 136, 0.05)',
            borderWidth: 2,
            fill: true,
            pointRadius: 4,
            pointBackgroundColor: '#1eb988',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            tension: 0.4
          },
          {
            label: comparisonLabel || 'Previous Period',
            data: data.previous || [],
            borderColor: '#e68161',
            backgroundColor: 'rgba(230, 129, 97, 0.05)',
            borderWidth: 2,
            fill: true,
            pointRadius: 4,
            pointBackgroundColor: '#e68161',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            tension: 0.4
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
            titleFont: {
              size: 13,
              weight: 'bold'
            },
            bodyFont: {
              size: 12
            },
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
              font: {
                size: 12
              }
            },
            border: {
              display: false
            },
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            }
          },
          x: {
            ticks: {
              color: '#626c7c',
              font: {
                size: 12
              }
            },
            border: {
              display: false
            },
            grid: {
              display: false
            }
          }
        }
      }
    });

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [data, loading, periodLabel, comparisonLabel]);

  if (loading) {
    return (
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <div className="h-6 bg-gray-200 rounded w-40 mb-4 animate-pulse"></div>
        <div className="h-80 bg-gray-100 rounded animate-pulse"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-xl p-6 shadow-sm">
        <h3 className="text-base font-semibold text-gray-900 mb-4">Order Trends</h3>
        <div className="h-80 flex items-center justify-center text-gray-500 text-sm">
          No data available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-base font-semibold text-gray-900">Order Trends</h3>
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
            <span className="text-gray-600">{periodLabel || 'Current Period'}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-orange-500"></div>
            <span className="text-gray-600">{comparisonLabel || 'Previous Period'}</span>
          </div>
        </div>
      </div>
      <div className="relative h-80">
        <canvas ref={canvasRef}></canvas>
      </div>
    </div>
  );
};
