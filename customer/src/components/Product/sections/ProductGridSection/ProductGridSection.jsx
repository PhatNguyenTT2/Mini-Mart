import { useState, useEffect } from 'react';
import { ProductCard } from '../../ProductCard.jsx';
import { useCart } from '../../../../contexts/CartContext';
import productService from '../../../../services/productService';

export const ProductGridSection = ({ selectedCategories = [] }) => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { addToCart } = useCart();

  useEffect(() => {
    const fetchProducts = async () => {
      setLoading(true);
      setError(null);
      try {
        let result;
        if (selectedCategories.length === 1) {
          result = await productService.getActiveProducts({
            categoryId: selectedCategories[0]
          });
        } else {
          result = await productService.getActiveProducts();
        }

        let productList = result?.data?.products || [];

        // Client-side multi-category filter (API only supports single categoryId)
        if (selectedCategories.length > 1) {
          productList = productList.filter(p =>
            selectedCategories.includes(p.categoryId) ||
            selectedCategories.includes(p.category?.id)
          );
        }

        setProducts(productList);
      } catch (err) {
        console.error('Failed to fetch products:', err);
        setError('Failed to load products. Please try again.');
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, [selectedCategories]);

  const handleAddToCart = (product) => {
    const cartItem = {
      id: product.id,
      name: product.name,
      image: product.image,
      price: product.discountPercentage > 0
        ? product.unitPrice * (1 - product.discountPercentage / 100)
        : product.unitPrice,
      originalPrice: product.unitPrice,
      category: product.category?.name || 'Uncategorized',
    };
    addToCart(cartItem);
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="bg-white border border-gray-200 rounded-lg overflow-hidden animate-pulse">
            <div className="h-48 bg-gray-100" />
            <div className="p-4 space-y-3">
              <div className="h-3 bg-gray-100 rounded w-1/3" />
              <div className="h-4 bg-gray-100 rounded w-3/4" />
              <div className="h-4 bg-gray-100 rounded w-1/2" />
              <div className="flex justify-between items-center">
                <div className="h-5 bg-gray-100 rounded w-1/3" />
                <div className="h-8 w-8 bg-gray-100 rounded-full" />
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="text-4xl mb-4">⚠️</div>
        <h3 className="text-lg font-bold text-gray-800 mb-2">Something went wrong</h3>
        <p className="text-sm text-gray-500 mb-4">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="bg-emerald-500 hover:bg-emerald-600 text-white font-semibold text-sm px-5 py-2 rounded-lg transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  // Empty state
  if (products.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="text-4xl mb-4">🔍</div>
        <h3 className="text-lg font-bold text-gray-800 mb-2">No products found</h3>
        <p className="text-sm text-gray-500">
          No products match the current filters. Try selecting a different category.
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Results count */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">
          Showing <span className="font-semibold text-gray-700">{products.length}</span> products
        </p>
      </div>

      {/* Product Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
        {products.map((product) => (
          <ProductCard
            key={product.id}
            product={product}
            onAddToCart={handleAddToCart}
          />
        ))}
      </div>
    </div>
  );
};
