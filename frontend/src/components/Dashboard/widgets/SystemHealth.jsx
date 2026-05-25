import React, { useState } from 'react';
import { Clock, CheckCircle, XCircle, AlertTriangle, Activity, Check, X, Play, Loader } from 'lucide-react';

const LatencyBar = ({ label, data, maxMs }) => {
  if (!data || data.avg === 0) return null;
  const width = maxMs > 0 ? Math.max((data.p95 / maxMs) * 100, 5) : 5;
  const severity = data.p95 < 500 ? 'emerald' : data.p95 < 1500 ? 'amber' : 'red';
  const colors = {
    emerald: { bar: 'bg-emerald-400', text: 'text-emerald-700' },
    amber: { bar: 'bg-amber-400', text: 'text-amber-700' },
    red: { bar: 'bg-red-400', text: 'text-red-700' },
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-600">{label}</span>
        <span className={`text-xs font-bold ${colors[severity].text}`}>P95: {data.p95}ms</span>
      </div>
      <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${colors[severity].bar} rounded-full transition-all duration-500`}
          style={{ width: `${width}%` }}
        />
      </div>
      <div className="flex gap-3 text-[10px] text-gray-400">
        <span>Avg: {data.avg}ms</span>
        <span>Min: {data.min}ms</span>
        <span>Max: {data.max}ms</span>
      </div>
    </div>
  );
};

const formatTimeAgo = (dateStr) => {
  if (!dateStr) return 'Never';
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
};

const STEP_LABELS = {
  apriori: 'Apriori',
  cf: 'CF',
  weightLearner: 'Weights',
  cacheWarmup: 'Warmup'
};

export const SystemHealth = ({ latency, batch, loading, onRunBatch }) => {
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchResult, setBatchResult] = useState(null);

  const lastRunAt = batchResult?.lastRunAt || batch?.lastBatchRun;
  const displayResult = batchResult?.result || batch?.batchResult;
  const failCount = displayResult?.failCount || 0;
  const totalMs = displayResult?.totalMs;

  const handleRunBatch = async () => {
    if (!onRunBatch) return;
    setBatchRunning(true);
    setBatchResult(null);
    try {
      const result = await onRunBatch();
      setBatchResult({
        lastRunAt: new Date().toISOString(),
        result
      });
    } catch (err) {
      setBatchResult({
        lastRunAt: new Date().toISOString(),
        result: { failCount: -1, error: err.message }
      });
    } finally {
      setBatchRunning(false);
    }
  };

  const latencySteps = latency ? [
    { label: 'Total Pipeline', data: latency.total },
    { label: 'LLM Generation', data: latency.generation },
    { label: 'Hybrid Scoring', data: latency.hybrid },
    { label: 'Embedding', data: latency.embedding },
  ] : [];

  const maxMs = latencySteps.reduce((max, s) => Math.max(max, s.data?.p95 || 0), 0);

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-sm font-semibold text-gray-800 mb-4 flex items-center gap-2">
        <Activity size={14} className="text-gray-500" />
        System Health
      </h3>

      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map(i => <div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />)}
        </div>
      ) : (
        <div className="space-y-5">
          {/* Latency Section */}
          {latency?.sampleSize > 0 ? (
            <div className="space-y-3">
              <p className="text-[10px] text-gray-400 uppercase tracking-wider">Pipeline Latency (last 24h, {latency.sampleSize} samples)</p>
              {latencySteps.map(s => (
                <LatencyBar key={s.label} label={s.label} data={s.data} maxMs={maxMs} />
              ))}
            </div>
          ) : (
            <div className="text-center py-6 px-4 bg-gray-50 rounded-xl border border-dashed border-gray-200">
              <p className="text-xs font-semibold text-gray-700 mb-1">No latency data in the last 24h</p>
              <p className="text-[10px] text-gray-400 leading-normal max-w-[220px] mx-auto">
                RAG system requires active chat messages to compute performance stats. Type a recommendation request in the chatbot to populate latency data.
              </p>
            </div>
          )}

          {/* Divider */}
          <div className="border-t border-gray-100" />

          {/* Batch Status Section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] text-gray-400 uppercase tracking-wider">Nightly Batch Pipeline</p>
              {onRunBatch && (
                <button
                  onClick={handleRunBatch}
                  disabled={batchRunning}
                  className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                >
                  {batchRunning ? (
                    <>
                      <Loader size={10} className="animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Play size={10} />
                      Run Now
                    </>
                  )}
                </button>
              )}
            </div>

            <div className={`rounded-lg border p-3 ${batchRunning ? 'border-indigo-200 bg-indigo-50' :
              !lastRunAt ? 'border-gray-200 bg-gray-50' :
                failCount === 0 ? 'border-emerald-200 bg-emerald-50' :
                  failCount === -1 ? 'border-red-200 bg-red-50' :
                    'border-amber-200 bg-amber-50'
              }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {batchRunning ? (
                    <Loader size={14} className="text-indigo-500 animate-spin" />
                  ) : !lastRunAt ? (
                    <AlertTriangle size={14} className="text-gray-400" />
                  ) : failCount === 0 ? (
                    <CheckCircle size={14} className="text-emerald-500" />
                  ) : failCount === -1 ? (
                    <XCircle size={14} className="text-red-500" />
                  ) : (
                    <AlertTriangle size={14} className="text-amber-500" />
                  )}
                  <span className="text-xs font-medium text-gray-700">
                    {batchRunning ? 'Running pipeline...' :
                      !lastRunAt ? 'Never run' :
                        failCount === 0 ? 'All steps OK' :
                          failCount === -1 ? 'Pipeline error' :
                            `${failCount} step(s) failed`}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                  <Clock size={10} />
                  <span>{formatTimeAgo(lastRunAt)}</span>
                </div>
              </div>

              {totalMs && (
                <p className="text-[10px] text-gray-500 mt-1.5">
                  Duration: {(totalMs / 1000).toFixed(1)}s
                </p>
              )}

              {displayResult?.error && (
                <p className="text-[10px] text-red-600 mt-1.5">
                  Error: {displayResult.error}
                </p>
              )}

              {displayResult && !displayResult.error && (
                <div className="flex gap-2 mt-2">
                  {Object.keys(STEP_LABELS).map(step => {
                    const status = displayResult[step]?.status;
                    return (
                      <span
                        key={step}
                        className={`inline-flex items-center gap-1 text-[9px] px-1.5 py-0.5 rounded-md ${status === 'success' ? 'bg-emerald-100 text-emerald-700' :
                          status === 'failed' ? 'bg-red-100 text-red-700' :
                            status === 'skipped' ? 'bg-gray-100 text-gray-500' :
                              'bg-gray-100 text-gray-500'
                          }`}
                      >
                        {STEP_LABELS[step]}
                        {status === 'success' && <Check size={10} />}
                        {status === 'failed' && <X size={10} />}
                      </span>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
