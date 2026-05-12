import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const SERIES = [
  { key: 'alpha', name: 'α Content', color: '#3b82f6', dash: '' },
  { key: 'beta', name: 'β CF', color: '#10b981', dash: '' },
  { key: 'gamma', name: 'γ Apriori', color: '#f59e0b', dash: '' },
  { key: 'delta', name: 'δ Session', color: '#f43f5e', dash: '5 5' },
];

const formatDate = (dateStr) => {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()}`;
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const point = payload[0]?.payload;
  return (
    <div className="bg-white shadow-lg rounded-lg border border-gray-200 p-3 text-xs">
      <p className="font-medium text-gray-700 mb-1.5">
        {new Date(point.date).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
      </p>
      {payload.map(p => (
        <div key={p.dataKey} className="flex items-center gap-2 py-0.5">
          <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-gray-600">{p.name}:</span>
          <span className="font-bold text-gray-800">{(p.value * 100).toFixed(1)}%</span>
        </div>
      ))}
      {point.triggerType && (
        <div className="mt-1.5 pt-1.5 border-t border-gray-100 text-gray-500">
          Trigger: {point.triggerType === 'manual' ? '⚡ Manual' : point.triggerType === 'nightly' ? '🌙 Nightly' : `📌 ${point.triggerType}`}
        </div>
      )}
    </div>
  );
};

export const WeightEvolutionChart = ({ data, currentWeights, loading }) => {
  const history = data?.history || [];

  // If no history but we have current weights, show a single point
  const chartData = history.length > 0
    ? history.map(h => ({ ...h, dateLabel: formatDate(h.date) }))
    : currentWeights
      ? [{ ...currentWeights, date: new Date().toISOString(), dateLabel: 'Now', triggerType: 'current' }]
      : [];

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-800">Weight Evolution</h3>
        {currentWeights && (
          <div className="flex gap-2 text-[10px] text-gray-500">
            <span className="px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded">α={currentWeights.alpha}</span>
            <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-600 rounded">β={currentWeights.beta}</span>
            <span className="px-1.5 py-0.5 bg-amber-50 text-amber-600 rounded">γ={currentWeights.gamma}</span>
            <span className="px-1.5 py-0.5 bg-rose-50 text-rose-600 rounded">δ={currentWeights.delta}</span>
          </div>
        )}
      </div>

      {loading ? (
        <div className="h-48 bg-gray-100 rounded-lg animate-pulse" />
      ) : chartData.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
          No weight history available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: -15, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis dataKey="dateLabel" tick={{ fontSize: 10, fill: '#9ca3af' }} />
            <YAxis domain={[0, 0.65]} tick={{ fontSize: 10, fill: '#9ca3af' }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
            <Tooltip content={<CustomTooltip />} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
            {SERIES.map(s => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.name}
                stroke={s.color}
                strokeWidth={2}
                strokeDasharray={s.dash}
                dot={(props) => {
                  const isManual = chartData[props.index]?.triggerType === 'manual';
                  return (
                    <circle
                      cx={props.cx}
                      cy={props.cy}
                      r={isManual ? 5 : 3}
                      fill={isManual ? '#fbbf24' : props.stroke}
                      stroke={isManual ? '#f59e0b' : 'white'}
                      strokeWidth={isManual ? 2 : 1.5}
                    />
                  );
                }}
                activeDot={{ r: 5 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
};
