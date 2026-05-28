import React, { useRef, useEffect, useState } from 'react';
import { List, Send, Eye, MousePointerClick, ShoppingCart, CreditCard } from 'lucide-react';

const ACTION_CONFIG = {
  recommended: { icon: <Send size={12} />, label: 'Recommended', bg: 'bg-gray-100', text: 'text-gray-600' },
  hovered: { icon: <Eye size={12} />, label: 'Hovered', bg: 'bg-indigo-50', text: 'text-indigo-700' },
  clicked: { icon: <MousePointerClick size={12} />, label: 'Clicked', bg: 'bg-blue-50', text: 'text-blue-700' },
  added_to_cart: { icon: <ShoppingCart size={12} />, label: 'Added to Cart', bg: 'bg-amber-50', text: 'text-amber-700' },
  purchased: { icon: <CreditCard size={12} />, label: 'Purchased', bg: 'bg-emerald-50', text: 'text-emerald-700' },
};

const SOURCE_COLORS = {
  content: 'bg-blue-100 text-blue-700',
  cf: 'bg-emerald-100 text-emerald-700',
  apriori: 'bg-amber-100 text-amber-700',
  session: 'bg-rose-100 text-rose-700',
  organic: 'bg-teal-100 text-teal-700',
};

const formatTimeAgo = (dateStr) => {
  const diff = Date.now() - new Date(dateStr).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};

export const LiveFeedbackStream = ({ data, loading, selectedSource, setSelectedSource, selectedRecency, setSelectedRecency, sseConnected }) => {
  const feedbacks = data?.feedbacks || [];
  const prevIdsRef = useRef(new Set());
  const [newIds, setNewIds] = useState(new Set());

  useEffect(() => {
    if (feedbacks.length === 0) return;

    const currentIds = new Set(feedbacks.map(fb => fb.id));
    const fresh = new Set();

    if (prevIdsRef.current.size > 0) {
      for (const id of currentIds) {
        if (!prevIdsRef.current.has(id)) {
          fresh.add(id);
        }
      }
    }

    if (fresh.size > 0) {
      setNewIds(fresh);
      // Clear animation after 2 seconds
      const timer = setTimeout(() => setNewIds(new Set()), 2000);
      prevIdsRef.current = currentIds;
      return () => clearTimeout(timer);
    }

    prevIdsRef.current = currentIds;
  }, [feedbacks]);

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 flex flex-col h-[calc(100vh-120px)] min-h-[600px] max-h-[850px] overflow-hidden">
      <div className="flex flex-col gap-2.5 mb-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
            <List size={14} className="text-gray-500" />
            Live Feedback Stream
            {sseConnected ? (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                Live
              </span>
            ) : (
              <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-semibold bg-gray-50 text-gray-500 border border-gray-200">
                <span className="h-1.5 w-1.5 rounded-full bg-gray-400"></span>
                Offline
              </span>
            )}
            {newIds.size > 0 && (
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
            )}
          </h3>
          <span className="text-[10px] text-gray-400">{feedbacks.length} recent interactions</span>
        </div>

        {/* Controls: Source filter + Recency filter */}
        <div className="flex items-center gap-2">
          <select
            value={selectedSource || 'all'}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="flex-1 text-xs bg-gray-50 border border-gray-200 outline-none rounded-lg px-2.5 py-1.5 text-gray-600 focus:border-indigo-300 transition-colors"
          >
            <option value="all">All algorithms</option>
            <option value="content">Content-Based (alpha)</option>
            <option value="cf">Collaborative Filtering (beta)</option>
            <option value="apriori">Apriori Rules (gamma)</option>
            <option value="session">Session Boost (delta)</option>
            <option value="organic">Organic (Non-AI)</option>
          </select>

          <select
            value={selectedRecency || 'all'}
            onChange={(e) => setSelectedRecency(e.target.value)}
            className="text-xs bg-gray-50 border border-gray-200 outline-none rounded-lg px-2.5 py-1.5 text-gray-600 focus:border-indigo-300 transition-colors"
          >
            <option value="all">All time</option>
            <option value="30m">Last 30 min</option>
            <option value="1h">Last 1 hour</option>
            <option value="6h">Last 6 hours</option>
            <option value="24h">Last 24 hours</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="h-10 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : feedbacks.length === 0 ? (
        <div className="text-center py-8 text-gray-400 text-sm">
          No feedback interactions yet
        </div>
      ) : (
        <div className="overflow-y-auto flex-1 pr-2 space-y-3">
          {feedbacks.map((fb) => {
            const actionCfg = ACTION_CONFIG[fb.action] || ACTION_CONFIG.recommended;
            const isNew = newIds.has(fb.id);
            return (
              <div
                key={fb.id}
                className={`p-3 border rounded-lg transition-all duration-500 ${isNew
                  ? 'bg-emerald-50 border-emerald-200 shadow-md animate-pulse ring-1 ring-emerald-300'
                  : 'bg-gray-50 border-gray-100 hover:bg-gray-100'
                  }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-700">
                      {fb.userId ? `User #${fb.userId}` : 'Guest'}
                    </span>
                    <span className="text-[10px] text-gray-400">
                      {formatTimeAgo(fb.createdAt)}
                    </span>
                    {isNew && (
                      <span className="text-[9px] font-bold text-emerald-600 bg-emerald-100 px-1.5 py-0.5 rounded-full uppercase tracking-wider">
                        New
                      </span>
                    )}
                  </div>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${SOURCE_COLORS[fb.source] || 'bg-gray-200 text-gray-700'}`}>
                    {fb.source}
                  </span>
                </div>

                <div className="flex items-start gap-2">
                  <div className={`p-1.5 rounded-md mt-0.5 ${actionCfg.bg} ${actionCfg.text}`}>
                    {actionCfg.icon}
                  </div>
                  <div className="flex-1">
                    <p className="text-xs text-gray-800 leading-snug">
                      <span className={`font-semibold ${actionCfg.text}`}>{actionCfg.label}</span>
                      {' '}
                      <span className="text-gray-600 line-clamp-2" title={fb.productName}>{fb.productName}</span>
                    </p>
                    {fb.score != null && (
                      <p className="text-[10px] text-gray-500 mt-1">
                        AI Score: <span className="font-mono font-medium text-gray-700">{fb.score.toFixed(4)}</span>
                      </p>
                    )}
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
