import React from 'react';
import { SidebarProvider } from '../../contexts/SidebarContext';
import { NotificationProvider } from '../../contexts/NotificationContext';
import { ChatProvider } from '../../contexts/ChatContext';
import { ToastContainer } from '../ToastNotification';
import { ChatWidget } from '../ChatWidget';
import { SidebarSection } from './sections/SidebarSection';
import { MainContentSection } from './sections/MainContentSection';

export const Layout = ({ children }) => {
  return (
    <SidebarProvider>
      <NotificationProvider>
        <ChatProvider>
          <div className="flex h-screen bg-gray-100 overflow-hidden">
            <SidebarSection />
            <MainContentSection>{children}</MainContentSection>
          </div>
          <ToastContainer />
          <ChatWidget />
        </ChatProvider>
      </NotificationProvider>
    </SidebarProvider>
  );
};
