import React from 'react';
import { Search } from 'lucide-react';
import { NotificationDropdown } from './NotificationDropdown';

export const SearchNotificationSection = () => {
  return (
    <div className="flex items-center space-x-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search..."
          className="pl-10 pr-4 py-2 rounded-lg bg-white border border-gray-200 focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
      </div>

      <div className="flex items-center space-x-4">
        <NotificationDropdown />
      </div>
    </div>
  );
};
