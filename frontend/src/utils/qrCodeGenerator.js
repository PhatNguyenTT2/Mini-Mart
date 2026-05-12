import QRCode from 'qrcode';

/**
 * Generate QR code for a product's barcode
 * @param {string} barcode - Product barcode (EAN-13 or custom)
 * @param {object} options - QR code generation options
 * @returns {Promise<string>} Data URL of the QR code image
 */
export const generateProductQRCode = async (barcode, options = {}) => {
  try {
    const defaultOptions = {
      width: 300,
      margin: 2,
      color: {
        dark: '#000000',
        light: '#FFFFFF'
      },
      errorCorrectionLevel: 'M',
      ...options
    };

    const qrCodeDataUrl = await QRCode.toDataURL(barcode, defaultOptions);
    return qrCodeDataUrl;
  } catch (error) {
    console.error('QR Code generation error:', error);
    throw error;
  }
};

/**
 * Generate QR code as canvas element
 * @param {string} barcode - Product barcode
 * @param {HTMLCanvasElement} canvas - Canvas element to render QR code
 * @param {object} options - QR code generation options
 */
export const generateQRCodeToCanvas = async (barcode, canvas, options = {}) => {
  try {
    const defaultOptions = {
      width: 300,
      margin: 2,
      color: {
        dark: '#000000',
        light: '#FFFFFF'
      },
      errorCorrectionLevel: 'M',
      ...options
    };

    await QRCode.toCanvas(canvas, barcode, defaultOptions);
  } catch (error) {
    console.error('QR Code canvas generation error:', error);
    throw error;
  }
};

/**
 * Generate multiple QR codes for products
 * @param {Array} products - Array of product objects with barcode
 * @returns {Promise<Array>} Array of objects with product info and QR code data URL
 */
export const generateBulkQRCodes = async (products) => {
  try {
    const qrCodes = await Promise.all(
      products.map(async (product) => {
        const barcode = product.barcode || String(product._id || product.id);
        const qrCodeDataUrl = await generateProductQRCode(barcode);
        return {
          productId: product._id || product.id,
          barcode,
          productName: product.name,
          qrCode: qrCodeDataUrl
        };
      })
    );
    return qrCodes;
  } catch (error) {
    console.error('Bulk QR Code generation error:', error);
    throw error;
  }
};

/**
 * Download QR code as image file
 * @param {string} dataUrl - QR code data URL
 * @param {string} filename - Download filename
 */
export const downloadQRCode = (dataUrl, filename) => {
  const link = document.createElement('a');
  link.href = dataUrl;
  link.download = filename || 'qrcode.png';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

/**
 * Download multiple QR codes as ZIP (requires JSZip)
 * Note: This is a placeholder. For actual implementation, install jszip library
 */
export const downloadBulkQRCodes = async (qrCodes) => {
  qrCodes.forEach((qrCode, index) => {
    setTimeout(() => {
      downloadQRCode(qrCode.qrCode, `${qrCode.barcode}.png`);
    }, index * 100);
  });
};
