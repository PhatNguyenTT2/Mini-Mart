import React, { useEffect, useRef } from 'react';
import { Chart, registerables } from 'chart.js';
import { PieChart } from 'lucide-react';

Chart.register(...registerables);

export const StockDistributionChart = ({ data }) => {
  const chartRef = useRef(null);
  const chartInstance = useRef(null);

  useEffect(() => {
    if (!data || data.length === 0 || !chartRef.current) return;

    const ctx = chartRef.current.getContext('2d');

    // Destroy existing chart
    if (chartInstance.current) {
      chartInstance.current.destroy();
    }

    // Create new chart
    chartInstance.current = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.map(cat => cat.categoryName),
        datasets: [{
          data: data.map(cat => cat.percentage),
          backgroundColor: data.map(cat => cat.color),
          borderWidth: 2,
          borderColor: '#ffffff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              padding: 15,
              font: {
                size: 12
              },
              generateLabels: (chart) => {
                const data = chart.data;
                if (data.labels.length && data.datasets.length) {
                  return data.labels.map((label, i) => {
                    const value = data.datasets[0].data[i];
                    return {
                      text: `${label}: ${value}%`,
                      fillStyle: data.datasets[0].backgroundColor[i],
                      hidden: false,
                      index: i
                    };
                  });
                }
                return [];
              }
            }
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const label = context.label || '';
                const value = context.parsed || 0;
                const categoryData = data[context.dataIndex];
                return [
                  `${label}: ${value}%`,
                  `Quantity: ${categoryData.totalQuantity.toLocaleString('vi-VN')}`,
                  `Products: ${categoryData.productCount}`
                ];
              }
            }
          }
        }
      }
    });

    return () => {
      if (chartInstance.current) {
        chartInstance.current.destroy();
      }
    };
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6">
        <div className="flex items-center gap-2 mb-6">
          <PieChart className="w-5 h-5 text-gray-700" />
          <h3 className="text-lg font-semibold text-gray-900">Stock Distribution by Category</h3>
        </div>
        <div className="text-center py-12 text-gray-500">
          No category data available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="flex items-center gap-2 mb-6">
        <PieChart className="w-5 h-5 text-gray-700" />
        <h3 className="text-lg font-semibold text-gray-900">Stock Distribution by Category</h3>
      </div>

      <div className="h-80">
        <canvas ref={chartRef}></canvas>
      </div>
    </div>
  );
};
