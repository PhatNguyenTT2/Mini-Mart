import React from 'react';

/**
 * ProductListHeader Component
 * Hiển thị số lượng sản phẩm và các thông tin header
 */
export const ProductListHeader = ({ totalItems = 0, currentCount = 0, isLoading = false }) => {
  return (
    <div className="mb-6 pb-4 border-b border-gray-200">
      <h2 className="text-2xl font-bold text-gray-800">All Products</h2>
      <div className="text-sm text-gray-600 mt-1">
        {isLoading ? (
          <span className="inline-block w-32 h-4 bg-gray-200 rounded animate-pulse"></span>
        ) : (
          <>
            Showing <span className="font-semibold text-emerald-600">{currentCount}</span>
            {totalItems > 0 && (
              <>
                {' '}of <span className="font-semibold text-emerald-600">{totalItems}</span>
              </>
            )} products
          </>
        )}
      </div>
    </div>
  );
};
