import React from 'react';
import { Header } from '../../../Header';
import { Footer } from '../../../Footer';

export const MainContentSection = ({ children }) => {
  return (
    <div className="flex-1 flex flex-col min-h-0">
      <Header />
      <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-100">
        <div className="min-h-full flex flex-col">
          <div className="flex-1 p-6">
            {children}
          </div>
          <Footer />
        </div>
      </main>
    </div>
  );
};
