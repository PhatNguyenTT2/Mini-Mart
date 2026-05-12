import React, { useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

export const PurchaseChart = ({ purchaseData }) => {
  const chartData = useMemo(() => {
    if (!purchaseData || purchaseData.length === 0) return [];

    const categoryMap = new Map();

    purchaseData.forEach(product => {
      const category = product.categoryName || 'Uncategorized';
      const cost = product.totalCost || 0;

      if (categoryMap.has(category)) {
        categoryMap.set(category, categoryMap.get(category) + cost);
      } else {
        categoryMap.set(category, cost);
      }
    });

    return Array.from(categoryMap.entries())
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
  }, [purchaseData]);

  const chartTotal = useMemo(() => chartData.reduce((sum, item) => sum + item.value, 0), [chartData]);

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658'];

  if (chartData.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Purchases by Category</h3>
      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              outerRadius={120}
              fill="#8884d8"
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name, props) => {
                const percent = ((value / chartTotal) * 100).toFixed(1);
                return [
                  `${new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value)} (${percent}%)`,
                  props.payload.name
                ];
              }}
            />
            <Legend layout="vertical" verticalAlign="middle" align="right" />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
