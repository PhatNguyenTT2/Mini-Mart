import React from 'react';
import { Database, TrendingUp, Layers, Activity } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const DUAL_STREAM_COLORS = {
  organic: '#14b8a6', // Teal
  chatbot: '#6366f1', // Indigo
};

const SIMILARITY_COLORS = {
  high: '#10b981', // Emerald
  medium: '#f59e0b', // Amber
  low: '#ef4444', // Red
};

export const CFMatrixHealth = ({ data, loading }) => {
  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6 animate-pulse">
        <div className="h-4 w-1/3 bg-gray-200 rounded mb-6"></div>
        <div className="h-24 bg-gray-100 rounded-xl mb-6"></div>
        <div className="flex gap-4">
          <div className="flex-1 h-32 bg-gray-50 rounded-xl"></div>
          <div className="flex-1 h-32 bg-gray-50 rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6 text-center text-gray-400">
        <Database className="mx-auto mb-2 opacity-50" size={32} />
        <p className="text-sm">No CF Matrix data available</p>
      </div>
    );
  }

  const { interactionMatrix: im, implicitSignals: is, similarityMatrix: sm } = data;

  const densityPercent = im?.density ? (im.density * 100).toFixed(2) : '0.00';
  
  // Chart Data
  const streamData = [
    { name: 'Organic', value: is?.organicCount || 0, fill: DUAL_STREAM_COLORS.organic },
    { name: 'Chatbot', value: is?.chatbotCount || 0, fill: DUAL_STREAM_COLORS.chatbot },
  ];

  const simData = [
    { name: 'High (≥0.5)', value: sm?.highSimilarity || 0, fill: SIMILARITY_COLORS.high },
    { name: 'Med (0.2-0.5)', value: sm?.mediumSimilarity || 0, fill: SIMILARITY_COLORS.medium },
    { name: 'Low (<0.2)', value: sm?.lowSimilarity || 0, fill: SIMILARITY_COLORS.low },
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
          <Database size={16} className="text-indigo-500" />
          CF Matrix Health
        </h3>
        {sm?.lastComputedAt && (
          <span className="text-[10px] text-gray-400 bg-gray-50 px-2 py-1 rounded">
            Updated: {new Date(sm.lastComputedAt).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
          </span>
        )}
      </div>

      {/* Density Gauge */}
      <div className="bg-gray-50 rounded-xl p-4 mb-5 border border-gray-100">
        <div className="flex justify-between items-end mb-2">
          <div>
            <div className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1">Matrix Density</div>
            <div className="text-2xl font-bold text-gray-800 flex items-baseline gap-1">
              {densityPercent}%
              <TrendingUp size={14} className="text-emerald-500" />
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-gray-500">Users: <span className="font-semibold text-gray-700">{im?.totalUsers}</span></div>
            <div className="text-xs text-gray-500">Products: <span className="font-semibold text-gray-700">{im?.totalProducts}</span></div>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-2 mt-2 overflow-hidden">
          <div 
            className="bg-indigo-500 h-2 rounded-full transition-all duration-1000" 
            style={{ width: `${Math.min(Math.max(im?.density * 100 * 5, 2), 100)}%` }} // Visual scaling
          ></div>
        </div>
        <div className="flex justify-between text-[10px] text-gray-400 mt-1">
          <span>Sparse</span>
          <span>Dense</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Dual Stream Breakdown */}
        <div className="bg-white border border-gray-100 rounded-xl p-3 flex flex-col items-center">
          <div className="text-[11px] font-medium text-gray-500 uppercase flex items-center gap-1 w-full mb-1">
            <Activity size={12} /> Data Source
          </div>
          <div className="h-28 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={streamData}
                  cx="50%" cy="50%"
                  innerRadius={25} outerRadius={40}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {streamData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: '10px', padding: '4px 8px', borderRadius: '4px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex gap-3 text-[10px] mt-1">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-teal-500"></div> Organic
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-indigo-500"></div> Chatbot
            </div>
          </div>
        </div>

        {/* Similarity Distribution */}
        <div className="bg-white border border-gray-100 rounded-xl p-3 flex flex-col items-center">
          <div className="text-[11px] font-medium text-gray-500 uppercase flex items-center gap-1 w-full mb-1">
            <Layers size={12} /> Similarity Pairs
          </div>
          <div className="h-28 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={simData}
                  cx="50%" cy="50%"
                  outerRadius={40}
                  dataKey="value"
                  stroke="none"
                >
                  {simData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: '10px', padding: '4px 8px', borderRadius: '4px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="text-[10px] text-gray-500 font-medium">
            Total Pairs: {sm?.totalPairs}
          </div>
        </div>
      </div>
      
    </div>
  );
};
