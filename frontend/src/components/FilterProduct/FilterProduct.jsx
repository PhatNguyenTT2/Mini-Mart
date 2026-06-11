import React, { useState, useEffect } from 'react';
import { Filter, X } from 'lucide-react';
import categoryService from '../../services/categoryService';
import { useTranslation } from 'react-i18next';

export const FilterProduct = ({ onFilterChange, currentFilters = {} }) => {
  const { t } = useTranslation();
  // Helper function to format VND currency
  const formatVND = (amount) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND'
    }).format(amount);
  };

  const [categoryTree, setCategoryTree] = useState([]);
  const [loadingCategories, setLoadingCategories] = useState(true);
  const [selectedCategories, setSelectedCategories] = useState(currentFilters.categories || []);
  const [expandedParents, setExpandedParents] = useState({});
  const [priceRange, setPriceRange] = useState([
    currentFilters.minPrice || 0,
    currentFilters.maxPrice || 1000000
  ]);
  const [onlyDiscounted, setOnlyDiscounted] = useState(currentFilters.onlyDiscounted || false);
  const [isDragging, setIsDragging] = useState(null); // null | 'min' | 'max'

  // Fetch category tree from API
  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const result = await categoryService.getCategoryTree();
        if (result.success && result.data?.categories) {
          setCategoryTree(result.data.categories);
          // Default: all parents collapsed
          setExpandedParents({});
        }
      } catch (error) {
        console.error('Failed to fetch categories:', error);
      } finally {
        setLoadingCategories(false);
      }
    };

    fetchCategories();
  }, []);

  const handleCategoryClick = (categoryId) => {
    if (categoryId === null) {
      // Click "All Products" - clear all categories
      setSelectedCategories([]);
    } else {
      // Toggle category selection
      setSelectedCategories(prev => {
        if (prev.includes(categoryId)) {
          return prev.filter(id => id !== categoryId);
        } else {
          return [...prev, categoryId];
        }
      });
    }
  };

  // Toggle parent expand/collapse
  const toggleParentExpand = (parentId) => {
    setExpandedParents(prev => ({ ...prev, [parentId]: !prev[parentId] }));
  };

  // Select/deselect an entire parent + all its children
  const handleParentClick = (parent) => {
    const childIds = (parent.children || []).map(c => c.id);
    const allIds = [parent.id, ...childIds];
    const allSelected = allIds.every(id => selectedCategories.includes(id));

    if (allSelected) {
      setSelectedCategories(prev => prev.filter(id => !allIds.includes(id)));
    } else {
      setSelectedCategories(prev => [...new Set([...prev, ...allIds])]);
    }
  };

  // Flatten categoryTree for lookup by id
  const allCategories = React.useMemo(() => {
    const flat = [];
    categoryTree.forEach(root => {
      flat.push(root);
      (root.children || []).forEach(child => flat.push(child));
    });
    return flat;
  }, [categoryTree]);

  // Auto-apply filters whenever selectedCategories, priceRange, or onlyDiscounted changes
  useEffect(() => {
    if (onFilterChange) {
      const filterParams = {
        categories: selectedCategories,
        minPrice: priceRange[0] !== 0 ? priceRange[0] : null,
        maxPrice: priceRange[1] !== 1000000 ? priceRange[1] : null,
        onlyDiscounted: onlyDiscounted
      };

      onFilterChange(filterParams);
    }
  }, [selectedCategories, priceRange, onlyDiscounted]);

  // Clear all filters
  const handleClearFilters = () => {
    setSelectedCategories([]);
    setPriceRange([0, 1000000]);
    setOnlyDiscounted(false);
  };

  const handleMouseDown = (type) => {
    setIsDragging(type);
  };

  const handleMouseUp = () => {
    setIsDragging(null);
  };

  // Add global mouse event listeners for price slider
  React.useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isDragging) return;

      const slider = document.querySelector('.price-slider-track');
      if (!slider) return;

      const rect = slider.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));
      const value = Math.round((percentage / 100) * 1000000);

      setPriceRange(prev => {
        if (isDragging === 'min') {
          return [Math.min(value, prev[1] - 10000), prev[1]];
        } else {
          return [prev[0], Math.max(value, prev[0] + 10000)];
        }
      });
    };

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'grabbing';
      document.body.style.userSelect = 'none';

      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };
    }
  }, [isDragging]);

  // Check if any filters are active
  const hasActiveFilters = selectedCategories.length > 0 ||
    priceRange[0] !== 0 ||
    priceRange[1] !== 1000000 ||
    onlyDiscounted;

  return (
    <div className="w-72 space-y-4 overflow-y-auto h-full">
      {/* Promotion Filter Toggle Section */}
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-gray-800">{t('products.only_promoted', 'Only Promoted Items')}</span>
          <button
            type="button"
            onClick={() => setOnlyDiscounted(!onlyDiscounted)}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${onlyDiscounted ? 'bg-emerald-500' : 'bg-gray-200'
              }`}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${onlyDiscounted ? 'translate-x-5' : 'translate-x-0'
                }`}
            />
          </button>
        </div>
      </div>
      {/* Filter Header with Clear Button */}
      {hasActiveFilters && (
        <div className="bg-white border border-gray-200 rounded-xl p-3">
          <button
            onClick={handleClearFilters}
            className="w-full flex items-center justify-center gap-2 text-red-600 hover:text-red-700 transition-colors"
          >
            <X className="w-4 h-4" />
            <span className="text-sm font-semibold">{t('products.clear_all_filters', 'Clear All Filters')}</span>
          </button>
        </div>
      )}

      {/* Category Section */}
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        {/* Header */}
        <div className="border-b border-gray-200 pb-2 mb-4">
          <h3 className="text-lg font-bold text-gray-800">{t('products.category', 'Category')}</h3>
          <div className="w-16 h-0.5 bg-emerald-400 mt-1.5"></div>
        </div>

        {/* Loading State */}
        {loadingCategories ? (
          <div className="text-center py-4">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-emerald-500"></div>
            <p className="text-xs text-gray-500 mt-2">{t('products.loading_categories', 'Loading categories...')}</p>
          </div>
        ) : (
          <>
            {/* "All" Option */}
            <button
              onClick={() => handleCategoryClick(null)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded border transition-all mb-2 ${selectedCategories.length === 0
                ? 'border-emerald-500 bg-emerald-50'
                : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
                }`}
            >
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 flex items-center justify-center bg-emerald-100 rounded">
                  <Filter className="w-4 h-4 text-emerald-600" />
                </div>
                <span className="text-xs text-gray-800 font-semibold">{t('products.all_products', 'All Products')}</span>
              </div>
            </button>

            {/* Category Tree from API */}
            <div className="space-y-1">
              {categoryTree.map((parent) => {
                const childIds = (parent.children || []).map(c => c.id);
                const allIds = [parent.id, ...childIds];
                const allSelected = allIds.length > 0 && allIds.every(id => selectedCategories.includes(id));
                const someSelected = allIds.some(id => selectedCategories.includes(id));
                const isExpanded = expandedParents[parent.id];

                return (
                  <div key={parent.id}>
                    {/* Parent Category Row */}
                    <div className="flex items-center gap-1">
                      {/* Expand/collapse toggle */}
                      {parent.children && parent.children.length > 0 && (
                        <button
                          onClick={() => toggleParentExpand(parent.id)}
                          className="w-5 h-5 flex items-center justify-center text-gray-400 hover:text-gray-600 flex-shrink-0"
                        >
                          <svg width="10" height="10" viewBox="0 0 10 10" fill="none" xmlns="http://www.w3.org/2000/svg" className={`transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                            <path d="M3 1L7 5L3 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </button>
                      )}
                      {(!parent.children || parent.children.length === 0) && <div className="w-5 flex-shrink-0" />}

                      {/* Parent button */}
                      <button
                        onClick={() => handleParentClick(parent)}
                        className={`flex-1 flex items-center justify-between px-2 py-1.5 rounded border transition-all ${allSelected
                          ? 'border-emerald-500 bg-emerald-50'
                          : someSelected
                            ? 'border-emerald-300 bg-emerald-50/50'
                            : 'border-gray-200 hover:border-emerald-300 hover:bg-gray-50'
                          }`}
                      >
                        <div className="flex items-center gap-2">
                          {parent.image ? (
                            <img
                              src={parent.image}
                              alt={parent.name}
                              className="w-7 h-7 object-cover rounded flex-shrink-0"
                              onError={(e) => { e.target.style.display = 'none'; }}
                            />
                          ) : (
                            <div className="w-7 h-7 bg-gray-100 rounded flex items-center justify-center flex-shrink-0">
                              <span className="text-[10px] text-gray-400">--</span>
                            </div>
                          )}
                          <span className="text-xs text-gray-800 font-semibold">{parent.name}</span>
                        </div>
                        <div className="bg-emerald-200 rounded-full min-w-[20px] h-5 flex items-center justify-center px-1.5">
                          <span className="text-[10px] text-gray-800 font-medium">{parent.productCount || 0}</span>
                        </div>
                      </button>
                    </div>

                    {/* Children (subcategories) */}
                    {isExpanded && parent.children && parent.children.length > 0 && (
                      <div className="ml-5 mt-1 space-y-1">
                        {parent.children.map(child => (
                          <button
                            key={child.id}
                            onClick={() => handleCategoryClick(child.id)}
                            className={`w-full flex items-center justify-between px-2 py-1.5 rounded border transition-all ${selectedCategories.includes(child.id)
                              ? 'border-emerald-500 bg-emerald-50'
                              : 'border-gray-100 hover:border-emerald-300 hover:bg-gray-50'
                              }`}
                          >
                            <span className="text-[11px] text-gray-600">{child.name}</span>
                            <div className="bg-gray-200 rounded-full min-w-[18px] h-4 flex items-center justify-center px-1">
                              <span className="text-[9px] text-gray-700 font-medium">{child.productCount || 0}</span>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </div>

      {/* Filter by Price Section */}
      <div className="bg-white border border-gray-200 rounded-xl p-4 relative overflow-hidden">
        {/* Decorative image in bottom right */}
        <div className="absolute bottom-0 right-0 w-16 h-16 opacity-10 pointer-events-none">
          <div className="text-4xl">$</div>
        </div>

        {/* Header */}
        <div className="border-b border-gray-200 pb-2 mb-4 relative z-10">
          <h3 className="text-lg font-bold text-gray-800">{t('products.filter_by_price', 'Filter by Price')}</h3>
          <div className="w-16 h-0.5 bg-emerald-400 mt-1.5"></div>
        </div>

        {/* Price Range Slider */}
        <div className="mb-4 relative z-10">
          <div className="flex justify-between mb-3 text-xs">
            <span className="text-gray-500">
              {t('products.price_from', 'Từ')}: <span className="text-emerald-600 font-semibold">{formatVND(priceRange[0])}</span>
            </span>
            <span className="text-gray-500">
              {t('products.price_to', 'Đến')}: <span className="text-emerald-600 font-semibold">{formatVND(priceRange[1])}</span>
            </span>
          </div>

          {/* Slider Track */}
          <div className="relative h-1 mb-6">
            <div
              className="price-slider-track absolute inset-0 bg-gray-300 rounded cursor-pointer"
              onMouseDown={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const percentage = (x / rect.width) * 100;
                const clickValue = Math.round((percentage / 100) * 1000000);

                const distToMin = Math.abs(clickValue - priceRange[0]);
                const distToMax = Math.abs(clickValue - priceRange[1]);

                if (distToMin < distToMax) {
                  setPriceRange([Math.min(clickValue, priceRange[1] - 10000), priceRange[1]]);
                  handleMouseDown('min');
                } else {
                  setPriceRange([priceRange[0], Math.max(clickValue, priceRange[0] + 10000)]);
                  handleMouseDown('max');
                }
              }}
            >
              {/* Active range */}
              <div
                className="absolute h-1 bg-emerald-500 rounded"
                style={{
                  left: `${(priceRange[0] / 1000000) * 100}%`,
                  right: `${100 - (priceRange[1] / 1000000) * 100}%`
                }}
              />

              {/* Min thumb */}
              <div
                className="absolute w-4 h-4 bg-emerald-500 rounded-full -top-1.5 transform -translate-x-1/2 cursor-grab active:cursor-grabbing z-10"
                style={{ left: `${(priceRange[0] / 1000000) * 100}%` }}
                onMouseDown={(e) => {
                  e.stopPropagation();
                  handleMouseDown('min');
                }}
              />

              {/* Max thumb */}
              <div
                className="absolute w-4 h-4 bg-emerald-500 rounded-full -top-1.5 transform -translate-x-1/2 cursor-grab active:cursor-grabbing z-10"
                style={{ left: `${(priceRange[1] / 1000000) * 100}%` }}
                onMouseDown={(e) => {
                  e.stopPropagation();
                  handleMouseDown('max');
                }}
              />
            </div>
          </div>
        </div>

        {/* Filter Actions - Auto-applied, only show clear */}
        {hasActiveFilters && (
          <div className="flex gap-2 relative z-10">
            <button
              onClick={handleClearFilters}
              className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-700 font-bold py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              <X className="w-4 h-4" />
              <span className="text-xs tracking-wider">{t('products.clear_filters_btn', 'CLEAR FILTERS')}</span>
            </button>
          </div>
        )}
      </div>

      {/* Active Filters Display */}
      {hasActiveFilters && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <h4 className="text-sm font-bold text-gray-800 mb-3">{t('products.active_filters', 'Active Filters')} ({selectedCategories.length + (priceRange[0] !== 0 || priceRange[1] !== 1000000 ? 1 : 0)})</h4>
          <div className="space-y-2">
            {selectedCategories.map(catId => {
              const cat = allCategories.find(c => c.id === catId);
              return cat ? (
                <div key={catId} className="flex items-center justify-between bg-emerald-50 px-3 py-1.5 rounded">
                  <span className="text-xs text-emerald-700">
                    {cat.name}
                  </span>
                  <button
                    onClick={() => handleCategoryClick(catId)}
                    className="text-emerald-700 hover:text-emerald-900"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : null;
            })}
            {(priceRange[0] !== 0 || priceRange[1] !== 1000000) && (
              <div className="flex items-center justify-between bg-emerald-50 px-3 py-1.5 rounded">
                <span className="text-xs text-emerald-700">
                  {formatVND(priceRange[0])} - {formatVND(priceRange[1])}
                </span>
                <button
                  onClick={() => setPriceRange([0, 1000000])}
                  className="text-emerald-700 hover:text-emerald-900"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}
            {onlyDiscounted && (
              <div className="flex items-center justify-between bg-emerald-50 px-3 py-1.5 rounded">
                <span className="text-xs text-emerald-700">
                  {t('products.only_promoted_label', 'Only Promoted')}
                </span>
                <button
                  onClick={() => setOnlyDiscounted(false)}
                  className="text-emerald-700 hover:text-emerald-900"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
