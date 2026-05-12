import { useNavigate } from 'react-router-dom'
import { useRef, useCallback } from 'react'
import { Check, XCircle, ShoppingCart } from 'lucide-react'
import { useCart } from '../../../contexts/CartContext'
import { useStore } from '../../../contexts/StoreContext'
import chatFeedbackService from '../../../services/chatFeedbackService'

const formatPrice = (price) => new Intl.NumberFormat('vi-VN').format(price)

const SOURCE_COLORS = {
  content: 'bg-blue-100 text-blue-700 border-blue-200',
  cf: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  apriori: 'bg-amber-100 text-amber-700 border-amber-200',
  session: 'bg-rose-100 text-rose-700 border-rose-200',
}

/**
 * ChatProductCard — Product card inside chatbot (Customer Edition)
 */
export const ChatProductCard = ({ product }) => {
  const navigate = useNavigate()
  const { addToCart } = useCart()
  const { selectedStore } = useStore()

  const hoverTimerRef = useRef(null)
  const hoverStartRef = useRef(0)
  const isHoverTrackedRef = useRef(false)
  const trackedClicksRef = useRef(new Set())
  const DWELL_THRESHOLD_MS = 1500

  const name = product.name || product.productName || 'Product'
  const price = product.unitPrice || product.unit_price || 0
  const qty = product.quantityOnShelf || product.quantity_on_shelf || 0
  const inStock = product.isInStock ?? product.is_in_stock ?? (qty > 0)
  const category = product.categoryName || product.category_name || ''
  const imageUrl = product.image || product.image_url || null
  
  // Extract dominant source for tracking
  const getDominantSource = () => {
    if (typeof product.topSource === 'string' && product.topSource) return product.topSource;
    if (typeof product.source === 'string' && product.source) return product.source;
    if (Array.isArray(product.ensembleSources) && product.ensembleSources.length > 0) {
      return product.ensembleSources[0];
    }
    return 'content';
  };
  const source = getDominantSource();
  const validStoreId = selectedStore?.id || 1;

  const handleCardClick = () => {
    navigate(`/product/${product.id}?ref=chat&src=${encodeURIComponent(source)}`)
    if (!trackedClicksRef.current.has(product.id)) {
      chatFeedbackService.trackClick(product.id, validStoreId, source)
      trackedClicksRef.current.add(product.id)
    }
  }

  const handleMouseEnter = useCallback(() => {
    // Only track hover on desktop (fine pointer) to avoid mobile noise
    const canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    if (!canHover || isHoverTrackedRef.current) return;

    hoverStartRef.current = Date.now()
    hoverTimerRef.current = setTimeout(() => {
      const dwellMs = Date.now() - hoverStartRef.current
      chatFeedbackService.trackHover(product.id, validStoreId, source, dwellMs)
      isHoverTrackedRef.current = true
    }, DWELL_THRESHOLD_MS)
  }, [product.id, validStoreId, source])

  const handleMouseLeave = useCallback(() => {
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current)
      hoverTimerRef.current = null
    }
  }, [])

  const handleAddToCart = (e) => {
    e.stopPropagation()
    if (!inStock) return

    addToCart({
      id: product.id,
      name,
      image: imageUrl,
      price,
      originalPrice: price,
      category,
    })

    chatFeedbackService.trackAddToCart(product.id, validStoreId, source)
  }

  return (
    <div
      onClick={handleCardClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="flex items-center gap-3 p-2.5 bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md hover:border-emerald-300 transition-all cursor-pointer ml-9 group relative overflow-hidden"
    >
      {/* Source Badge (Demo mode) */}
      <div className={`absolute top-0 right-0 rounded-bl-lg border-b border-l px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider ${SOURCE_COLORS[source] || 'bg-gray-100 text-gray-500'}`}>
        {source}
      </div>

      {/* Product Image */}
      <div className="flex-shrink-0 w-14 h-14 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center overflow-hidden">
        {imageUrl ? (
          <img 
            src={imageUrl} 
            alt={name} 
            loading="lazy" 
            className="w-full h-full object-contain group-hover:scale-110 transition-transform duration-300"
            onError={(e) => {
              e.target.style.display = 'none';
              e.target.nextElementSibling.style.display = 'flex';
            }}
          />
        ) : null}
        
        {/* Placeholder if no image */}
        <div 
          className="w-full h-full flex flex-col items-center justify-center text-gray-300"
          style={{ display: imageUrl ? 'none' : 'flex' }}
        >
          <svg className="w-6 h-6 mb-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
          </svg>
        </div>
      </div>

      {/* Product Info */}
      <div className="flex-1 min-w-0 py-0.5">
        <p className="text-sm font-medium text-gray-800 truncate group-hover:text-emerald-700 transition-colors pr-10">{name}</p>
        <div className="flex items-center justify-between mt-1">
          <div className="flex flex-col">
            <span className="text-xs font-bold text-emerald-600">{formatPrice(price)}đ</span>
            {inStock ? (
              <span className="text-[10px] text-gray-400">In stock: {qty}</span>
            ) : (
              <span className="text-[10px] text-red-500 font-medium">Out of stock</span>
            )}
          </div>

          {/* Add to Cart Button */}
          {inStock && (
            <button
              onClick={handleAddToCart}
              className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600 hover:bg-emerald-600 hover:text-white transition-colors border border-emerald-100 hover:border-emerald-600 shadow-sm"
              title="Add to cart"
            >
              <ShoppingCart size={14} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
