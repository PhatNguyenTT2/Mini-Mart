import React from 'react';

export const LogoSection = ({ isCollapsed }) => {
  const logoUrl = "https://cdn-icons-png.flaticon.com/512/427/427513.png";

  return (
    <div className="flex items-center justify-center py-2">
      <img
        src={logoUrl}
        alt="Nest Logo"
        className={`transition-all duration-300 ${isCollapsed ? 'h-8 w-8 object-contain' : 'h-10 w-auto'
          }`}
      />
    </div>
  );
};
