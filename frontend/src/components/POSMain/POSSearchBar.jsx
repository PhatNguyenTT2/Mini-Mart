import React, { useState, useEffect, useRef, useCallback } from 'react';
import { QrCode, Map, StopCircle, History } from 'lucide-react';

export const POSSearchBar = ({ onProductScanned, onSearchChange, searchTerm, scanning, onOpenQRScanner, onMapClick, onHistoryClick, onHelpClick, scannerActive }) => {
  const [scanStatus, setScanStatus] = useState(null); // 'success' | 'error' | null
  const [isBuffering, setIsBuffering] = useState(false);

  // Bug #4 fix: Ref-based approach — eliminates stale closures and re-subscription overhead
  const scanBufferRef = useRef('');
  const lastKeyTimeRef = useRef(0);
  const scanTimeoutRef = useRef(null);
  const statusTimeoutRef = useRef(null);
  const inputRef = useRef(null);
  const onProductScannedRef = useRef(onProductScanned);
  useEffect(() => { onProductScannedRef.current = onProductScanned; }, [onProductScanned]);

  const showScanSuccess = useCallback(() => {
    setScanStatus('success');
    if (statusTimeoutRef.current) clearTimeout(statusTimeoutRef.current);
    statusTimeoutRef.current = setTimeout(() => setScanStatus(null), 2000);
  }, []);

  // Stable keypress listener — registers once, never re-subscribes
  useEffect(() => {
    const handleKeyPress = (e) => {
      // Ignore if user is typing in other inputs
      if (e.target.tagName === 'INPUT' && e.target !== inputRef.current) {
        return;
      }

      // Ignore non-printable / modifier keys
      if (e.key.length !== 1) return;

      const now = Date.now();
      const timeDiff = now - lastKeyTimeRef.current;

      // Reset buffer after 500ms idle (new scan or manual typing)
      if (timeDiff > 500) {
        scanBufferRef.current = '';
      }

      scanBufferRef.current += e.key;
      lastKeyTimeRef.current = now;
      setIsBuffering(true);

      // Auto-submit after 150ms of no input (scanner finished sending all chars)
      if (scanTimeoutRef.current) {
        clearTimeout(scanTimeoutRef.current);
      }

      scanTimeoutRef.current = setTimeout(() => {
        const buffer = scanBufferRef.current;
        setIsBuffering(false);

        // Match barcode patterns: 8-14 digits (EAN-8, EAN-13, UPC-A, internal codes)
        if (/^\d{8,14}$/.test(buffer)) {
          console.log('Barcode scanned:', buffer);
          onProductScannedRef.current?.(buffer);
          showScanSuccess();

          // Clear buffer and input field
          if (inputRef.current) inputRef.current.value = '';
        }

        scanBufferRef.current = '';
      }, 150);
    };

    const handleKeyDown = (e) => {
      // Handle Enter key for manual barcode input in search field
      if (e.key === 'Enter' && e.target === inputRef.current) {
        const value = e.target.value.trim();

        // If input looks like a barcode (8-14 digits)
        if (/^\d{8,14}$/.test(value)) {
          e.preventDefault();
          onProductScannedRef.current?.(value);
          showScanSuccess();

          e.target.value = '';
          scanBufferRef.current = '';
        }
      }
    };

    window.addEventListener('keypress', handleKeyPress);
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      window.removeEventListener('keypress', handleKeyPress);
      window.removeEventListener('keydown', handleKeyDown);
      if (scanTimeoutRef.current) clearTimeout(scanTimeoutRef.current);
      if (statusTimeoutRef.current) clearTimeout(statusTimeoutRef.current);
    };
  }, [showScanSuccess]); // showScanSuccess is stable via useCallback

  // Manual search change
  const handleInputChange = (e) => {
    const value = e.target.value;
    scanBufferRef.current = '';

    if (onSearchChange) {
      onSearchChange(value);
    }
  };

  return (
    <div className="relative">
      <div className="flex gap-2 mb-3">
        {/* Search Input */}
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            id="product-search"
            type="text"
            defaultValue={searchTerm}
            onChange={handleInputChange}
            placeholder="Scan barcode or search products... (Ctrl+K or F2)"
            className="w-full px-4 py-3 pl-10 border-2 border-gray-300 rounded-lg text-[15px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
          />
          <svg
            className="absolute left-3 top-3.5 text-gray-400"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2" />
            <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>

          {/* Scanning/Processing indicator */}
          {(isBuffering || scanning) && (
            <div className="absolute right-3 top-3 flex items-center gap-2 px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-semibold animate-pulse">
              <svg className="animate-spin" width="14" height="14" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.25" />
                <path d="M8 2 A6 6 0 0 1 14 8" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" />
              </svg>
              {isBuffering ? 'Scanning...' : 'Processing...'}
            </div>
          )}
        </div>

        {/* QR Scanner Toggle Button */}
        <button
          onClick={onOpenQRScanner}
          className={`px-4 py-3 text-white rounded-lg transition-all flex items-center gap-2 font-medium shadow-sm ${scannerActive
            ? 'bg-red-500 hover:bg-red-600 ring-2 ring-red-300'
            : 'bg-emerald-600 hover:bg-emerald-700'
            }`}
          title={scannerActive ? 'Stop Scanning (F2)' : 'Scan QR Code (F2)'}
        >
          {scannerActive ? (
            <>
              <StopCircle size={20} />
              <span className="hidden sm:inline">Stop Scan</span>
            </>
          ) : (
            <>
              <QrCode size={20} />
              <span className="hidden sm:inline">Scan QR</span>
            </>
          )}
        </button>

        {/* Store Map Button */}
        {onMapClick && (
          <button
            onClick={onMapClick}
            className="px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2 font-medium shadow-sm"
            title="Open Store Map"
          >
            <Map size={20} />
            <span className="hidden sm:inline">Map</span>
          </button>
        )}

        {/* Order History Button */}
        {onHistoryClick && (
          <button
            onClick={onHistoryClick}
            className="px-4 py-3 bg-violet-600 hover:bg-violet-700 text-white rounded-lg transition-colors flex items-center gap-2 font-medium shadow-sm"
            title="My Order History (F5)"
          >
            <History size={20} />
            <span className="hidden sm:inline">History</span>
          </button>
        )}

        {/* Keyboard Shortcuts Help Button */}
        {onHelpClick && (
          <button
            onClick={onHelpClick}
            className="px-4 py-3 bg-gray-250 bg-gray-200 text-gray-700 rounded-lg transition-colors flex items-center justify-center font-bold shadow-sm"
            title="Keyboard Shortcuts Guide"
          >
            <span className="text-lg leading-none font-semibold">?</span>
          </button>
        )}
      </div>
    </div>
  );
};


