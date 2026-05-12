import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Layout } from './Layout';

/**
 * ProtectedLayout - Shared layout wrapper for all protected routes
 * Uses React Router's Outlet to render nested route components
 * This prevents re-mounting of Sidebar/Header when navigating between pages
 * Includes page transition animation on route change
 */
export const ProtectedLayout = () => {
  const location = useLocation();

  return (
    <Layout>
      {/* Use location.pathname as key to trigger animation on route change */}
      <div
        key={location.pathname}
        className="animate-fade-in-smooth"
      >
        <Outlet />
      </div>
    </Layout>
  );
};
