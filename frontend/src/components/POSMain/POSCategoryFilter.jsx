import React from 'react';

/**
 * POS Category Filter
 * Supports parent/subcategory hierarchy.
 * Parent = bold tab, subcategories = smaller pills below when parent selected.
 */
export const POSCategoryFilter = ({ categories, selectedCategory, onCategoryChange }) => {
  // Find if current selection is a subcategory
  const getParentOfSelected = () => {
    for (const cat of categories) {
      if (cat.children?.some(child => child.id === selectedCategory)) {
        return cat.id;
      }
    }
    return null;
  };

  const activeParentId = getParentOfSelected();
  // Show subcategories if a parent with children is selected, or a child of that parent
  const expandedParent = categories.find(cat =>
    cat.id === selectedCategory && cat.children?.length > 0
  ) || (activeParentId ? categories.find(c => c.id === activeParentId) : null);

  return (
    <div className="space-y-2">
      {/* Main category tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
        {categories.map(category => {
          const isParentActive = category.id === selectedCategory ||
            category.children?.some(c => c.id === selectedCategory);

          return (
            <button
              key={category.id}
              onClick={() => onCategoryChange(category.id)}
              className={`px-4 py-2 rounded-lg font-['Poppins',sans-serif] text-[13px] font-medium whitespace-nowrap transition-all ${
                isParentActive
                  ? 'bg-emerald-600 text-white shadow-md'
                  : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              {category.name}
              {category.productCount > 0 && (
                <span className={`ml-1.5 text-[11px] ${isParentActive ? 'text-emerald-200' : 'text-gray-400'}`}>
                  ({category.productCount})
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Subcategory pills (when parent with children is selected) */}
      {expandedParent && expandedParent.children?.length > 0 && (
        <div className="flex gap-1.5 overflow-x-auto pb-1 pl-2">
          <button
            onClick={() => onCategoryChange(expandedParent.id)}
            className={`px-3 py-1 rounded-full text-[11px] font-medium whitespace-nowrap transition-all ${
              selectedCategory === expandedParent.id
                ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                : 'bg-gray-50 text-gray-500 hover:bg-gray-100 border border-gray-200'
            }`}
          >
            All {expandedParent.name}
          </button>
          {expandedParent.children.map(sub => (
            <button
              key={sub.id}
              onClick={() => onCategoryChange(sub.id)}
              className={`px-3 py-1 rounded-full text-[11px] font-medium whitespace-nowrap transition-all ${
                selectedCategory === sub.id
                  ? 'bg-emerald-500 text-white'
                  : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'
              }`}
            >
              {sub.name}
              {sub.productCount > 0 && (
                <span className={`ml-1 ${selectedCategory === sub.id ? 'text-emerald-200' : 'text-gray-400'}`}>
                  ({sub.productCount})
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
