import React from 'react';
import { TrendingDown, Send, Eye, MousePointerClick, ShoppingCart, CreditCard } from 'lucide-react';

const STEPS = [
  { key: 'totalRecommended', label: 'Recommended', color: 'bg-gray-400', textColor: 'text-gray-700', icon: <Send size={16} /> },
  { key: 'totalHovered', label: 'Hovered', color: 'bg-indigo-400', textColor: 'text-indigo-700', icon: <Eye size={16} /> },
  { key: 'totalClicked', label: 'Clicked', color: 'bg-blue-500', textColor: 'text-blue-700', icon: <MousePointerClick size={16} /> },
  { key: 'totalAddedToCart', label: 'Added to Cart', color: 'bg-amber-500', textColor: 'text-amber-700', icon: <ShoppingCart size={16} /> },
  { key: 'totalPurchased', label: 'Purchased', color: 'bg-emerald-500', textColor: 'text-emerald-700', icon: <CreditCard size={16} /> },
];

export const ConversionFunnel = ({ data, loading }) => {
  const funnel = data?.funnel || {};
  const rates = data?.rates || {};

  const values = STEPS.map(s => funnel[s.key] || 0);
  const maxValue = Math.max(...values, 1);

  const rateLabels = [
    null,
    rates.hoverRate ? `${(rates.hoverRate * 100).toFixed(1)}% Hover` : null,
    rates.clickThroughRate ? `${(rates.clickThroughRate * 100).toFixed(1)}% CTR` : null,
    rates.addToCartRate ? `${(rates.addToCartRate * 100).toFixed(1)}% A2C` : null,
    rates.conversionRate ? `${(rates.conversionRate * 100).toFixed(1)}% CVR` : null,
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-sm font-semibold text-gray-800 mb-4">Conversion Funnel</h3>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-10 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : values.every(v => v === 0) ? (
        <div className="text-center py-8 text-gray-400">
          <p className="text-sm">No recommendation data yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {STEPS.map((step, idx) => {
            const value = values[idx];
            const width = maxValue > 0 ? Math.max((value / maxValue) * 100, 4) : 4;
            const rate = rateLabels[idx];

            return (
              <div key={step.key}>
                {/* Drop-off indicator */}
                {idx > 0 && rate && (
                  <div className="flex items-center gap-1 text-xs text-gray-400 mb-1 ml-2">
                    <TrendingDown size={10} />
                    <span>{rate}</span>
                  </div>
                )}

                <div className="flex items-center gap-3">
                  <span className="text-base w-5 text-center">{step.icon}</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs font-medium ${step.textColor}`}>{step.label}</span>
                      <span className="text-xs font-bold text-gray-700">{value.toLocaleString()}</span>
                    </div>
                    <div className="h-5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${step.color} rounded-full transition-all duration-700`}
                        style={{ width: `${width}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
