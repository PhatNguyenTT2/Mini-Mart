import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ShoppingCart, Minus, Plus, Package, Clock, AlertTriangle, Leaf } from 'lucide-react';
import { Header } from '../components/Header';
import Footer from '../components/Footer/Footer';
import productService from '../services/productService';
import { useCart } from '../contexts/CartContext';
import { useStore } from '../contexts/StoreContext';
import { lazy, Suspense } from 'react';
import chatFeedbackService from '../services/chatFeedbackService';

const ProductCard = lazy(() => import('../components/Product/ProductCard').then(module => ({ default: module.ProductCard })));

/**
 * ProductDetail — Customer PDP with FEFO batch display
 * Aggregates data from:
 *   - Catalog Service: product info (name, price, image, vendor, category)
 *   - Inventory Service: FEFO-sorted batches (public endpoint)
 */
const formatVND = (price) => {
  if (price === undefined || price === null) return '0 đ';
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
};

const formatDate = (dateString) => {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString('vi-VN');
};
export default function ProductDetail() {
  const { productId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { addToCart } = useCart();
  const { selectedStore } = useStore();

  const chatRef = searchParams.get('ref');
  const chatSource = searchParams.get('src') || 'content';

  const [product, setProduct] = useState(null);
  const [batches, setBatches] = useState([]);
  const [totalOnShelf, setTotalOnShelf] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [addedToCart, setAddedToCart] = useState(false);
  const [descExpanded, setDescExpanded] = useState(false);
  
  const [relatedProducts, setRelatedProducts] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const storeId = selectedStore?.id || 1;

        // Parallel fetch: Catalog + Inventory
        const [productRes, batchRes] = await Promise.all([
          productService.getProductById(productId),
          productService.getProductBatches(storeId, productId)
        ]);

        const fetchedProduct = productRes?.data?.product || null;
        setProduct(fetchedProduct);
        setBatches(batchRes?.data?.batches || []);
        setTotalOnShelf(batchRes?.data?.totalOnShelf || 0);
        
        if (fetchedProduct?.category?.id || fetchedProduct?.categoryId) {
          const catId = fetchedProduct?.category?.id || fetchedProduct?.categoryId;
          try {
            const relatedRes = await productService.getProductsByCategory(catId);
            const rProducts = relatedRes?.data?.products || relatedRes?.products || [];
            // Filter out current product and get max 5
            setRelatedProducts(rProducts.filter(p => p.id !== Number(productId)).slice(0, 5));
          } catch (rErr) {
            console.error('Failed to fetch related products', rErr);
          }
        }
      } catch (err) {
        console.error('Failed to fetch product detail:', err);
        setError(err.response?.status === 404 ? 'not_found' : 'error');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [productId, selectedStore]);

  // Compute best price from batches (lowest discounted price)
  const priceInfo = useMemo(() => {
    if (!product) return { basePrice: 0, finalPrice: 0, hasDiscount: false, discountPct: 0 };

    const basePrice = product.unitPrice || 0;

    if (batches.length === 0) {
      return { basePrice, finalPrice: basePrice, hasDiscount: false, discountPct: 0 };
    }

    // Find the batch with the highest discount (customer gets best price)
    const maxDiscount = Math.max(...batches.map(b => b.discountPercentage || 0));
    const finalPrice = maxDiscount > 0 ? basePrice * (1 - maxDiscount / 100) : basePrice;

    return {
      basePrice,
      finalPrice,
      hasDiscount: maxDiscount > 0,
      discountPct: maxDiscount
    };
  }, [product, batches]);

  // Save to recently viewed
  useEffect(() => {
    if (product && priceInfo.basePrice > 0) {
      try {
        const saved = localStorage.getItem('recently_viewed');
        let viewed = saved ? JSON.parse(saved) : [];
        
        // Remove if already exists
        viewed = viewed.filter(p => p.id !== product.id);
        
        // Add to front
        viewed.unshift({
          id: product.id,
          name: product.name,
          image: product.image,
          unitPrice: priceInfo.basePrice,
          discountPercentage: priceInfo.discountPct,
          category: product.category,
          vendor: product.vendor
        });
        
        // Keep only max 10
        if (viewed.length > 10) {
          viewed = viewed.slice(0, 10);
        }
        
        localStorage.setItem('recently_viewed', JSON.stringify(viewed));
      } catch (err) {
        console.error('Failed to save recently viewed', err);
      }
    }
  }, [product, priceInfo]);



  const isOutOfStock = totalOnShelf <= 0;

  const handleAddToCart = () => {
    if (!product || isOutOfStock) return;

    addToCart({
      id: product.id,
      name: product.name,
      image: product.image,
      price: priceInfo.finalPrice,
      originalPrice: priceInfo.basePrice,
      category: product.categoryName || 'Uncategorized',
      quantity
    });

    const validStoreId = selectedStore?.id || 1;
    const trackingSource = chatRef === 'chat' ? chatSource : 'organic';
    chatFeedbackService.trackAddToCart(Number(productId), validStoreId, trackingSource);

    if (chatRef === 'chat') {
      // Clean up tracking parameters from URL to avoid duplicate tracking on page refresh
      window.history.replaceState(null, '', window.location.pathname);
    }

    setAddedToCart(true);
    setTimeout(() => setAddedToCart(false), 2000);
  };

  // ── Loading State ──
  if (loading) {
    return (
      <>
        <Header />
        <main className="max-w-[1440px] mx-auto px-4 lg:px-8 py-8">
          <div className="animate-pulse">
            <div className="h-6 w-32 bg-gray-200 rounded mb-8" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12">
              <div className="aspect-square bg-gray-100 rounded-2xl" />
              <div className="space-y-4">
                <div className="h-4 w-24 bg-gray-200 rounded" />
                <div className="h-8 w-3/4 bg-gray-200 rounded" />
                <div className="h-6 w-1/3 bg-gray-200 rounded" />
                <div className="h-40 bg-gray-100 rounded-xl mt-6" />
              </div>
            </div>
          </div>
        </main>
        <Footer />
      </>
    );
  }

  // ── Error / Not Found State ──
  if (error || !product) {
    return (
      <>
        <Header />
        <main className="max-w-[1440px] mx-auto px-4 lg:px-8 py-20">
          <div className="flex flex-col items-center justify-center text-center">
            <div className="text-6xl mb-4">{error === 'not_found' ? '🔍' : '⚠️'}</div>
            <h2 className="text-xl font-bold text-gray-800 mb-2">
              {error === 'not_found' ? 'Product not found' : 'An error occurred'}
            </h2>
            <p className="text-gray-500 mb-6">
              {error === 'not_found'
                ? 'This product may have been deleted or does not exist.'
                : 'Unable to load product information. Please try again.'}
            </p>
            <button
              onClick={() => navigate('/')}
              className="bg-emerald-600 text-white font-semibold px-6 py-2.5 rounded-xl hover:bg-emerald-700 transition-colors"
            >
              ← Back to Home
            </button>
          </div>
        </main>
        <Footer />
      </>
    );
  }

  return (
    <>
      <Header />
      <main className="max-w-[1440px] mx-auto px-4 lg:px-8 py-8">
        {/* Breadcrumb Navigation */}
        <nav className="flex items-center gap-2 text-sm text-gray-500 mb-6">
          <button 
            onClick={() => navigate('/')} 
            className="hover:text-emerald-600 transition-colors"
          >
            Home
          </button>
          <span className="text-gray-300">/</span>
          {product.category?.name && (
            <>
              <span className="hover:text-emerald-600 transition-colors cursor-default">
                {product.category.name}
              </span>
              <span className="text-gray-300">/</span>
            </>
          )}
          <span className="text-gray-800 font-medium truncate max-w-[200px] sm:max-w-md">
            {product.name}
          </span>
        </nav>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 lg:gap-12">
          {/* ── Left Column: Product Image ── */}
          <div className="relative">
            <div className="aspect-square bg-gray-50 rounded-2xl flex items-center justify-center overflow-hidden border border-gray-100">
              {product.image ? (
                <img
                  src={product.image}
                  alt={product.name}
                  className={`max-w-full max-h-full object-contain p-6 ${isOutOfStock ? 'grayscale opacity-50' : ''}`}
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.nextElementSibling.style.display = 'flex';
                  }}
                />
              ) : null}
              <div
                className="w-full h-full flex flex-col items-center justify-center text-gray-300"
                style={{ display: product.image ? 'none' : 'flex' }}
              >
                <svg className="w-24 h-24 mb-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
                </svg>
                <span className="text-sm">No Image</span>
              </div>

              {/* Out-of-stock overlay */}
              {isOutOfStock && (
                <div className="absolute inset-0 bg-gray-900/30 rounded-2xl flex items-center justify-center">
                  <span className="bg-gray-800 text-white text-sm font-bold px-6 py-3 rounded-xl shadow-lg">
                    Out of stock at this store
                  </span>
                </div>
              )}

              {/* Discount badge */}
              {priceInfo.hasDiscount && !isOutOfStock && (
                <div className="absolute top-4 right-4 bg-red-500 text-white text-sm font-bold px-3 py-1.5 rounded-xl shadow-sm">
                  -{priceInfo.discountPct}%
                </div>
              )}
            </div>
          </div>

          {/* ── Right Column: Product Info ── */}
          <div className="flex flex-col">
            {/* Category */}
            <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold mb-2">
              {product.categoryName || 'Uncategorized'}
            </span>

            {/* Product Name */}
            <h1 className="text-2xl lg:text-3xl font-bold text-gray-900 mb-2 leading-tight">
              {product.name}
            </h1>

            {/* Vendor */}
            {product.vendor && (
              <p className="text-sm text-gray-400 mb-4 flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V8a2 2 0 00-2-2h-5L9 4H4zm7 5a1 1 0 10-2 0v1H8a1 1 0 100 2h1v1a1 1 0 102 0v-1h1a1 1 0 100-2h-1V9z" clipRule="evenodd" />
                </svg>
                {product.vendor}
              </p>
            )}

            {/* Price */}
            <div className="flex items-baseline gap-3 mb-6">
              <span className={`text-3xl font-bold ${priceInfo.hasDiscount ? 'text-red-600' : 'text-emerald-600'}`}>
                {formatVND(priceInfo.finalPrice)}
              </span>
              {priceInfo.hasDiscount && (
                <span className="text-lg text-gray-400 line-through">
                  {formatVND(priceInfo.basePrice)}
                </span>
              )}
            </div>

            {/* Store info */}
            <div className="text-sm text-gray-500 mb-4 flex items-center gap-1.5">
              <Package className="w-4 h-4" />
              Store: <span className="font-medium text-gray-700">{selectedStore?.name || 'Not selected'}</span>
            </div>

            {/* ── FEFO Batch Table ── */}
            <BatchTable
              batches={batches}
              formatDate={formatDate}
              storeName={selectedStore?.name}
            />

            {/* ── Quantity Selector + Add to Cart ── */}
            <div className="mt-6 flex items-center gap-4">
              {/* Quantity */}
              <div className="flex items-center border-2 border-gray-200 rounded-xl overflow-hidden">
                <button
                  onClick={() => setQuantity(q => Math.max(1, q - 1))}
                  disabled={isOutOfStock}
                  className="w-10 h-10 flex items-center justify-center text-gray-500 hover:bg-gray-50 transition-colors disabled:opacity-30"
                >
                  <Minus className="w-4 h-4" />
                </button>
                <span className="w-12 text-center font-semibold text-gray-800">{quantity}</span>
                <button
                  onClick={() => setQuantity(q => Math.min(totalOnShelf, q + 1))}
                  disabled={isOutOfStock || quantity >= totalOnShelf}
                  className="w-10 h-10 flex items-center justify-center text-gray-500 hover:bg-gray-50 transition-colors disabled:opacity-30"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>

              {/* Add to Cart Button */}
              <button
                id="pdp-add-to-cart"
                onClick={handleAddToCart}
                disabled={isOutOfStock}
                className={`flex-1 flex items-center justify-center gap-2 py-3 px-6 rounded-xl font-bold text-sm transition-all duration-200 ${
                  addedToCart
                    ? 'bg-emerald-100 text-emerald-700 border-2 border-emerald-300'
                    : isOutOfStock
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-lg hover:shadow-xl active:scale-[0.98]'
                }`}
              >
                <ShoppingCart className="w-5 h-5" />
                {addedToCart
                  ? '✓ Added to cart!'
                  : isOutOfStock
                    ? 'Out of stock'
                    : 'Add to cart'}
              </button>
            </div>

            {/* Total price hint */}
            {!isOutOfStock && quantity > 1 && (
              <p className="text-sm text-gray-400 mt-2">
                Total: <span className="font-semibold text-gray-600">{formatVND(priceInfo.finalPrice * quantity)}</span>
              </p>
            )}

            {/* ── Product Description ── */}
            <div className="mt-8 border-t border-gray-100 pt-6">
              <h3 className="text-lg font-bold text-gray-800 mb-3">Product Description</h3>
              <div className={`text-sm text-gray-600 leading-relaxed whitespace-pre-line ${!descExpanded ? 'line-clamp-4' : ''}`}>
                {product.description || 'Description is being updated.'}
              </div>
              {product.description && product.description.length > 200 && (
                <button
                  onClick={() => setDescExpanded(!descExpanded)}
                  className="text-emerald-600 hover:text-emerald-700 text-sm font-semibold mt-2"
                >
                  {descExpanded ? 'Show less' : 'Read more'}
                </button>
              )}
            </div>
          </div>
        </div>
        
        {/* Related Products Section */}
        {relatedProducts.length > 0 && (
          <section className="mt-16 pt-10 border-t border-gray-100">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">You Might Also Like</h2>
            <Suspense fallback={
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="h-64 bg-gray-100 rounded-xl animate-pulse" />
                ))}
              </div>
            }>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {relatedProducts.map(relProduct => (
                  <ProductCard 
                    key={relProduct.id} 
                    product={relProduct} 
                    onAddToCart={(p) => {
                      addToCart({
                        id: p.id,
                        name: p.name,
                        image: p.image,
                        price: p.discountPercentage > 0
                          ? p.unitPrice * (1 - p.discountPercentage / 100)
                          : p.unitPrice,
                        originalPrice: p.unitPrice,
                        category: p.category?.name || 'Uncategorized',
                      });
                    }} 
                  />
                ))}
              </div>
            </Suspense>
          </section>
        )}
      </main>
      <Footer />
    </>
  );
}

// ── Batch Table Component ──────────────────────

function BatchTable({ batches, formatDate, storeName }) {
  if (batches.length === 0) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
        <div className="flex items-center gap-2 text-amber-700">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span className="text-sm font-medium">
            Product is currently out of stock at this store
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 bg-white border-b border-gray-100">
        <h3 className="text-sm font-bold text-gray-800 flex items-center gap-2">
          <Package className="w-4 h-4 text-emerald-600" />
          Available batches at {storeName || 'store'}
        </h3>
      </div>

      {/* Batch Rows */}
      <div className="divide-y divide-gray-100">
        {batches.map((batch, index) => (
          <BatchRow
            key={batch.id}
            batch={batch}
            index={index}
            formatDate={formatDate}
          />
        ))}
      </div>

      {/* FEFO Notice */}
      <div className="px-4 py-2.5 bg-emerald-50 border-t border-emerald-100">
        <p className="text-xs text-emerald-700 flex items-center gap-1.5">
          <Leaf className="w-3.5 h-3.5" />
          System automatically dispatches batches expiring first (FEFO)
        </p>
      </div>
    </div>
  );
}

// ── Batch Row Component ──────────────────────

function BatchRow({ batch, index, formatDate }) {
  const expiryStatus = getExpiryStatus(batch.expiryDate);

  return (
    <div className={`px-4 py-3 flex items-center justify-between ${index === 0 ? 'bg-emerald-50/50' : 'bg-white'}`}>
      <div className="flex items-center gap-3">
        {/* FEFO Priority Indicator */}
        <div className={`w-2 h-2 rounded-full shrink-0 ${expiryStatus.dotColor}`} />

        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-800">
              Batch {batch.batchCode}
            </span>
            {index === 0 && (
              <span className="text-[10px] font-bold bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">
                Dispatch first
              </span>
            )}
            {batch.promotionApplied === 'auto_fresh' && (
              <span className="text-[10px] font-bold bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full flex items-center gap-0.5">
                Fresh Discount
              </span>
            )}
          </div>

          {/* Expiry Date */}
          <div className="flex items-center gap-1.5 mt-0.5">
            <Clock className={`w-3 h-3 ${expiryStatus.iconColor}`} />
            <span className={`text-xs font-medium ${expiryStatus.textColor}`}>
              {batch.expiryDate
                ? `EXP: ${formatDate(batch.expiryDate)}`
                : 'No EXP'}
              {expiryStatus.label && ` · ${expiryStatus.label}`}
            </span>
          </div>
        </div>
      </div>

      {/* Quantity available */}
      <div className="text-right">
        <span className="text-sm font-bold text-gray-700">
          {batch.quantityAvailable}
        </span>
        <span className="text-xs text-gray-400 ml-1">items</span>
      </div>
    </div>
  );
}

// ── Expiry Status Helper ──────────────────────

function getExpiryStatus(expiryDate) {
  if (!expiryDate) {
    return {
      dotColor: 'bg-gray-300',
      iconColor: 'text-gray-400',
      textColor: 'text-gray-500',
      label: null
    };
  }

  const now = new Date();
  const expiry = new Date(expiryDate);
  const diffDays = Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));

  if (diffDays <= 0) {
    return {
      dotColor: 'bg-red-500',
      iconColor: 'text-red-500',
      textColor: 'text-red-600',
      label: 'Expired'
    };
  }
  if (diffDays <= 7) {
    return {
      dotColor: 'bg-red-500',
      iconColor: 'text-red-500',
      textColor: 'text-red-600',
      label: `${diffDays} days left`
    };
  }
  if (diffDays <= 30) {
    return {
      dotColor: 'bg-amber-400',
      iconColor: 'text-amber-500',
      textColor: 'text-amber-600',
      label: `${diffDays} days left`
    };
  }
  return {
    dotColor: 'bg-emerald-500',
    iconColor: 'text-emerald-500',
    textColor: 'text-gray-500',
    label: null
  };
}
