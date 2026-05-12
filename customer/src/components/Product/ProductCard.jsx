import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ShoppingCart } from 'lucide-react';
import { useStore } from '../../contexts/StoreContext';
import chatFeedbackService from '../../services/chatFeedbackService';

/**
 * ProductCard — Customer version
 * Decision.md #4 improvements:
 * - Larger cart button with emerald-100 bg
 * - Hover reveals "Add to Cart" text
 * - Out-of-stock overlay when quantityOnShelf <= 0
 */
export const ProductCard = ({ product, onAddToCart, trackingSource = 'organic' }) => {
  const [isHovered, setIsHovered] = useState(false);
  const navigate = useNavigate();
  const { selectedStore } = useStore();

  const hoverTimerRef = useRef(null);
  const isHoverTrackedRef = useRef(false);
  const trackedClicksRef = useRef(new Set());
  const DWELL_THRESHOLD_MS = 1500;

  const formatVND = (amount) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount);
  };

  const categoryName = product.category?.name || product.categoryName || 'Uncategorized';
  const imageUrl = product.image || null;

  const basePrice = product.unitPrice || 0;
  const discountPercentage = product.discountPercentage || 0;
  const hasDiscount = discountPercentage > 0;
  const finalPrice = hasDiscount ? basePrice * (1 - discountPercentage / 100) : basePrice;

  // Out-of-stock detection
  const isOutOfStock = product.quantityOnShelf !== undefined && product.quantityOnShelf <= 0;

  const handleAddToCart = (e) => {
    e.stopPropagation();
    if (isOutOfStock) return;
    chatFeedbackService.trackAddToCart(product.id, selectedStore?.id, trackingSource);
    if (onAddToCart) onAddToCart(product);
  };

  const handleCardClick = () => {
    navigate(`/product/${product.id}`);
    if (!trackedClicksRef.current.has(product.id)) {
      chatFeedbackService.trackClick(product.id, selectedStore?.id, trackingSource);
      trackedClicksRef.current.add(product.id);
    }
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
    if (isHoverTrackedRef.current) return;

    hoverTimerRef.current = setTimeout(() => {
      chatFeedbackService.trackHover(product.id, selectedStore?.id, trackingSource);
      isHoverTrackedRef.current = true;
    }, DWELL_THRESHOLD_MS);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
    }
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (hoverTimerRef.current) {
        clearTimeout(hoverTimerRef.current);
      }
    };
  }, []);

  return (
    <div
      className="bg-white border border-gray-100 rounded-xl overflow-hidden transition-all duration-200 hover:shadow-lg hover:border-emerald-400 cursor-pointer group relative"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleCardClick}
    >
      {/* Image Container */}
      <div className="relative h-44 bg-gray-50/50 flex items-center justify-center p-4">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={product.name}
            loading="lazy"
            className={`max-w-full max-h-full object-contain transition-transform duration-300 ${
              isOutOfStock ? 'grayscale opacity-50' : 'group-hover:scale-110'
            }`}
            onError={(e) => {
              e.target.style.display = 'none';
              e.target.nextElementSibling.style.display = 'flex';
            }}
          />
        ) : null}

        {/* Placeholder */}
        <div
          className="w-full h-full flex flex-col items-center justify-center text-gray-300"
          style={{ display: imageUrl ? 'none' : 'flex' }}
        >
          <svg className="w-16 h-16 mb-1" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
          </svg>
          <span className="text-xs">No Image</span>
        </div>

        {/* Out-of-stock overlay */}
        {isOutOfStock && (
          <div className="absolute inset-0 bg-gray-900/30 flex items-center justify-center">
            <span className="bg-gray-800 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-lg">
              Out of Stock
            </span>
          </div>
        )}

        {/* Discount Badge */}
        {hasDiscount && !isOutOfStock && (
          <div className="absolute top-2.5 right-2.5 bg-red-500 text-white text-xs font-bold px-2.5 py-1 rounded-lg shadow-sm">
            -{discountPercentage}%
          </div>
        )}

        {/* Inactive Badge */}
        {!product.isActive && (
          <div className="absolute top-2.5 left-2.5 bg-gray-500 text-white text-xs font-semibold px-2 py-1 rounded-lg">
            Inactive
          </div>
        )}
      </div>

      {/* Product Info */}
      <div className="p-3.5">
        {/* Category */}
        <div className="text-[11px] text-gray-400 mb-1 uppercase tracking-wider font-medium">
          {categoryName}
        </div>

        {/* Product Name */}
        <h3 className="text-sm font-semibold text-gray-800 mb-1 line-clamp-2 leading-snug min-h-[2.5rem]" title={product.name}>
          {product.name}
        </h3>

        {/* Vendor */}
        {product.vendor && (
          <div className="text-xs text-gray-400 mb-2 flex items-center gap-1">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V8a2 2 0 00-2-2h-5L9 4H4zm7 5a1 1 0 10-2 0v1H8a1 1 0 100 2h1v1a1 1 0 102 0v-1h1a1 1 0 100-2h-1V9z" clipRule="evenodd" />
            </svg>
            <span className="truncate">{product.vendor}</span>
          </div>
        )}

        {/* Price + Add to Cart */}
        <div className="flex items-end justify-between mt-2">
          <div className="flex flex-col">
            {hasDiscount ? (
              <>
                <span className="text-base font-bold text-red-600">
                  {formatVND(finalPrice)}
                </span>
                <span className="text-xs text-gray-400 line-through">
                  {formatVND(basePrice)}
                </span>
              </>
            ) : (
              <span className="text-base font-bold text-emerald-600">
                {formatVND(basePrice)}
              </span>
            )}
          </div>

          {/* Cart Button — larger with bg, expands on hover */}
          {isOutOfStock ? (
            <span className="bg-gray-100 text-gray-400 text-xs font-semibold px-3 py-2 rounded-xl">
              Sold Out
            </span>
          ) : (
            <button
              onClick={handleAddToCart}
              className={`flex items-center gap-1.5 transition-all duration-200 rounded-xl font-semibold ${
                isHovered
                  ? 'bg-emerald-600 text-white shadow-md px-3.5 py-2'
                  : 'bg-emerald-100 text-emerald-600 px-2.5 py-2'
              }`}
              title="Add to cart"
            >
              <ShoppingCart className="w-4 h-4" />
              <span className={`text-xs whitespace-nowrap transition-all duration-200 overflow-hidden ${
                isHovered ? 'max-w-[80px] opacity-100' : 'max-w-0 opacity-0'
              }`}>
                Add
              </span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
