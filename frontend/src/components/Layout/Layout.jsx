import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { SidebarProvider } from '../../contexts/SidebarContext';
import { NotificationProvider } from '../../contexts/NotificationContext';
import { ChatProvider } from '../../contexts/ChatContext';
import { ToastContainer } from '../ToastNotification';
import { ChatWidget } from '../ChatWidget';
import { SidebarSection } from './sections/SidebarSection';
import { MainContentSection } from './sections/MainContentSection';

export const Layout = ({ children }) => {
  const navigate = useNavigate();

  useEffect(() => {
    const handleChatAction = (e) => {
      const action = e.detail;
      if (action && action.type === 'NAVIGATE' && action.payload && action.payload.path) {
        navigate(action.payload.path);
      }
    };
    window.addEventListener('posmart:chat_action', handleChatAction);
    return () => {
      window.removeEventListener('posmart:chat_action', handleChatAction);
    };
  }, [navigate]);

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
