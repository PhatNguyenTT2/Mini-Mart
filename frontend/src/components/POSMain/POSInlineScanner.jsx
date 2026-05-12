import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Camera, X, AlertCircle, CheckCircle2, Upload, ScanLine, Trash2, Volume2, VolumeX } from 'lucide-react';

/**
 * POSInlineScanner — Inline camera scanner that replaces ProductGrid.
 * Supports continuous scanning with scan history log.
 * Cart remains visible alongside this component.
 */
export const POSInlineScanner = ({
  onScanSuccess,
  onClose,
  scanHistory = [],
  scanning: externalScanning = false
}) => {
  const [cameraActive, setCameraActive] = useState(false);
  const [cameras, setCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [initError, setInitError] = useState(null);
  const [lastScanFeedback, setLastScanFeedback] = useState(null);
  const [soundEnabled, setSoundEnabled] = useState(true);

  const html5QrCodeRef = useRef(null);
  const lastScanTimeRef = useRef(0);
  const lastBarcodeRef = useRef('');
  const isMountedRef = useRef(true);
  const scanHistoryEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Refs for latest callbacks
  const onScanSuccessRef = useRef(onScanSuccess);
  useEffect(() => { onScanSuccessRef.current = onScanSuccess; }, [onScanSuccess]);

  // Audio feedback refs
  const successAudioRef = useRef(null);
  const errorAudioRef = useRef(null);

  useEffect(() => {
    // Generate simple beep sounds using AudioContext
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

      // Success beep: short high-pitched tone
      const createBeep = (frequency, duration) => {
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.frequency.value = frequency;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.3;
        return { oscillator, gainNode, duration };
      };

      successAudioRef.current = () => {
        if (!soundEnabled) return;
        try {
          const ctx = new (window.AudioContext || window.webkitAudioContext)();
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.frequency.value = 1200;
          osc.type = 'sine';
          gain.gain.value = 0.15;
          osc.start();
          osc.stop(ctx.currentTime + 0.12);
        } catch (e) { /* audio not available */ }
      };

      errorAudioRef.current = () => {
        if (!soundEnabled) return;
        try {
          const ctx = new (window.AudioContext || window.webkitAudioContext)();
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.frequency.value = 300;
          osc.type = 'square';
          gain.gain.value = 0.12;
          osc.start();
          osc.stop(ctx.currentTime + 0.3);
        } catch (e) { /* audio not available */ }
      };
    } catch (e) {
      // AudioContext not supported
    }
  }, [soundEnabled]);

  // Auto-scroll scan history
  useEffect(() => {
    scanHistoryEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [scanHistory.length]);

  // Cleanup scanner
  const cleanupScanner = useCallback(async () => {
    try {
      const scanner = html5QrCodeRef.current;
      if (scanner) {
        if (scanner.isScanning) {
          await scanner.stop();
        }
        scanner.clear();
      }
    } catch (e) { /* ignore */ }
    finally {
      html5QrCodeRef.current = null;
      setCameraActive(false);
    }
  }, []);

  // Handle scan result — continuous mode with smart dual cooldown
  // Same barcode: 1500ms cooldown (prevent duplicate scans)
  // Different barcode: 500ms cooldown (fast multi-item scanning)
  const handleScanResult = useCallback(async (decodedText) => {
    const now = Date.now();
    const barcode = decodedText.trim();

    if (!barcode || barcode.length > 100) return;

    const isSameBarcode = barcode === lastBarcodeRef.current;
    const minInterval = isSameBarcode ? 1500 : 500;
    if (now - lastScanTimeRef.current < minInterval) return;

    lastScanTimeRef.current = now;
    lastBarcodeRef.current = barcode;

    setLastScanFeedback({ type: 'success', message: `Scanned: ${barcode}` });
    successAudioRef.current?.();

    try {
      await onScanSuccessRef.current?.(barcode);
    } catch (error) {
      setLastScanFeedback({ type: 'error', message: `Error: ${error.message || 'Failed'}` });
      errorAudioRef.current?.();
    }

    // Clear feedback after 1.2s — camera keeps running (continuous mode)
    setTimeout(() => {
      if (isMountedRef.current) setLastScanFeedback(null);
    }, 1200);
  }, []);

  // Start camera scanning
  const startScanning = useCallback(async (cameraId) => {
    if (!isMountedRef.current) return;

    try {
      await cleanupScanner();
      await new Promise(resolve => setTimeout(resolve, 100));

      const readerElement = document.getElementById('inline-qr-reader');
      if (!readerElement) return;

      const { Html5Qrcode, Html5QrcodeSupportedFormats } = await import('html5-qrcode');
      const scanner = new Html5Qrcode('inline-qr-reader');
      html5QrCodeRef.current = scanner;

      setCameraActive(true);
      setInitError(null);

      // Dynamic qrbox: 70% of viewfinder — large enough for both barcodes and QR codes
      const qrboxFunction = (viewfinderWidth, viewfinderHeight) => {
        const w = Math.floor(viewfinderWidth * 0.7);
        const h = Math.floor(viewfinderHeight * 0.5);
        return { width: w, height: h };
      };

      await scanner.start(
        cameraId,
        {
          fps: 15,
          qrbox: qrboxFunction,
          disableFlip: false,
          // Bug #2 fix: Prioritize barcode formats for supermarket use
          formatsToSupport: [
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8,
            Html5QrcodeSupportedFormats.UPC_A,
            Html5QrcodeSupportedFormats.CODE_128,
            Html5QrcodeSupportedFormats.QR_CODE,
          ]
        },
        (decodedText) => handleScanResult(decodedText),
        () => {}
      );

      // Bug #3 fix: Conditional camera constraints based on device capabilities
      try {
        const videoElement = readerElement.querySelector('video');
        if (videoElement && videoElement.srcObject) {
          const track = videoElement.srcObject.getVideoTracks()[0];
          if (track) {
            const capabilities = track.getCapabilities?.() || {};
            const constraints = {};

            if (capabilities.width) {
              constraints.width = { ideal: Math.min(1280, capabilities.width.max || 1280) };
            }
            if (capabilities.height) {
              constraints.height = { ideal: Math.min(720, capabilities.height.max || 720) };
            }
            if (capabilities.focusMode?.includes('continuous')) {
              constraints.focusMode = 'continuous';
            }

            if (Object.keys(constraints).length > 0) {
              await track.applyConstraints(constraints);
            }
          }
        }
      } catch (constraintErr) {
        console.log('Camera constraint upgrade skipped:', constraintErr.message);
      }
    } catch (error) {
      console.error('Inline scanner start error:', error);
      setCameraActive(false);
      setInitError(error.message || 'Failed to start camera');
    }
  }, [cleanupScanner, handleScanResult]);

  // Init camera on mount
  useEffect(() => {
    isMountedRef.current = true;
    let isCancelled = false;

    const init = async () => {
      try {
        const { Html5Qrcode } = await import('html5-qrcode');
        const devices = await Html5Qrcode.getCameras();

        if (isCancelled) return;

        if (!devices || devices.length === 0) {
          setInitError('No cameras found.');
          return;
        }

        setCameras(devices);
        const backCam = devices.find(d =>
          d.label.toLowerCase().includes('back') ||
          d.label.toLowerCase().includes('rear')
        ) || devices[0];

        setSelectedCamera(backCam.id);
        await new Promise(resolve => setTimeout(resolve, 300));

        if (isCancelled) return;
        await startScanning(backCam.id);
      } catch (error) {
        if (!isCancelled) {
          console.error('Camera init error:', error);
          setInitError('Camera access denied. Check permissions.');
        }
      }
    };

    init();

    return () => {
      isCancelled = true;
      isMountedRef.current = false;
      cleanupScanner();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCameraChange = async (cameraId) => {
    setSelectedCamera(cameraId);
    await startScanning(cameraId);
  };

  // Bug #8 fix: Safe cleanup for file scanner with try/finally
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    let tempScanner = null;
    try {
      const { Html5Qrcode } = await import('html5-qrcode');
      tempScanner = new Html5Qrcode('inline-qr-file');
      const decodedText = await tempScanner.scanFile(file, true);
      handleScanResult(decodedText);
    } catch (error) {
      setLastScanFeedback({ type: 'error', message: 'Could not read barcode from image' });
      errorAudioRef.current?.();
      setTimeout(() => setLastScanFeedback(null), 2000);
    } finally {
      try { tempScanner?.clear(); } catch (_) { /* cleanup best-effort */ }
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const formatTime = (timestamp) => {
    const d = new Date(timestamp);
    return d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const formatVND = (amount) => {
    if (!amount) return '';
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  return (
    <div className="flex flex-col h-full animate-fade-in-smooth">
      {/* Scanner Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-900 rounded-t-lg">
        <div className="flex items-center gap-2">
          <ScanLine className="w-5 h-5 text-emerald-400" />
          <h3 className="text-base font-semibold text-white">Continuous Scanner</h3>
          {cameraActive && (
            <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded-full text-xs font-medium">
              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
              LIVE
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Sound toggle */}
          <button
            onClick={() => setSoundEnabled(!soundEnabled)}
            className="p-1.5 text-gray-400 hover:text-white rounded transition-colors"
            title={soundEnabled ? 'Mute sounds' : 'Enable sounds'}
          >
            {soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          </button>

          {/* Upload button */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="p-1.5 text-gray-400 hover:text-white rounded transition-colors"
            title="Upload barcode image"
          >
            <Upload size={16} />
          </button>

          {/* Close */}
          <button
            onClick={() => { cleanupScanner(); onClose(); }}
            className="p-1.5 text-gray-400 hover:text-red-400 rounded transition-colors"
            title="Stop scanning (ESC)"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Camera Feed Section */}
      <div className="relative bg-gray-950" style={{ minHeight: '300px', maxHeight: '50vh' }}>
        {/* CSS override: hide html5-qrcode's default ugly overlay, use clean border instead */}
        <style>{`
          #inline-qr-reader video {
            object-fit: cover !important;
          }
          #inline-qr-reader {
            border: none !important;
          }
          /* Hide the built-in shaded region, keep scan box visible */
          #inline-qr-reader > div:nth-child(2) {
            border: none !important;
          }
          /* Style the qrbox scan region border */
          #inline-qr-reader img[alt="Info icon"] {
            display: none !important;
          }
          #inline-qr-reader > div > div {
            border: none !important;
          }
        `}</style>
        <div id="inline-qr-reader" style={{ width: '100%' }} />
        <div id="inline-qr-file" className="hidden" />

        {initError && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-950/90">
            <div className="text-center px-6">
              <AlertCircle size={40} className="text-red-400 mx-auto mb-2" />
              <p className="text-white font-medium text-sm mb-1">Camera Error</p>
              <p className="text-gray-400 text-xs mb-3">{initError}</p>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-xs hover:bg-emerald-700"
              >
                Upload Image Instead
              </button>
            </div>
          </div>
        )}

        {/* Scanning guide text overlay */}
        {cameraActive && !lastScanFeedback && !initError && (
          <div className="absolute bottom-3 left-0 right-0 flex justify-center pointer-events-none">
            <span className="px-3 py-1.5 bg-black/60 text-white text-xs rounded-full backdrop-blur-sm">
              Đưa mã vạch / QR vào vùng quét
            </span>
          </div>
        )}

        {/* Scan flash feedback */}
        {lastScanFeedback && (
          <div className={`absolute inset-0 flex items-center justify-center z-10 pointer-events-none ${
            lastScanFeedback.type === 'success'
              ? 'bg-emerald-500/20 animate-pulse'
              : 'bg-red-500/20 animate-pulse'
          }`}>
            <div className={`px-4 py-2 rounded-lg flex items-center gap-2 text-sm font-semibold ${
              lastScanFeedback.type === 'success'
                ? 'bg-emerald-500 text-white'
                : 'bg-red-500 text-white'
            }`}>
              {lastScanFeedback.type === 'success'
                ? <CheckCircle2 size={18} />
                : <AlertCircle size={18} />
              }
              {lastScanFeedback.message}
            </div>
          </div>
        )}

        {/* Processing indicator */}
        {externalScanning && (
          <div className="absolute top-2 right-2 px-2 py-1 bg-blue-600/80 text-white rounded text-xs font-medium flex items-center gap-1">
            <svg className="animate-spin w-3 h-3" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" opacity="0.25" />
              <path d="M8 2 A6 6 0 0 1 14 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Processing...
          </div>
        )}
      </div>

      {/* Camera selector */}
      {cameras.length > 1 && (
        <div className="flex items-center gap-2 px-3 py-2 bg-gray-800 border-t border-gray-700">
          <Camera size={14} className="text-gray-400" />
          <select
            value={selectedCamera || ''}
            onChange={(e) => handleCameraChange(e.target.value)}
            className="flex-1 px-2 py-1 bg-gray-700 text-white text-xs rounded border border-gray-600 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            {cameras.map((cam) => (
              <option key={cam.id} value={cam.id}>
                {cam.label || `Camera ${cam.id}`}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Scan History Log */}
      <div className="flex-1 overflow-hidden flex flex-col bg-white border-t border-gray-200 rounded-b-lg">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
          <h4 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            Scan History
            {scanHistory.length > 0 && (
              <span className="px-1.5 py-0.5 bg-gray-200 text-gray-600 rounded-full text-xs font-medium">
                {scanHistory.length}
              </span>
            )}
          </h4>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-2">
          {scanHistory.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 py-8">
              <ScanLine size={32} className="mb-2 opacity-50" />
              <p className="text-sm">Point camera at barcode to start</p>
              <p className="text-xs mt-1">Items will appear here after scanning</p>
            </div>
          ) : (
            <div className="space-y-1.5">
              {scanHistory.map((entry, index) => (
                <div
                  key={entry.id || index}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                    entry.success
                      ? 'bg-emerald-50 border border-emerald-100'
                      : 'bg-red-50 border border-red-100'
                  } ${index === scanHistory.length - 1 ? 'ring-2 ring-emerald-300/50 animate-fade-in-smooth' : ''}`}
                >
                  {entry.success ? (
                    <CheckCircle2 size={16} className="text-emerald-500 flex-shrink-0" />
                  ) : (
                    <AlertCircle size={16} className="text-red-500 flex-shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className={`font-medium truncate ${entry.success ? 'text-gray-900' : 'text-red-700'}`}>
                      {entry.productName || entry.code}
                    </p>
                    {entry.success && entry.price && (
                      <p className="text-xs text-gray-500">
                        x{entry.quantity || 1} · {formatVND(entry.price)}
                      </p>
                    )}
                    {!entry.success && entry.error && (
                      <p className="text-xs text-red-500">{entry.error}</p>
                    )}
                  </div>
                  <span className="text-[10px] text-gray-400 flex-shrink-0">
                    {formatTime(entry.timestamp)}
                  </span>
                </div>
              ))}
              <div ref={scanHistoryEndRef} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
