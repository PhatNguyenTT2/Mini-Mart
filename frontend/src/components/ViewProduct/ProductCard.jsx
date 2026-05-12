import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * ProductCard Component
 * Hiển thị thông tin sản phẩm dạng card
 * Chỉ sử dụng các field có trong Product model:
 * - productCode, name, image, category, unitPrice, vendor, isActive
 * 
 * Props:
 * - product: Product object
 * - onAddToCart: Callback function when adding to cart (optional)
 * - onClick: Callback function when clicking card (optional)
 */
export const ProductCard = ({ product, onAddToCart, onClick }) => {
  const [isHovered, setIsHovered] = useState(false);
  const navigate = useNavigate();

  // Helper function to format VND currency
  const formatVND = (amount) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount);
  };

  // Safe access với fallback
  const productId = product.id || product._id;
  const categoryName = product.category?.name || product.categoryName || 'Uncategorized';
  const onShelfQuantity = product.inventory?.quantityOnShelf || 0;
  const imageUrl = product.image || null;

  // Get discount percentage from backend (calculated via FEFO virtual property)
  const basePrice = product.unitPrice || 0;
  const discountPercentage = product.discountPercentage || 0;
  const hasDiscount = discountPercentage > 0;
  const finalPrice = hasDiscount ? basePrice * (1 - discountPercentage / 100) : basePrice;

  const handleClick = () => {
    // If onClick prop is provided, use it (for POS mode)
    if (onClick) {
      onClick(product);
    } else {
      // Otherwise navigate to product detail (for normal product list)
      navigate(`/products/${productId}`);
    }
  };

  const handleAddToCart = (e) => {
    e.stopPropagation();
    if (onAddToCart) {
      onAddToCart(product);
    } else {
      console.log('Add to cart:', productId);
    }
  };

  return (
    <div
      className="bg-white border border-gray-200 rounded-lg overflow-hidden transition-all duration-200 hover:shadow-xl hover:border-emerald-500 cursor-pointer"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleClick}
    >
      {/* Image Container */}
      <div className="relative h-48 bg-gray-50 flex items-center justify-center p-4">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={product.name}
            className="max-w-full max-h-full object-contain transition-transform duration-200 hover:scale-105"
            onError={(e) => {
              // Fallback to placeholder on image error
              e.target.style.display = 'none';
              e.target.nextElementSibling.style.display = 'flex';
            }}
          />
        ) : null}

        {/* Placeholder Icon */}
        <div
          className="w-full h-full flex flex-col items-center justify-center text-gray-300"
          style={{ display: imageUrl ? 'none' : 'flex' }}
        >
          <svg className="w-20 h-20 mb-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
          </svg>
          <span className="text-xs">No Image</span>
        </div>

        {/* Active Badge */}
        {!product.isActive && (
          <div className="absolute top-2 left-2 bg-gray-500 text-white text-xs font-semibold px-2 py-1 rounded">
            Inactive
          </div>
        )}

        {/* Product Code Badge */}
        <div className="absolute top-2 right-2 bg-blue-500 text-white text-xs font-mono px-2 py-1 rounded">
          {product.productCode}
        </div>
      </div>

      {/* Product Info */}
      <div className="p-4">
        {/* Category */}
        <div className="text-xs text-gray-500 mb-1 uppercase tracking-wide">
          {categoryName}
        </div>

        {/* Product Name */}
        <h3 className="text-sm font-semibold text-gray-800 mb-2 line-clamp-2 h-10" title={product.name}>
          {product.name}
        </h3>

        {/* Vendor */}
        {product.vendor && (
          <div className="text-xs text-gray-500 mb-2 flex items-center">
            <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V8a2 2 0 00-2-2h-5L9 4H4zm7 5a1 1 0 10-2 0v1H8a1 1 0 100 2h1v1a1 1 0 102 0v-1h1a1 1 0 100-2h-1V9z" clipRule="evenodd" />
            </svg>
            <span className="truncate">{product.vendor}</span>
          </div>
        )}

        {/* Price Section */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex flex-col">
            {hasDiscount ? (
              <>
                <span className="text-base font-bold text-red-600">
                  {formatVND(finalPrice)}
                </span>
                <div className="flex items-center gap-1 mt-0.5">
                  <span className="text-xs text-gray-500 line-through">
                    {formatVND(basePrice)}
                  </span>
                  <span className="bg-red-100 text-red-700 text-xs font-semibold px-1.5 py-0.5 rounded">
                    -{discountPercentage}%
                  </span>
                </div>
              </>
            ) : (
              <span className="text-base font-bold text-emerald-600">
                {formatVND(basePrice)}
              </span>
            )}
          </div>

          {/* Add to Cart Button */}
          <button
            onClick={handleAddToCart}
            className={`transition-all duration-200 p-2 rounded-full ${isHovered
              ? 'bg-emerald-600 text-white shadow-lg scale-110'
              : 'bg-emerald-50 text-emerald-600'
              }`}
            title="Add to cart"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </button>
        </div>

        {/* Stock Status */}
        <div className="pt-3 border-t border-gray-100">
          {product.isActive ? (
            <div className="flex items-center justify-between text-xs">
              <span className={`font-medium flex items-center ${onShelfQuantity > 0 ? 'text-green-600' : 'text-red-600'}`}>
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  {onShelfQuantity > 0 ? (
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  ) : (
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  )}
                </svg>
                {onShelfQuantity > 0 ? 'On Shelf' : 'Not on shelf'}
              </span>
              <span className={`font-semibold ${onShelfQuantity > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {onShelfQuantity} {onShelfQuantity === 1 ? 'unit' : 'units'}
              </span>
            </div>
          ) : (
            <div className="text-xs text-gray-500 font-medium">
              Product Inactive
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
