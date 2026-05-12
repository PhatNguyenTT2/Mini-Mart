import React from 'react';
import { useSidebar } from '../../contexts/SidebarContext';
import { LogoSection } from './sections/LogoSection';
import { NavigationMenuSection } from './sections/NavigationMenuSection';
import { UserProfileSection } from './sections/UserProfileSection';

export const Sidebar = () => {
  const { isCollapsed, toggleCollapse } = useSidebar();

  return (
    <div
      className={`bg-white flex flex-col h-full transition-all duration-100 ease-in-out ${isCollapsed ? 'w-20' : 'w-64'
        }`}
    >
      <div className="p-4 flex-shrink-0">
        <LogoSection isCollapsed={isCollapsed} />
      </div>
      <div className="px-4 py-2 flex-shrink-0">
        <UserProfileSection isCollapsed={isCollapsed} />
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-2 custom-scrollbar">
        <NavigationMenuSection isCollapsed={isCollapsed} toggleCollapse={toggleCollapse} />
      </div>
    </div>
  );
};

export default Sidebar;
