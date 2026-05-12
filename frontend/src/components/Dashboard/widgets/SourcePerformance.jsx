import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const SOURCE_CONFIG = {
  content: { label: 'Content', color: '#3b82f6', bg: 'bg-blue-50', text: 'text-blue-700' },
  cf: { label: 'CF (Item-based)', color: '#10b981', bg: 'bg-emerald-50', text: 'text-emerald-700' },
  apriori: { label: 'Apriori', color: '#f59e0b', bg: 'bg-amber-50', text: 'text-amber-700' },
  session: { label: 'Session', color: '#f43f5e', bg: 'bg-rose-50', text: 'text-rose-700' },
  organic: { label: 'Organic', color: '#14b8a6', bg: 'bg-teal-50', text: 'text-teal-700' },
};

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const data = payload[0]?.payload;
  return (
    <div className="bg-white shadow-lg rounded-lg border border-gray-200 p-3 text-xs">
      <p className="font-semibold text-gray-700 mb-1">{data.label}</p>
      <div className="space-y-0.5">
        <p>Recommended: <span className="font-bold">{data.recommended}</span></p>
        <p>Clicked: <span className="font-bold">{data.clicked}</span></p>
        <p>Purchased: <span className="font-bold">{data.purchased}</span></p>
        <p>CTR: <span className="font-bold text-blue-600">{(data.ctr * 100).toFixed(1)}%</span></p>
        <p>CVR: <span className="font-bold text-emerald-600">{(data.cvr * 100).toFixed(1)}%</span></p>
      </div>
    </div>
  );
};

export const SourcePerformance = ({ data, loading }) => {
  const chartData = Object.entries(data || {}).map(([source, stats]) => ({
    source,
    label: SOURCE_CONFIG[source]?.label || source,
    recommended: stats.recommended || 0,
    clicked: stats.clicked || 0,
    purchased: stats.purchased || 0,
    ctr: stats.ctr || 0,
    cvr: stats.cvr || 0,
    fill: SOURCE_CONFIG[source]?.color || '#6b7280',
  }));

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-sm font-semibold text-gray-800 mb-4">Source Performance</h3>

      {loading ? (
        <div className="h-48 bg-gray-100 rounded-lg animate-pulse" />
      ) : chartData.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
          No source data available
        </div>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 10, left: 15, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <YAxis type="category" dataKey="label" tick={{ fontSize: 11, fill: '#4b5563' }} width={90} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: '11px' }} />
              <Bar dataKey="recommended" name="Recommended" fill="#d1d5db" radius={[0, 2, 2, 0]} />
              <Bar dataKey="clicked" name="Clicked" fill="#3b82f6" radius={[0, 2, 2, 0]} />
              <Bar dataKey="purchased" name="Purchased" fill="#10b981" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>

          <div className="mt-3 flex flex-wrap gap-2">
            {chartData.map(d => (
              <div key={d.source} className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] ${SOURCE_CONFIG[d.source]?.bg || 'bg-gray-50'} ${SOURCE_CONFIG[d.source]?.text || 'text-gray-600'}`}>
                <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: d.fill }} />
                <span className="font-medium">{d.label}</span>
                <span>CTR {(d.ctr * 100).toFixed(1)}%</span>
                <span className="opacity-50">|</span>
                <span>CVR {(d.cvr * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
