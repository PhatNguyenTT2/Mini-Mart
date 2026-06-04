import React, { useState, useEffect, useCallback, useRef } from 'react';
import { RefreshCw, Zap, AlertCircle, Timer, TimerOff, RotateCcw } from 'lucide-react';
import api from '../../services/api';
import { ConversionFunnel } from './widgets/ConversionFunnel';
import { WeightEvolutionChart } from './widgets/WeightEvolutionChart';
import { SourcePerformance } from './widgets/SourcePerformance';
import { SystemHealth } from './widgets/SystemHealth';
import { LiveFeedbackStream } from './widgets/LiveFeedbackStream';
import { CFMatrixHealth } from './widgets/CFMatrixHealth';

const STORE_ID = 1;
const AUTO_REFRESH_INTERVAL = 10000; // 10 seconds

export const AIDashboardTab = () => {
  const [days, setDays] = useState(30);
  const [widgetsLoading, setWidgetsLoading] = useState(true);
  const [feedbackLoading, setFeedbackLoading] = useState(true);
  const [sseConnected, setSseConnected] = useState(false);
  const [error, setError] = useState(null);
  const [forceLoading, setForceLoading] = useState(false);
  const [forceResult, setForceResult] = useState(null);
  const [resetLoading, setResetLoading] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);
  const [resetResult, setResetResult] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [selectedSource, setSelectedSource] = useState('all');
  const [selectedRecency, setSelectedRecency] = useState('all');

  const [recData, setRecData] = useState(null);
  const [latencyData, setLatencyData] = useState(null);
  const [feedbackData, setFeedbackData] = useState(null);
  const [weightHistory, setWeightHistory] = useState(null);
  const [cfMatrixData, setCfMatrixData] = useState(null);

  const intervalRef = useRef(null);
  const countdownRef = useRef(null);

  // Ref to hold current filter values to guard against stale closure in SSE handler
  const filterRef = useRef({ selectedSource, selectedRecency });

  useEffect(() => {
    filterRef.current = { selectedSource, selectedRecency };
  }, [selectedSource, selectedRecency]);

  const fetchWidgets = useCallback(async () => {
    setWidgetsLoading(true);
    setError(null);
    try {
      const [recRes, latRes, whRes, cfmRes] = await Promise.all([
        api.get('/chatbot/stats/recommendations', { params: { storeId: STORE_ID, days } }),
        api.get('/chatbot/stats/latency', { params: { storeId: STORE_ID } }),
        api.get('/chatbot/stats/weight-history', { params: { storeId: STORE_ID, limit: 30 } }),
        api.get('/chatbot/stats/cf-matrix', { params: { storeId: STORE_ID } })
      ]);
      setRecData(recRes.data?.data || null);
      setLatencyData(latRes.data?.data || null);
      setWeightHistory(whRes.data?.data || null);
      setCfMatrixData(cfmRes.data?.data || null);
    } catch (err) {
      console.error('AI Dashboard fetch widgets error:', err);
      setError(err.response?.data?.error?.message || err.message || 'Failed to load AI metrics');
    } finally {
      setWidgetsLoading(false);
    }
  }, [days]);

  const fetchFeedback = useCallback(async () => {
    setFeedbackLoading(true);
    try {
      const fbRes = await api.get('/chatbot/stats/feedback-stream', {
        params: { storeId: STORE_ID, limit: 50, source: selectedSource, recency: selectedRecency }
      });
      setFeedbackData(fbRes.data?.data || null);
    } catch (err) {
      console.error('AI Dashboard fetch feedback error:', err);
    } finally {
      setFeedbackLoading(false);
    }
  }, [selectedSource, selectedRecency]);

  const fetchAll = useCallback(async () => {
    await Promise.all([fetchWidgets(), fetchFeedback()]);
  }, [fetchWidgets, fetchFeedback]);

  useEffect(() => {
    fetchWidgets();
  }, [fetchWidgets]);

  useEffect(() => {
    fetchFeedback();
  }, [fetchFeedback]);

  // Connect to SSE for real-time live events without polling
  useEffect(() => {
    const sseUrl = `${import.meta.env.VITE_API_URL || '/api'}/chatbot/stats/feedback-stream/live`;
    const eventSource = new EventSource(sseUrl);

    eventSource.onopen = () => {
      setSseConnected(true);
    };

    eventSource.onerror = () => {
      setSseConnected(false);
    };

    eventSource.onmessage = (event) => {
      try {
        const fb = JSON.parse(event.data);
        const { selectedSource: currentSource } = filterRef.current;

        // Client-side filtering check
        if (currentSource !== 'all' && fb.source !== currentSource) return;

        setFeedbackData(prev => {
          const currentFeedbacks = prev?.feedbacks || [];
          if (currentFeedbacks.some(f => f.id === fb.id)) return prev;

          return {
            ...prev,
            feedbacks: [fb, ...currentFeedbacks].slice(0, 50)
          };
        });
      } catch (err) {
        console.error('Failed to parse SSE live message:', err);
      }
    };

    return () => {
      eventSource.close();
      setSseConnected(false);
    };
  }, []);

  const loading = widgetsLoading || feedbackLoading;

  // Auto-refresh logic
  useEffect(() => {
    if (autoRefresh) {
      setCountdown(AUTO_REFRESH_INTERVAL / 1000);

      countdownRef.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) return AUTO_REFRESH_INTERVAL / 1000;
          return prev - 1;
        });
      }, 1000);

      intervalRef.current = setInterval(() => {
        fetchAll();
      }, AUTO_REFRESH_INTERVAL);
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, [autoRefresh, fetchAll]);

  const handleForceLearn = async () => {
    setForceLoading(true);
    setForceResult(null);
    try {
      const res = await api.post('/chatbot/admin/force-learn', { storeId: STORE_ID });
      setForceResult(res.data?.data || null);
      await fetchAll();
    } catch (err) {
      setForceResult({ error: err.response?.data?.error?.message || err.message });
    } finally {
      setForceLoading(false);
    }
  };

  const handleResetDemo = async () => {
    setResetLoading(true);
    setResetResult(null);
    try {
      const res = await api.post('/chatbot/admin/reset-demo', { storeId: STORE_ID });
      setResetResult(res.data?.data || null);
      setForceResult(null); // Clear force learn result to avoid visual clutter
      setError(null);       // Clear global tab error
      setShowResetConfirm(false);
      await fetchAll();
    } catch (err) {
      setResetResult({ error: err.response?.data?.error?.message || err.message });
    } finally {
      setResetLoading(false);
    }
  };


  const handleRunBatch = async () => {
    const res = await api.post('/chatbot/admin/run-batch', { storeId: STORE_ID });
    const result = res.data?.data;
    // Refresh all data after batch completes
    await fetchAll();
    return result;
  };

  const periodOptions = [
    { value: 7, label: '7 days' },
    { value: 30, label: '30 days' },
    { value: 90, label: '90 days' }
  ];

  if (error && !recData) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-8 text-center">
        <AlertCircle className="mx-auto text-red-400 mb-3" size={40} />
        <p className="text-gray-700 font-medium">Failed to load AI metrics</p>
        <p className="text-sm text-gray-500 mt-1">{error}</p>
        <button
          onClick={fetchAll}
          className="mt-4 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in-smooth">
      {/* Controls Bar */}
      <div className="bg-white rounded-xl shadow-sm p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Period Selector */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500 font-medium">Period:</span>
            <div className="flex bg-gray-100 rounded-lg p-0.5">
              {periodOptions.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setDays(opt.value)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${days === opt.value
                    ? 'bg-white text-emerald-700 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                    }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {/* Auto-refresh toggle */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors border ${autoRefresh
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                : 'text-gray-500 border-gray-300 hover:bg-gray-50'
                }`}
            >
              {autoRefresh ? (
                <>
                  <Timer size={14} />
                  Auto {countdown}s
                </>
              ) : (
                <>
                  <TimerOff size={14} />
                  Auto Off
                </>
              )}
            </button>

            <button
              onClick={fetchAll}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-800 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Refresh
            </button>
            <button
              onClick={handleForceLearn}
              disabled={forceLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-amber-500 hover:bg-amber-600 rounded-lg transition-colors disabled:opacity-50 shadow-sm"
            >
              <Zap size={14} className={forceLoading ? 'animate-pulse' : ''} />
              {forceLoading ? 'Learning...' : 'Force AI Learn'}
            </button>
            <button
              onClick={() => setShowResetConfirm(true)}
              disabled={resetLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50 shadow-sm"
            >
              <RotateCcw size={14} className={resetLoading ? 'animate-spin' : ''} />
              {resetLoading ? 'Resetting...' : 'Reset Demo'}
            </button>
          </div>
        </div>

        {/* Force Learn Result */}
        {forceResult && (
          <div className={`mt-3 px-3 py-2 rounded-lg text-xs ${forceResult.error
            ? 'bg-red-50 text-red-700 border border-red-200'
            : forceResult.skipped
              ? 'bg-amber-50 text-amber-700 border border-amber-200'
              : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
            }`}>
            {forceResult.error
              ? `❌ Error: ${forceResult.error}`
              : forceResult.message
            }
            {forceResult.newWeights && !forceResult.skipped && (
              <span className="ml-2">
                → α={forceResult.newWeights.alpha} β={forceResult.newWeights.beta} γ={forceResult.newWeights.gamma}
              </span>
            )}
          </div>
        )}

        {/* Reset Demo Result */}
        {resetResult && (
          <div className={`mt-3 px-3 py-2 rounded-lg text-xs ${resetResult.error
            ? 'bg-red-50 text-red-700 border border-red-200'
            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
            }`}>
            {resetResult.error
              ? `❌ Error resetting: ${resetResult.error}`
              : resetResult.message
            }
          </div>
        )}
      </div>

      {/* Widgets Layout: Asymmetric Tension (66/33) */}
      <div>
        <div className="flex flex-col lg:flex-row items-start gap-6">
          {/* Left Column: Analytics (66%) */}
          <div className={`w-full lg:w-2/3 flex flex-col gap-6 transition-opacity duration-300 ${widgetsLoading ? 'opacity-60' : 'opacity-100'}`}>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <ConversionFunnel data={recData} loading={widgetsLoading} />
              <WeightEvolutionChart data={weightHistory} currentWeights={recData?.currentWeights} loading={widgetsLoading} />
            </div>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <SourcePerformance data={recData?.sourceBreakdown} loading={widgetsLoading} />
              <CFMatrixHealth data={cfMatrixData} loading={widgetsLoading} />
            </div>
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <SystemHealth
                latency={latencyData}
                batch={recData}
                loading={widgetsLoading}
                onRunBatch={handleRunBatch}
              />
            </div>
          </div>

          {/* Right Column: Live Stream (33% Sticky) */}
          <div className="w-full lg:w-1/3 lg:sticky lg:top-6">
            <LiveFeedbackStream
              data={feedbackData}
              loading={feedbackLoading}
              selectedSource={selectedSource}
              setSelectedSource={setSelectedSource}
              selectedRecency={selectedRecency}
              setSelectedRecency={setSelectedRecency}
              sseConnected={sseConnected}
            />
          </div>
        </div>
      </div>

      {/* Premium Confirmation Modal overlay for reset */}
      {showResetConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 backdrop-blur-sm transition-all duration-300">
          <div className="bg-white rounded-xl shadow-xl border border-gray-100 max-w-md w-full mx-4 p-6 transform transition-all scale-100 animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-red-50 text-red-600 rounded-lg shrink-0">
                <RotateCcw size={24} className="animate-pulse" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-gray-900">Reset Demo Environment?</h3>
                <p className="text-xs text-gray-500 mt-2 leading-relaxed">
                  This action is **destructive**. It will delete all accumulated recommendation feedback interactions, reset AI weights to default parameters (α=0.40, β=0.25, γ=0.25, δ=0.10) and wipe out the weight training history log.
                </p>
                <div className="p-3 bg-gray-50 rounded-lg mt-3 text-[11px] text-gray-600 border border-gray-100">
                  <div className="flex justify-between font-mono">
                    <span>Feedback:</span> <span className="font-bold text-red-600">DELETE ALL</span>
                  </div>
                  <div className="flex justify-between font-mono mt-1">
                    <span>Weights:</span> <span className="font-bold">α=0.40 β=0.25 γ=0.25 δ=0.10</span>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                type="button"
                onClick={() => setShowResetConfirm(false)}
                disabled={resetLoading}
                className="px-4 py-2 border border-gray-300 rounded-lg text-xs font-semibold text-gray-700 hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleResetDemo}
                disabled={resetLoading}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all hover:shadow disabled:opacity-50 flex items-center gap-1.5"
              >
                {resetLoading ? 'Resetting...' : 'Confirm Reset'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
