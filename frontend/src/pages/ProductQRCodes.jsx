import React, { useState, useEffect } from 'react';
import { Breadcrumb } from '../components/Breadcrumb';
import { Download, QrCode, Search, Loader } from 'lucide-react';
import productService from '../services/productService';
import { generateProductQRCode, downloadQRCode, generateBulkQRCodes } from '../utils/qrCodeGenerator';

export const ProductQRCodes = () => {
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [qrCodes, setQrCodes] = useState({});

  const breadcrumbItems = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Product QR Codes', href: '/product-qr-codes' }
  ];

  useEffect(() => {
    fetchProducts();
  }, []);

  useEffect(() => {
    if (searchTerm.trim()) {
      const filtered = products.filter(product =>
        (product.barcode || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        product.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredProducts(filtered);
    } else {
      setFilteredProducts(products);
    }
  }, [searchTerm, products]);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const response = await productService.getAllProducts({ isActive: true });
      const productsData = response.data?.products || [];
      setProducts(productsData);
      setFilteredProducts(productsData);
    } catch (error) {
      console.error('Error fetching products:', error);
    } finally {
      setLoading(false);
    }
  };

  const getBarcodeKey = (product) => product.barcode || String(product._id || product.id);

  const handleGenerateQRCode = async (product) => {
    try {
      const barcode = getBarcodeKey(product);
      const qrCodeDataUrl = await generateProductQRCode(barcode);
      setQrCodes(prev => ({
        ...prev,
        [barcode]: qrCodeDataUrl
      }));
    } catch (error) {
      console.error('Error generating QR code:', error);
      alert('Failed to generate QR code');
    }
  };

  const handleGenerateAll = async () => {
    try {
      setGenerating(true);
      const qrCodesData = await generateBulkQRCodes(filteredProducts);

      const qrCodesMap = {};
      qrCodesData.forEach(item => {
        qrCodesMap[item.barcode] = item.qrCode;
      });

      setQrCodes(qrCodesMap);
      alert(`Generated ${qrCodesData.length} QR codes successfully!`);
    } catch (error) {
      console.error('Error generating bulk QR codes:', error);
      alert('Failed to generate QR codes');
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = (barcode) => {
    const qrCode = qrCodes[barcode];
    if (qrCode) {
      downloadQRCode(qrCode, `${barcode}.png`);
    }
  };

  const handleDownloadAll = () => {
    Object.keys(qrCodes).forEach((barcode, index) => {
      setTimeout(() => {
        downloadQRCode(qrCodes[barcode], `${barcode}.png`);
      }, index * 100);
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Breadcrumb items={breadcrumbItems} />

      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Product QR Codes</h1>
            <p className="text-sm text-gray-500 mt-1">
              Generate and download QR codes for POS barcode scanning
            </p>
          </div>

          <div className="flex gap-3">
            <button
              onClick={handleGenerateAll}
              disabled={generating || filteredProducts.length === 0}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
            >
              {generating ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <QrCode className="w-5 h-5" />
                  Generate All QR Codes
                </>
              )}
            </button>

            {Object.keys(qrCodes).length > 0 && (
              <button
                onClick={handleDownloadAll}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2 transition-colors"
              >
                <Download className="w-5 h-5" />
                Download All ({Object.keys(qrCodes).length})
              </button>
            )}
          </div>
        </div>

        {/* Search Bar */}
        <div className="bg-white rounded-lg shadow-sm p-4">
          <div className="relative">
            <Search className="absolute left-3 top-3 text-gray-400" size={20} />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by barcode or product name..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredProducts.map((product) => {
            const barcode = getBarcodeKey(product);
            return (
              <div
                key={product._id || product.id}
                className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow"
              >
                {/* Product Info */}
                <div className="mb-4">
                  {product.image && (
                    <img
                      src={product.image}
                      alt={product.name}
                      className="w-full h-32 object-cover rounded-lg mb-3"
                    />
                  )}
                  <h3 className="font-semibold text-gray-900 text-sm mb-1 truncate">
                    {product.name}
                  </h3>
                  <p className="text-xs text-gray-500 font-mono">
                    {product.barcode || `ID: ${product.id}`}
                  </p>
                </div>

                {/* QR Code Display */}
                <div className="mb-4">
                  {qrCodes[barcode] ? (
                    <div className="bg-gray-50 rounded-lg p-4 flex items-center justify-center">
                      <img
                        src={qrCodes[barcode]}
                        alt={`QR Code for ${barcode}`}
                        className="w-40 h-40"
                      />
                    </div>
                  ) : (
                    <div className="bg-gray-100 rounded-lg p-4 flex items-center justify-center h-40">
                      <QrCode className="w-12 h-12 text-gray-400" />
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  {qrCodes[barcode] ? (
                    <button
                      onClick={() => handleDownload(barcode)}
                      className="flex-1 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center justify-center gap-2 text-sm transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      Download
                    </button>
                  ) : (
                    <button
                      onClick={() => handleGenerateQRCode(product)}
                      className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center justify-center gap-2 text-sm transition-colors"
                    >
                      <QrCode className="w-4 h-4" />
                      Generate
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Empty State */}
        {filteredProducts.length === 0 && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <QrCode className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              No products found
            </h3>
            <p className="text-gray-500">
              {searchTerm ? 'Try adjusting your search terms' : 'No active products available'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
