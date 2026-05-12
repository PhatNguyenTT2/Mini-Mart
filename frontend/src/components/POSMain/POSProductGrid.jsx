import React from 'react';
import { ProductCard } from '../ViewProduct/ProductCard';

export const POSProductGrid = ({ products, loading, searchTerm, onProductClick }) => {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <svg className="animate-spin h-10 w-10 text-emerald-600 mx-auto mb-3" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-[14px] font-['Poppins',sans-serif] text-gray-600">
            Loading products...
          </p>
        </div>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" className="mx-auto mb-3 text-gray-300">
            <rect x="2" y="2" width="20" height="20" rx="2" stroke="currentColor" strokeWidth="2" />
            <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" />
            <path d="M2 17l5-5 3 3 7-7 5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <p className="text-gray-500 text-[15px] font-['Poppins',sans-serif]">
            {searchTerm ? 'No products found matching your search' : 'No products available'}
          </p>
        </div>
      </div>
    );
  }

  // Filter products: only show products that are on shelf (quantityOnShelf > 0)
  const productsOnShelf = products.filter(product => {
    const onShelfQuantity = product.inventory?.quantityOnShelf || 0;
    return onShelfQuantity > 0;
  });

  // Show message if all products are filtered out
  if (productsOnShelf.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" className="mx-auto mb-3 text-gray-300">
            <rect x="2" y="2" width="20" height="20" rx="2" stroke="currentColor" strokeWidth="2" />
            <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor" />
            <path d="M2 17l5-5 3 3 7-7 5 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <p className="text-gray-500 text-[15px] font-['Poppins',sans-serif]">
            No products available on shelf
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 pb-4">
      {productsOnShelf.map(product => (
        <ProductCard
          key={product.id}
          product={product}
          onClick={onProductClick}
          onAddToCart={onProductClick}
        />
      ))}
    </div>
  );
};
