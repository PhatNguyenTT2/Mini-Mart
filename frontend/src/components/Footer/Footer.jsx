import React from 'react';
import { CopyrightSection } from './sections/CopyrightSection';
import { LinksSection } from './sections/LinksSection';

export const Footer = () => {
  return (
    <footer className="bg-white border-t border-gray-200">
      <div className="mx-auto flex max-w-full items-center justify-between px-6 py-3 text-sm">
        <CopyrightSection />
        <LinksSection />
      </div>
    </footer>
  );
};
