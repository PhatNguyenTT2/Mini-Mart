import { useState, useEffect, useMemo, useCallback, lazy, Suspense } from 'react';
import { ChevronRight, ChevronDown, Tag } from 'lucide-react';
import categoryService from '../../services/categoryService';
import productService from '../../services/productService';
import { useCart } from '../../contexts/CartContext';
import { useStore } from '../../contexts/StoreContext';
import useEmblaCarousel from 'embla-carousel-react';
import Autoplay from 'embla-carousel-autoplay';

const ProductCard = lazy(() => import('../Product/ProductCard').then(module => ({ default: module.ProductCard })));

const PRODUCTS_PER_PAGE = 20;

/**
 * Homepage Merchandising Component
 * Decision.md #2: Full-width "showroom" — no sidebar on homepage.
 * Sections: Hero → Top Categories (with subcategory expansion) → Products (Load More)
 *
 * Category → Product relationship:
 *   Products belong to SUBCATEGORIES (leaf nodes).
 *   Root categories have children[]. When user clicks a root category,
 *   we collect all children IDs and filter by those.
 */
export default function HomeMerchandising() {
  const [categoryTree, setCategoryTree] = useState([]);
  const [products, setProducts] = useState([]);
  const [recentlyViewed, setRecentlyViewed] = useState([]);
  const [displayCount, setDisplayCount] = useState(PRODUCTS_PER_PAGE);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [selectedRootId, setSelectedRootId] = useState(null);
  const [selectedSubId, setSelectedSubId] = useState(null);
  const [expandedRoot, setExpandedRoot] = useState(null);
  const [sortBy, setSortBy] = useState('default');
  const { addToCart } = useCart();
  const { selectedStore } = useStore();

  const [emblaRef] = useEmblaCarousel({ loop: true }, [Autoplay({ delay: 5000, stopOnInteraction: false })]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [catResult, prodResult, invResult] = await Promise.all([
          categoryService.getCategoryTree(),
          productService.getActiveProducts(),
          selectedStore?.id ? productService.getStoreInventorySummary(selectedStore.id).catch(() => ({ data: [] })) : Promise.resolve({ data: [] })
        ]);

        setCategoryTree(catResult?.data?.categories || []);

        const inventoryMap = {};
        if (invResult?.data) {
          invResult.data.forEach(inv => {
            inventoryMap[inv.productId] = {
              quantityOnShelf: inv.quantityOnShelf || 0,
              discountPercentage: inv.discountPercentage || 0
            };
          });
        }

        const mergedProducts = (prodResult?.data?.products || []).map(p => {
          const inv = inventoryMap[p.id] || { quantityOnShelf: 0, discountPercentage: 0 };
          return {
            ...p,
            quantityOnShelf: inv.quantityOnShelf,
            discountPercentage: inv.discountPercentage || p.discountPercentage || 0
          };
        });

        setProducts(mergedProducts);
      } catch (err) {
        console.error('Failed to fetch data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();

    // Load recently viewed
    try {
      const saved = localStorage.getItem('recently_viewed');
      if (saved) {
        setRecentlyViewed(JSON.parse(saved));
      }
    } catch (err) {
      console.error('Failed to load recently viewed', err);
    }
  }, [selectedStore?.id]);

  // Build a set of valid categoryIds for the selected root or sub
  const activeCategoryIds = useMemo(() => {
    if (selectedSubId) return new Set([selectedSubId]);
    if (!selectedRootId) return null; // null = show all
    const root = categoryTree.find(c => c.id === selectedRootId);
    if (!root) return null;
    // Include root id + all children ids (products may sit at either level)
    const ids = new Set([root.id]);
    (root.children || []).forEach(child => ids.add(child.id));
    return ids;
  }, [selectedRootId, selectedSubId, categoryTree]);

  // Filter products using the ID set
  const filteredProducts = useMemo(() => {
    let result = products;
    if (activeCategoryIds) {
      result = products.filter(p => {
        const catId = p.categoryId || p.category_id || p.category?.id;
        return activeCategoryIds.has(catId);
      });
    }

    // Sort logic
    if (sortBy === 'price_asc') {
      return [...result].sort((a, b) => {
        const priceA = a.discountPercentage ? a.unitPrice * (1 - a.discountPercentage / 100) : a.unitPrice;
        const priceB = b.discountPercentage ? b.unitPrice * (1 - b.discountPercentage / 100) : b.unitPrice;
        return priceA - priceB;
      });
    }
    if (sortBy === 'price_desc') {
      return [...result].sort((a, b) => {
        const priceA = a.discountPercentage ? a.unitPrice * (1 - a.discountPercentage / 100) : a.unitPrice;
        const priceB = b.discountPercentage ? b.unitPrice * (1 - b.discountPercentage / 100) : b.unitPrice;
        return priceB - priceA;
      });
    }
    if (sortBy === 'name_asc') {
      return [...result].sort((a, b) => a.name.localeCompare(b.name));
    }
    // Default sort: prioritize discount first
    return [...result].sort((a, b) => {
      const hasDiscountA = (a.discountPercentage || 0) > 0 ? 1 : 0;
      const hasDiscountB = (b.discountPercentage || 0) > 0 ? 1 : 0;
      if (hasDiscountA !== hasDiscountB) {
        return hasDiscountB - hasDiscountA;
      }
      return 0;
    });
  }, [products, activeCategoryIds, sortBy]);

  const displayedProducts = filteredProducts.slice(0, displayCount);
  const hasMore = displayCount < filteredProducts.length;

  const handleLoadMore = () => {
    setLoadingMore(true);
    setTimeout(() => {
      setDisplayCount(prev => prev + PRODUCTS_PER_PAGE);
      setLoadingMore(false);
    }, 300);
  };

  const handleRootClick = useCallback((rootId) => {
    if (selectedRootId === rootId) {
      // Deselect
      setSelectedRootId(null);
      setSelectedSubId(null);
      setExpandedRoot(null);
    } else {
      setSelectedRootId(rootId);
      setSelectedSubId(null);
      // Auto-expand subcategories if any
      const root = categoryTree.find(c => c.id === rootId);
      setExpandedRoot(root?.children?.length > 0 ? rootId : null);
    }
    setDisplayCount(PRODUCTS_PER_PAGE);
    setSortBy('default');
  }, [selectedRootId, categoryTree]);

  const handleSubClick = useCallback((subId) => {
    setSelectedSubId(prev => prev === subId ? null : subId);
    setDisplayCount(PRODUCTS_PER_PAGE);
    setSortBy('default');
  }, []);

  const handleAddToCart = (product) => {
    addToCart({
      id: product.id,
      name: product.name,
      image: product.image,
      price: product.discountPercentage > 0
        ? product.unitPrice * (1 - product.discountPercentage / 100)
        : product.unitPrice,
      originalPrice: product.unitPrice,
      category: product.category?.name || 'Uncategorized',
    });
  };

  // Get the selected root for display
  const selectedRoot = categoryTree.find(c => c.id === selectedRootId);
  const sectionTitle = selectedSubId
    ? selectedRoot?.children?.find(c => c.id === selectedSubId)?.name || 'Products'
    : selectedRoot?.name || 'All Products';

  return (
    <div className="space-y-10">
      {/* ── Hero Banner Carousel ── */}
      <section id="hero-banner" className="relative rounded-2xl overflow-hidden bg-gray-50">
        <div className="overflow-hidden" ref={emblaRef}>
          <div className="flex">

            {/* Slide 1 */}
            <div className="flex-[0_0_100%] min-w-0 relative bg-gradient-to-r from-emerald-600 via-emerald-500 to-teal-400 p-8 md:p-12 lg:p-16">
              <div className="relative z-10 max-w-lg">
                <span className="inline-block bg-white/20 backdrop-blur-sm text-white text-xs font-bold px-3 py-1 rounded-full mb-4 uppercase tracking-wider">
                  Fresh & Quality
                </span>
                <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight">
                  Fresh Groceries<br />
                  <span className="text-emerald-100">Delivered to You</span>
                </h1>
                <p className="text-emerald-50 text-base md:text-lg mb-6 leading-relaxed">
                  Browse hundreds of products from your local store with the best prices and freshest quality.
                </p>
                <button
                  onClick={() => document.getElementById('products-section')?.scrollIntoView({ behavior: 'smooth' })}
                  className="bg-white text-emerald-600 font-bold text-sm px-6 py-3 rounded-xl hover:bg-emerald-50 transition-colors shadow-lg"
                >
                  Shop Now →
                </button>
              </div>
              <div className="absolute right-0 top-0 w-1/2 h-full opacity-10 pointer-events-none">
                <div className="absolute right-10 top-10 w-32 h-32 bg-white rounded-full" />
                <div className="absolute right-32 bottom-10 w-48 h-48 bg-white rounded-full" />
                <div className="absolute right-0 top-1/2 w-20 h-20 bg-white rounded-full" />
              </div>
            </div>

            {/* Slide 2 */}
            <div className="flex-[0_0_100%] min-w-0 relative bg-gradient-to-r from-orange-500 via-amber-500 to-yellow-400 p-8 md:p-12 lg:p-16">
              <div className="relative z-10 max-w-lg">
                <span className="inline-block bg-white/20 backdrop-blur-sm text-white text-xs font-bold px-3 py-1 rounded-full mb-4 uppercase tracking-wider">
                  Weekend Special
                </span>
                <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight">
                  Up to 50% Off<br />
                  <span className="text-orange-100">On Selected Items</span>
                </h1>
                <p className="text-orange-50 text-base md:text-lg mb-6 leading-relaxed">
                  Don't miss out on our biggest weekend sale. Stock up your pantry with massive discounts.
                </p>
                <button
                  onClick={() => { setSelectedRootId(null); document.getElementById('products-section')?.scrollIntoView({ behavior: 'smooth' }); }}
                  className="bg-white text-orange-600 font-bold text-sm px-6 py-3 rounded-xl hover:bg-orange-50 transition-colors shadow-lg"
                >
                  View Deals →
                </button>
              </div>
              <div className="absolute right-0 top-0 w-1/2 h-full opacity-10 pointer-events-none">
                <div className="absolute right-20 top-20 w-40 h-40 bg-white rounded-full blur-xl" />
                <div className="absolute left-10 bottom-10 w-32 h-32 bg-white rounded-full blur-lg" />
              </div>
            </div>

            {/* Slide 3 */}
            <div className="flex-[0_0_100%] min-w-0 relative bg-gradient-to-r from-blue-600 via-indigo-500 to-purple-500 p-8 md:p-12 lg:p-16">
              <div className="relative z-10 max-w-lg">
                <span className="inline-block bg-white/20 backdrop-blur-sm text-white text-xs font-bold px-3 py-1 rounded-full mb-4 uppercase tracking-wider">
                  Fast Delivery
                </span>
                <h1 className="text-3xl md:text-4xl lg:text-5xl font-bold text-white mb-4 leading-tight">
                  Same Day Delivery<br />
                  <span className="text-blue-100">Right to Your Door</span>
                </h1>
                <p className="text-blue-50 text-base md:text-lg mb-6 leading-relaxed">
                  Order before 2 PM and get your groceries delivered within hours. Freshness guaranteed.
                </p>
                <button
                  onClick={() => document.getElementById('products-section')?.scrollIntoView({ behavior: 'smooth' })}
                  className="bg-white text-blue-600 font-bold text-sm px-6 py-3 rounded-xl hover:bg-blue-50 transition-colors shadow-lg"
                >
                  Order Now →
                </button>
              </div>
              <div className="absolute right-0 top-0 w-1/2 h-full opacity-10 pointer-events-none">
                <svg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" className="absolute right-10 top-0 w-64 h-64 fill-white">
                  <path d="M44.7,-76.4C58.8,-69.2,71.8,-59.1,81.6,-46.3C91.4,-33.5,98,-18,97.7,-2.5C97.4,13.1,90.2,28.6,80.1,41.6C70,54.6,57,65.2,42.5,73.1C28,81,12,86.2,-4.5,86.6C-21,87,-37.9,82.5,-52.1,73.8C-66.3,65.1,-77.8,52.2,-85.7,37.3C-93.6,22.4,-97.9,5.5,-95.7,-10.8C-93.5,-27.1,-84.8,-42.8,-72.6,-54.6C-60.4,-66.4,-44.7,-74.3,-30,-78.9C-15.3,-83.5,-1.5,-84.8,12.7,-82.5C26.9,-80.2,41.4,-74.3,44.7,-76.4Z" transform="translate(100 100)" />
                </svg>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── Recently Viewed ── */}
      {recentlyViewed.length >= 2 && (
        <section id="recently-viewed" className="mb-10">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-xl font-bold text-gray-800">Recently Viewed</h2>
          </div>
          <div className="flex gap-4 overflow-x-auto pb-4 snap-x snap-mandatory hide-scrollbar">
            <Suspense fallback={<div className="h-44 w-44 bg-gray-100 rounded-xl animate-pulse flex-shrink-0" />}>
              {recentlyViewed.map((product) => (
                <div key={product.id} className="min-w-[160px] sm:min-w-[200px] md:min-w-[220px] snap-start flex-shrink-0">
                  <ProductCard
                    product={product}
                    onAddToCart={handleAddToCart}
                  />
                </div>
              ))}
            </Suspense>
          </div>
          <style dangerouslySetInnerHTML={{
            __html: `
            .hide-scrollbar::-webkit-scrollbar { display: none; }
            .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
          `}} />
        </section>
      )}

      {/* ── Top Categories ── */}
      <section id="categories-section">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-xl font-bold text-gray-800">Browse by Category</h2>
          {selectedRootId && (
            <button
              onClick={() => { setSelectedRootId(null); setSelectedSubId(null); setExpandedRoot(null); }}
              className="text-sm text-emerald-600 hover:text-emerald-700 font-semibold transition-colors"
            >
              View All →
            </button>
          )}
        </div>

        {loading ? (
          <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-8 gap-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="animate-pulse">
                <div className="aspect-square bg-gray-100 rounded-2xl mb-2" />
                <div className="h-3 bg-gray-100 rounded mx-auto w-3/4" />
              </div>
            ))}
          </div>
        ) : (
          <>
            {/* Root categories — grid layout for better balance */}
            <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-8 gap-3">
              {categoryTree.map((cat) => {
                const isActive = selectedRootId === cat.id;
                const hasChildren = cat.children && cat.children.length > 0;
                return (
                  <button
                    key={cat.id}
                    onClick={() => handleRootClick(cat.id)}
                    className={`flex flex-col items-center gap-1.5 p-3 rounded-2xl transition-all duration-200 group ${isActive
                      ? 'bg-emerald-50 border-2 border-emerald-500 shadow-sm'
                      : 'bg-white border-2 border-gray-100 hover:border-emerald-300 hover:shadow-sm'
                      }`}
                  >
                    <div className={`w-14 h-14 rounded-xl flex items-center justify-center overflow-hidden transition-all ${isActive ? 'bg-emerald-100 scale-110' : 'bg-gray-50 group-hover:bg-emerald-50 group-hover:scale-105'
                      }`}>
                      {cat.image ? (
                        <img src={cat.image} alt={cat.name} className="w-10 h-10 object-cover rounded-lg" onError={(e) => { e.target.style.display = 'none'; }} />
                      ) : (
                        <Tag className="w-6 h-6 text-emerald-500" />
                      )}
                    </div>
                    <span className={`text-[11px] font-semibold text-center line-clamp-2 leading-tight ${isActive ? 'text-emerald-700' : 'text-gray-600'
                      }`}>
                      {cat.name}
                    </span>
                    <div className="flex items-center gap-1">
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${isActive ? 'bg-emerald-200 text-emerald-800' : 'bg-gray-100 text-gray-500'
                        }`}>
                        {cat.productCount || 0}
                      </span>
                      {hasChildren && (
                        <ChevronDown className={`w-3 h-3 transition-transform ${isActive ? 'text-emerald-600 rotate-180' : 'text-gray-400'
                          }`} />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Subcategories — shown when root is expanded */}
            {expandedRoot && selectedRoot?.children?.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2 pl-1">
                <span className="text-xs text-gray-400 font-medium self-center mr-1">Subcategories:</span>
                {selectedRoot.children.map((sub) => {
                  const isSubActive = selectedSubId === sub.id;
                  return (
                    <button
                      key={sub.id}
                      onClick={() => handleSubClick(sub.id)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${isSubActive
                        ? 'bg-emerald-500 text-white shadow-sm'
                        : 'bg-gray-100 text-gray-600 hover:bg-emerald-50 hover:text-emerald-700'
                        }`}
                    >
                      {sub.name}
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${isSubActive ? 'bg-emerald-400 text-white' : 'bg-white text-gray-500'
                        }`}>
                        {sub.productCount || 0}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </>
        )}
      </section>

      {/* ── Promotion Products Section ── */}
      <section id="promotions" className="mb-10">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-xl font-bold text-red-650 flex items-center gap-2 font-['Poppins',sans-serif]">
              <span className="inline-block bg-red-100 p-1.5 rounded-lg text-red-600">
                <Tag className="w-4 h-4" />
              </span>
              Hot Promotions
            </h2>
            <p className="text-sm text-gray-400 mt-1">Super savings on your favorite products</p>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-64 bg-gray-100 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : products.filter(p => (p.discountPercentage || 0) > 0).length === 0 ? (
          <div className="bg-orange-50 border border-orange-200 rounded-2xl p-6 text-center text-orange-800">
            Currently there are no dynamic promotions available. Check back later!
          </div>
        ) : (
          <Suspense fallback={
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-64 bg-gray-100 rounded-xl animate-pulse" />
              ))}
            </div>
          }>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
              {products
                .filter(p => (p.discountPercentage || 0) > 0)
                .slice(0, 10)
                .map((product) => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    onAddToCart={handleAddToCart}
                  />
                ))}
            </div>
          </Suspense>
        )}
      </section>

      {/* ── Products Section ── */}
      <section id="products-section">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-gray-800">{sectionTitle}</h2>
            {!loading && (
              <p className="text-sm text-gray-400 mt-1">
                {filteredProducts.length} products available
              </p>
            )}
          </div>
          {!loading && filteredProducts.length > 0 && (
            <div className="flex items-center gap-2">
              <label htmlFor="sort-by" className="text-sm text-gray-500 font-medium hidden sm:block">Sort by:</label>
              <select
                id="sort-by"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-white border border-gray-200 text-gray-700 text-sm rounded-lg focus:ring-emerald-500 focus:border-emerald-500 block p-2 outline-none"
              >
                <option value="default">Default</option>
                <option value="price_asc">Price: Low to High</option>
                <option value="price_desc">Price: High to Low</option>
                <option value="name_asc">Name: A-Z</option>
              </select>
            </div>
          )}
        </div>

        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="bg-white border border-gray-100 rounded-xl overflow-hidden animate-pulse">
                <div className="h-44 bg-gray-50" />
                <div className="p-3 space-y-2.5">
                  <div className="h-2.5 bg-gray-100 rounded w-1/3" />
                  <div className="h-3.5 bg-gray-100 rounded w-4/5" />
                  <div className="h-3 bg-gray-100 rounded w-1/2" />
                  <div className="flex justify-between items-center pt-1">
                    <div className="h-4 bg-gray-100 rounded w-1/3" />
                    <div className="h-9 w-9 bg-gray-100 rounded-xl" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="text-5xl mb-4">🔍</div>
            <h3 className="text-lg font-bold text-gray-800 mb-2">No products found</h3>
            <p className="text-sm text-gray-500 mb-4">
              Try selecting a different category or clear your filter.
            </p>
            <button
              onClick={() => { setSelectedRootId(null); setSelectedSubId(null); setExpandedRoot(null); }}
              className="text-emerald-600 font-semibold text-sm hover:text-emerald-700 transition-colors"
            >
              View All Products →
            </button>
          </div>
        ) : (
          <>
            <Suspense fallback={
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {Array.from({ length: 10 }).map((_, i) => (
                  <div key={i} className="h-64 bg-gray-100 rounded-xl animate-pulse" />
                ))}
              </div>
            }>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {displayedProducts.map((product) => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    onAddToCart={handleAddToCart}
                  />
                ))}
              </div>
            </Suspense>

            {hasMore && (
              <div className="flex justify-center mt-8">
                <button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className="bg-white border-2 border-gray-200 hover:border-emerald-500 text-gray-700 hover:text-emerald-600 font-semibold text-sm px-8 py-3 rounded-xl transition-all duration-200 disabled:opacity-50"
                >
                  {loadingMore ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                      Loading...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      View More Products
                      <ChevronRight className="w-4 h-4" />
                    </span>
                  )}
                </button>
              </div>
            )}

            {!hasMore && filteredProducts.length > PRODUCTS_PER_PAGE && (
              <p className="text-center text-sm text-gray-400 mt-6">
                You've reached the end — {filteredProducts.length} products total
              </p>
            )}
          </>
        )}
      </section>
    </div>
  );
}
