import { useState, useCallback } from 'react';
import posDataService from '../services/posDataService';

/**
 * POS Scanner Hook.
 * Handles QR/barcode scanning, batch selection modal, and store map batch selection.
 */
export function usePOSScanner({ addToCart, addProductWithBatch, showToast }) {
  const [scanning, setScanning] = useState(false);
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [selectedProductData, setSelectedProductData] = useState(null);
  const [showQRScanner, setShowQRScanner] = useState(false);
  const [scanHistory, setScanHistory] = useState([]);

  // Add entry to scan history log
  const addScanEntry = useCallback((entry) => {
    setScanHistory(prev => [...prev, {
      id: Date.now() + Math.random(),
      timestamp: Date.now(),
      ...entry
    }]);
  }, []);

  const clearScanHistory = useCallback(() => {
    setScanHistory([]);
  }, []);

  // Fetch batches for a product by ID
  const fetchAndShowBatches = useCallback(async (productId) => {
    setScanning(true);
    try {
      const [productResponse, batchResponse] = await Promise.all([
        posDataService.getProductById(productId),
        posDataService.getProductBatches(productId)
      ]);

      if (!productResponse.success) {
        showToast('error', 'Failed to load product.');
        return null;
      }

      const product = productResponse.data?.product;
      const batches = batchResponse.data?.batches || batchResponse.data || [];

      if (!batches || batches.length === 0) {
        showToast('error', `${product.name} is currently out of stock!`);
        return null;
      }

      const availableBatches = batches.filter(batch => {
        const qty = batch.totalOnShelf || batch.detailInventory?.quantityOnShelf || batch.quantityOnShelf || batch.quantity || 0;
        return qty > 0;
      });

      console.log('Total batches:', batches.length, '-> Available on shelf:', availableBatches.length);

      if (availableBatches.length === 0) {
        showToast('error', `${product.name} has no batches available on shelf!`);
        return null;
      }

      const productData = { product, inventory: null, batches: availableBatches };
      setSelectedProductData(productData);
      setShowBatchModal(true);
      return productData;
    } catch (error) {
      console.error('Error loading batches:', error);
      showToast('error', 'Failed to load product batches.');
      return null;
    } finally {
      setScanning(false);
    }
  }, [showToast]);

  // Handle product click (from grid)
  const handleProductClick = useCallback(async (product) => {
    const result = await addToCart(product);

    if (result?.needsBatchSelection) {
      const productId = product._id || product.id;
      await fetchAndShowBatches(productId);
    }
  }, [addToCart, fetchAndShowBatches]);

  // Handle barcode scanned (barcode scanner / QR)
  // Dual-lookup: try barcode first, fallback to productId for legacy QR codes
  const handleProductScanned = useCallback(async (scannedData) => {
    setScanning(true);
    try {
      let response;
      let product = null;

      // 1. Try lookup by barcode (EAN-13)
      try {
        response = await posDataService.getProductByBarcode(scannedData);
        if (response.success && response.data?.product) {
          product = response.data.product;
        }
      } catch (barcodeErr) {
        // Barcode lookup failed (404), will try fallback
        console.log(`Barcode lookup failed for "${scannedData}", trying ID fallback...`);
      }

      // 2. Fallback: try as product ID (numeric or MongoDB ObjectId)
      if (!product) {
        const isNumericId = /^\d+$/.test(scannedData);
        const isObjectId = /^[a-f0-9]{24}$/i.test(scannedData);

        if (isNumericId || isObjectId) {
          try {
            response = await posDataService.getProductById(scannedData);
            if (response.success && response.data?.product) {
              product = response.data.product;
            }
          } catch (idErr) {
            console.log(`Product ID lookup also failed for "${scannedData}"`);
          }
        }
      }

      if (!product) {
        showToast('error', `Product not found for code: ${scannedData}`);
        addScanEntry({ code: scannedData, success: false, error: 'Product not found' });
        return;
      }

      const productId = product.id;

      // Fetch batches
      const batchResponse = await posDataService.getProductBatches(productId);
      const batches = batchResponse.data?.batches || batchResponse.data || [];

      if (!batches || batches.length === 0) {
        showToast('error', `${product.name} is currently out of stock!`);
        addScanEntry({ code: scannedData, success: false, productName: product.name, error: 'Out of stock' });
        return;
      }

      const isFresh = product.isPerishable || false;

      if (isFresh) {
        const availableBatches = batches.filter(batch => {
          const qty = batch.totalOnShelf || batch.detailInventory?.quantityOnShelf || batch.quantityOnShelf || batch.quantity || 0;
          return qty > 0;
        });

        if (availableBatches.length === 0) {
          showToast('error', `${product.name} has no batches available on shelf!`);
          addScanEntry({ code: scannedData, success: false, productName: product.name, error: 'No batches on shelf' });
          return;
        }

        setSelectedProductData({ product, inventory: null, batches: availableBatches });
        setShowBatchModal(true);
        addScanEntry({
          code: scannedData,
          success: true,
          productName: product.name + ' (select batch)',
          price: product.unitPrice,
          quantity: 1
        });
      } else {
        // REGULAR PRODUCT: Add directly via FEFO
        const inventory = batches.reduce((acc, b) => {
          acc.quantityOnShelf += b.totalOnShelf || b.detailInventory?.quantityOnShelf || b.quantityOnShelf || 0;
          acc.quantityAvailable += b.quantity || b.totalOnHand || 0;
          return acc;
        }, { quantityOnShelf: 0, quantityAvailable: 0 });

        if (inventory.quantityOnShelf <= 0) {
          showToast('error', `${product.name} is not available on shelf!`);
          addScanEntry({ code: scannedData, success: false, productName: product.name, error: 'Not available on shelf' });
          return;
        }

        const basePrice = product.unitPrice || 0;
        const discountPercentage = product.discountPercentage || 0;
        const finalPrice = discountPercentage > 0
          ? basePrice * (1 - discountPercentage / 100)
          : basePrice;

        await addToCart({
          ...product,
          id: productId,
          _id: productId,
          price: finalPrice,
          stock: inventory.quantityAvailable,
          categoryName: product.category?.name || product.categoryName || 'Uncategorized',
          inventory,
          basePrice,
          discountPercentage
        });
        addScanEntry({
          code: scannedData,
          success: true,
          productName: product.name,
          price: finalPrice,
          quantity: 1
        });
      }
    } catch (error) {
      console.error('Error scanning product:', error);
      if (error.response?.status === 404) {
        showToast('error', `Product not found for code: ${scannedData}`);
      } else {
        showToast('error', 'Failed to scan product. Please try again.');
      }
    } finally {
      setScanning(false);
    }
  }, [addToCart, addScanEntry, showToast]);

  // Handle QR scan success - returns promise so modal can await completion
  const handleQRScanSuccess = useCallback(async (productCode) => {
    await handleProductScanned(productCode);
  }, [handleProductScanned]);

  // Handle QR scan error
  const handleQRScanError = useCallback((error) => {
    console.error('QR Scan error:', error);
    showToast('error', error);
  }, [showToast]);

  // Handle batch selected from modal
  const handleBatchSelected = useCallback((selectedBatch, quantity) => {
    addProductWithBatch(selectedProductData, selectedBatch, quantity);
    setShowBatchModal(false);
    setSelectedProductData(null);
  }, [selectedProductData, addProductWithBatch]);

  // Handle product selection from Store Map
  const handleMapBatchSelect = useCallback(async (productInfo) => {
    // productInfo: { productId, productName, totalOnShelf, unitPrice }
    const productId = productInfo.productId;
    if (!productId) {
      showToast('error', 'Invalid product data on map');
      return;
    }

    try {
      const [productResponse, batchResponse] = await Promise.all([
        posDataService.getProductById(productId),
        posDataService.getProductBatches(productId)
      ]);

      if (!productResponse.success) {
        showToast('error', 'Failed to load product details');
        return;
      }

      const product = productResponse.data?.product;
      const batches = batchResponse.data?.batches || batchResponse.data || [];

      const availableBatches = batches.filter(b => {
        const qty = b.totalOnShelf || b.quantityOnShelf || b.quantity || 0;
        return qty > 0;
      });

      if (availableBatches.length === 0) {
        showToast('error', `${product.name} has no available batches on shelf`);
        return;
      }

      const isFresh = product.isPerishable || false;

      if (isFresh || availableBatches.length > 1) {
        // Open batch selection modal
        setSelectedProductData({ product, inventory: null, batches: availableBatches });
        setShowBatchModal(true);
      } else {
        // Single batch → add directly
        const batch = availableBatches[0];
        addProductWithBatch({ product, inventory: null, batches: availableBatches }, batch, 1);
      }
    } catch (err) {
      console.error('Error adding from map:', err);
      showToast('error', 'Failed to add item from map');
    }
  }, [addProductWithBatch, showToast]);

  return {
    scanning,
    showBatchModal,
    setShowBatchModal,
    selectedProductData,
    setSelectedProductData,
    showQRScanner,
    setShowQRScanner,
    scanHistory,
    clearScanHistory,
    handleProductClick,
    handleProductScanned,
    handleQRScanSuccess,
    handleQRScanError,
    handleBatchSelected,
    handleMapBatchSelect
  };
}
