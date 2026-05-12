import { useState } from 'react';
import { CategoryFilter } from './sections/CategoryFilter';
import { ProductGridSection } from './sections/ProductGridSection';

export const Product = () => {
  const [selectedCategories, setSelectedCategories] = useState([]);

  return (
    <div className="flex gap-6">
      {/* Sidebar — Category Filter */}
      <aside className="w-72 shrink-0 hidden lg:block">
        <CategoryFilter
          onFilterChange={setSelectedCategories}
          selectedCategories={selectedCategories}
        />
      </aside>

      {/* Main — Product Grid */}
      <main className="flex-1 min-w-0">
        <ProductGridSection selectedCategories={selectedCategories} />
      </main>
    </div>
  );
};
