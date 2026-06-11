import React, { useRef, useState } from 'react';

/**
 * POS Category Filter
 * Supports parent/subcategory hierarchy.
 * Parent = bold tab, subcategories = smaller pills below when parent selected.
 */
export const POSCategoryFilter = ({ categories, selectedCategory, onCategoryChange }) => {
  const scrollRef = useRef(null);
  const subScrollRef = useRef(null);

  const [isDown, setIsDown] = useState(false);
  const [startX, setStartX] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [hasMoved, setHasMoved] = useState(false);

  const [isSubDown, setIsSubDown] = useState(false);
  const [subStartX, setSubStartX] = useState(0);
  const [subScrollLeft, setSubScrollLeft] = useState(0);
  const [subHasMoved, setSubHasMoved] = useState(false);

  const handleMouseDown = (e) => {
    setIsDown(true);
    setHasMoved(false);
    setStartX(e.pageX - scrollRef.current.offsetLeft);
    setScrollLeft(scrollRef.current.scrollLeft);
  };

  const handleMouseLeave = () => {
    setIsDown(false);
  };

  const handleMouseUp = () => {
    setIsDown(false);
  };

  const handleMouseMove = (e) => {
    if (!isDown) return;
    e.preventDefault();
    const x = e.pageX - scrollRef.current.offsetLeft;
    const walk = (x - startX) * 1.5;
    if (Math.abs(x - startX) > 5) {
      setHasMoved(true);
    }
    scrollRef.current.scrollLeft = scrollLeft - walk;
  };

  const handleSubMouseDown = (e) => {
    setIsSubDown(true);
    setSubHasMoved(false);
    setSubStartX(e.pageX - subScrollRef.current.offsetLeft);
    setSubScrollLeft(subScrollRef.current.scrollLeft);
  };

  const handleSubMouseLeave = () => {
    setIsSubDown(false);
  };

  const handleSubMouseUp = () => {
    setIsSubDown(false);
  };

  const handleSubMouseMove = (e) => {
    if (!isSubDown) return;
    e.preventDefault();
    const x = e.pageX - subScrollRef.current.offsetLeft;
    const walk = (x - subStartX) * 1.5;
    if (Math.abs(x - subStartX) > 5) {
      setSubHasMoved(true);
    }
    subScrollRef.current.scrollLeft = subScrollLeft - walk;
  };

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
    <div className="space-y-2 select-none">
      <style dangerouslySetInnerHTML={{
        __html: `
        .pos-category-scroll::-webkit-scrollbar {
          height: 6px;
        }
        .pos-category-scroll::-webkit-scrollbar-track {
          background: #f1f1f1;
          border-radius: 4px;
        }
        .pos-category-scroll::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 4px;
        }
        .pos-category-scroll::-webkit-scrollbar-thumb:hover {
          background: #94a3b8;
        }
      `}} />

      {/* Main category tabs */}
      <div
        ref={scrollRef}
        onMouseDown={handleMouseDown}
        onMouseLeave={handleMouseLeave}
        onMouseUp={handleMouseUp}
        onMouseMove={handleMouseMove}
        className="pos-category-scroll flex gap-2 overflow-x-auto pb-2 cursor-grab active:cursor-grabbing"
      >
        {categories.map(category => {
          const isParentActive = category.id === selectedCategory ||
            category.children?.some(c => c.id === selectedCategory);

          return (
            <button
              key={category.id}
              type="button"
              onClick={() => {
                if (!hasMoved) {
                  onCategoryChange(category.id);
                }
              }}
              className={`px-4 py-2 rounded-lg font-['Poppins',sans-serif] text-[13px] font-medium whitespace-nowrap transition-all ${isParentActive
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
        <div
          ref={subScrollRef}
          onMouseDown={handleSubMouseDown}
          onMouseLeave={handleSubMouseLeave}
          onMouseUp={handleSubMouseUp}
          onMouseMove={handleSubMouseMove}
          className="pos-category-scroll flex gap-1.5 overflow-x-auto pb-2 pl-2 cursor-grab active:cursor-grabbing w-full max-w-full"
        >
          <button
            type="button"
            onClick={() => {
              if (!subHasMoved) {
                onCategoryChange(expandedParent.id);
              }
            }}
            className={`px-3 py-1 rounded-full text-[11px] font-medium whitespace-nowrap transition-all ${selectedCategory === expandedParent.id
              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
              : 'bg-gray-50 text-gray-500 hover:bg-gray-100 border border-gray-200'
              }`}
          >
            All {expandedParent.name}
          </button>
          {expandedParent.children.map(sub => (
            <button
              key={sub.id}
              type="button"
              onClick={() => {
                if (!subHasMoved) {
                  onCategoryChange(sub.id);
                }
              }}
              className={`px-3 py-1 rounded-full text-[11px] font-medium whitespace-nowrap transition-all ${selectedCategory === sub.id
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
