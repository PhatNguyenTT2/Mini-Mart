import React from 'react';
import { SearchNotificationSection } from './sections/SearchNotificationSection';

export const Header = () => {
  return (
    <header className="bg-emerald-50 flex items-center justify-between px-6 py-4 flex-shrink-0">
      <div>
        <h1 className="text-2xl font-medium text-gray-800">Overview</h1>
      </div>

      <div className="flex items-center space-x-4">
        <SearchNotificationSection />
      </div>
    </header>
  );
};
