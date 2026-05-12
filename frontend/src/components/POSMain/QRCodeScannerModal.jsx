import React, { useEffect, useRef, useState, useCallback } from 'react';
import { X, Camera, AlertCircle, CheckCircle2, Upload, ScanLine } from 'lucide-react';

/**
 * QR Code / Barcode Scanner Modal
 * Uses html5-qrcode with webcam to scan QR codes and barcodes.
 *
 * Architecture: Uses refs for callbacks to avoid useEffect dependency hell.
 * The scan callback is stored in a ref so the camera scanner.start() closure
 * always calls the latest version without triggering re-renders.
 */
export const QRCodeScannerModal = ({ isOpen, onClose, onScanSuccess, onScanError }) => {
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [cameras, setCameras] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [isFileMode, setIsFileMode] = useState(false);
  const [initError, setInitError] = useState(null);

  const html5QrCodeRef = useRef(null);
  const fileInputRef = useRef(null);
  const lastScanTimeRef = useRef(0);
  const isMountedRef = useRef(false);

  // Store latest callbacks in refs to avoid dependency chains
  const onScanSuccessRef = useRef(onScanSuccess);
  const onCloseRef = useRef(onClose);
  useEffect(() => { onScanSuccessRef.current = onScanSuccess; }, [onScanSuccess]);
  useEffect(() => { onCloseRef.current = onClose; }, [onClose]);

  // ========== CLEANUP (stable, no deps) ==========
  const cleanupScanner = useCallback(async () => {
    try {
      const scanner = html5QrCodeRef.current;
      if (scanner) {
        if (scanner.isScanning) {
          await scanner.stop();
        }
        scanner.clear();
      }
    } catch (e) {
      // Ignore cleanup errors
    } finally {
      html5QrCodeRef.current = null;
      setScanning(false);
    }
  }, []);

  // ========== CLOSE (uses ref, stable) ==========
  const handleClose = useCallback(() => {
    cleanupScanner();
    setScanResult(null);
    setInitError(null);
    setIsFileMode(false);
    lastScanTimeRef.current = 0;
    onCloseRef.current?.();
  }, [cleanupScanner]);

  // ========== SCAN RESULT HANDLER (uses refs, stable) ==========
  const handleScanResult = useCallback(async (decodedText) => {
    const now = Date.now();
    if (now - lastScanTimeRef.current < 2000) return;
    lastScanTimeRef.current = now;

    const barcode = decodedText.trim();
    console.log('Scanned barcode:', barcode);

    // Accept numeric codes: EAN-13 (13 digits), EAN-8 (8 digits), or product ID (1+ digits)
    const isValid = /^\d{1,13}$/.test(barcode);

    if (!isValid) {
      setScanResult({ type: 'error', message: `Invalid format: "${barcode}"` });
      setTimeout(() => setScanResult(null), 2000);
      return;
    }

    setScanResult({ type: 'success', message: `Scanned: ${barcode}` });

    try {
      // Await the scan handler to complete API calls before closing
      await onScanSuccessRef.current?.(barcode);

      if (isMountedRef.current) {
        handleClose();
      }
    } catch (error) {
      console.error('Scan processing error:', error);
      setScanResult({ type: 'error', message: `Error processing: ${barcode}` });
      setTimeout(() => {
        if (isMountedRef.current) {
          setScanResult(null);
        }
      }, 2000);
    }
  }, [handleClose]);

  // ========== START SCANNING (stable — all deps are stable) ==========
  const startScanning = useCallback(async (cameraId) => {
    if (!isMountedRef.current) return;

    try {
      await cleanupScanner();
      await new Promise(resolve => setTimeout(resolve, 100));

      const readerElement = document.getElementById('qr-reader');
      if (!readerElement) return;

      const { Html5Qrcode, Html5QrcodeSupportedFormats } = await import('html5-qrcode');
      const scanner = new Html5Qrcode('qr-reader');
      html5QrCodeRef.current = scanner;

      setScanning(true);
      setInitError(null);

      await scanner.start(
        cameraId,
        {
          fps: 15,
          qrbox: { width: 250, height: 250 },
          aspectRatio: 1.0,
          formatsToSupport: [
            Html5QrcodeSupportedFormats.QR_CODE,
            Html5QrcodeSupportedFormats.EAN_13,
            Html5QrcodeSupportedFormats.EAN_8,
            Html5QrcodeSupportedFormats.CODE_128,
            Html5QrcodeSupportedFormats.CODE_39,
            Html5QrcodeSupportedFormats.UPC_A,
            Html5QrcodeSupportedFormats.UPC_E,
          ]
        },
        (decodedText) => {
          handleScanResult(decodedText);
        },
        () => {}
      );
    } catch (error) {
      console.error('Scanner start error:', error);
      setScanning(false);
      setInitError(error.message || 'Failed to start camera');
    }
  }, [cleanupScanner, handleScanResult]);

  // ========== INIT EFFECT — deps: [isOpen] only ==========
  useEffect(() => {
    if (!isOpen) return;

    let isCancelled = false;
    isMountedRef.current = true;
    setScanResult(null);
    setInitError(null);
    setIsFileMode(false);

    const init = async () => {
      try {
        const { Html5Qrcode } = await import('html5-qrcode');
        const devices = await Html5Qrcode.getCameras();

        if (isCancelled) return;

        if (!devices || devices.length === 0) {
          setInitError('No cameras found. Try uploading an image instead.');
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
          setInitError('Camera access denied. Check permissions or try image upload.');
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
  }, [isOpen]);

  // ========== EVENT HANDLERS ==========

  const handleCameraChange = async (cameraId) => {
    setSelectedCamera(cameraId);
    await startScanning(cameraId);
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const { Html5Qrcode } = await import('html5-qrcode');
      const tempScanner = new Html5Qrcode('qr-reader-file');
      const decodedText = await tempScanner.scanFile(file, true);
      tempScanner.clear();
      handleScanResult(decodedText);
    } catch (error) {
      console.error('File scan error:', error);
      setScanResult({ type: 'error', message: 'Could not read barcode from image' });
      setTimeout(() => setScanResult(null), 2500);
    }

    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const toggleMode = async () => {
    if (isFileMode) {
      setIsFileMode(false);
      if (selectedCamera) {
        await startScanning(selectedCamera);
      }
    } else {
      await cleanupScanner();
      setIsFileMode(true);
    }
  };

  // ========== RENDER ==========

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center">
      <div className="absolute inset-0 bg-black bg-opacity-60" onClick={handleClose} />

      <div className="relative w-full max-w-lg flex flex-col bg-gray-900 rounded-xl shadow-2xl overflow-hidden" style={{ height: '600px' }}>
        {/* Header */}
        <div className="flex items-center justify-between p-3 bg-gray-900 border-b border-gray-800">
          <div>
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <ScanLine className="w-5 h-5 text-emerald-400" />
              Scan Barcode / QR
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              {isFileMode ? 'Upload an image with QR/barcode' : 'Point camera at barcode'}
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Camera / Upload */}
        <div className="flex-1 relative bg-black flex items-center justify-center overflow-hidden">
          {isFileMode ? (
            <div className="flex flex-col items-center justify-center gap-5 text-white px-8">
              <Upload size={56} className="text-emerald-400" />
              <h3 className="text-xl font-semibold">Upload Barcode Image</h3>
              <p className="text-gray-400 text-center text-sm">
                Select a photo of a barcode or QR code to scan
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileUpload}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-semibold flex items-center gap-2"
              >
                <Upload size={18} />
                Choose Image
              </button>
              <div id="qr-reader-file" className="hidden"></div>
            </div>
          ) : (
            <>
              <div id="qr-reader" className="w-full h-full"></div>

              {initError && (
                <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-80">
                  <div className="text-center px-8">
                    <AlertCircle size={48} className="text-red-400 mx-auto mb-3" />
                    <p className="text-white font-medium mb-1">Camera Error</p>
                    <p className="text-gray-400 text-sm mb-4">{initError}</p>
                    <button
                      onClick={toggleMode}
                      className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 text-sm"
                    >
                      Upload Image Instead
                    </button>
                  </div>
                </div>
              )}

              {scanning && !scanResult && !initError && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="relative">
                    <div className="w-56 h-56 border-4 border-emerald-500/60 rounded-lg">
                      <div className="absolute -top-1 -left-1 w-8 h-8 border-t-4 border-l-4 border-emerald-400 rounded-tl"></div>
                      <div className="absolute -top-1 -right-1 w-8 h-8 border-t-4 border-r-4 border-emerald-400 rounded-tr"></div>
                      <div className="absolute -bottom-1 -left-1 w-8 h-8 border-b-4 border-l-4 border-emerald-400 rounded-bl"></div>
                      <div className="absolute -bottom-1 -right-1 w-8 h-8 border-b-4 border-r-4 border-emerald-400 rounded-br"></div>
                    </div>
                    <div className="absolute top-0 left-2 right-2 h-0.5 bg-emerald-400 animate-scan rounded"></div>
                  </div>
                </div>
              )}
            </>
          )}

          {scanResult && (
            <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-60 z-10">
              <div className={`px-6 py-4 rounded-xl shadow-2xl flex items-center gap-3 ${
                scanResult.type === 'success'
                  ? 'bg-emerald-500 text-white'
                  : 'bg-red-500 text-white'
              }`}>
                {scanResult.type === 'success' ? (
                  <CheckCircle2 size={24} />
                ) : (
                  <AlertCircle size={24} />
                )}
                <span className="text-base font-semibold">{scanResult.message}</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-gray-900 border-t border-gray-800 flex items-center justify-between gap-3">
          {!isFileMode && cameras.length > 1 && (
            <div className="flex items-center gap-2">
              <Camera size={18} className="text-gray-400" />
              <select
                value={selectedCamera || ''}
                onChange={(e) => handleCameraChange(e.target.value)}
                className="px-2 py-1.5 bg-gray-800 text-white text-sm rounded-lg border border-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              >
                {cameras.map((cam) => (
                  <option key={cam.id} value={cam.id}>
                    {cam.label || `Camera ${cam.id}`}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="flex-1" />

          <button
            onClick={toggleMode}
            className="px-3 py-1.5 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2 text-sm border border-gray-700"
          >
            {isFileMode ? (
              <><Camera size={16} /> Camera</>
            ) : (
              <><Upload size={16} /> Upload</>
            )}
          </button>

          <button
            onClick={handleClose}
            className="px-3 py-1.5 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm border border-gray-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
