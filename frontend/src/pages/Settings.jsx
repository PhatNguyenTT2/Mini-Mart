import React, { useState } from 'react';
import { Breadcrumb } from '../components/Breadcrumb';
import { Settings as SettingsIcon, Percent, Shield, Leaf, DollarSign } from 'lucide-react';
import {
  CustomerDiscountSettings,
  POSSecuritySettings,
  FreshProductPromotionSettings,
  ProductPriceSettings
} from '../components/Settings';

export const Settings = () => {
  const [activeTab, setActiveTab] = useState('discounts');

  const breadcrumbItems = [
    { label: 'Dashboard', link: '/dashboard' },
    { label: 'System Settings' }
  ];

  const tabs = [
    {
      id: 'discounts',
      label: 'Customer Discounts',
      icon: Percent,
      description: 'Configure default discount rates for customer types',
      component: CustomerDiscountSettings
    },
    {
      id: 'security',
      label: 'POS Security',
      icon: Shield,
      description: 'Configure POS PIN authentication settings',
      component: POSSecuritySettings
    },
    {
      id: 'fresh-promotion',
      label: 'Fresh Product Promotion',
      icon: Leaf,
      description: 'Auto-promotion for expiring fresh products',
      component: FreshProductPromotionSettings
    },
    {
      id: 'product-price',
      label: 'Product Price',
      icon: DollarSign,
      description: 'Manage product prices and view price history',
      component: ProductPriceSettings
    }
  ];

  const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb items={breadcrumbItems} />

      {/* Page Header */}
      <div className="bg-white p-6 rounded-lg shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-[20px] font-semibold font-['Poppins',sans-serif] text-[#212529] flex items-center gap-2">
              <SettingsIcon className="w-6 h-6" />
              System Settings
            </h1>
            <p className="text-[13px] text-gray-600 mt-1 font-['Poppins',sans-serif]">
              Configure system-wide settings and preferences
            </p>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow-sm overflow-hidden">
        {/* Tab Headers */}
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px" aria-label="Tabs">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                      group relative min-w-0 flex-1 overflow-hidden py-4 px-4 text-center text-sm font-medium
                      hover:bg-gray-50 focus:z-10 transition-colors
                      ${isActive
                      ? 'text-emerald-600 border-b-2 border-emerald-600'
                      : 'text-gray-500 hover:text-gray-700 border-b-2 border-transparent'
                    }
                    `}
                >
                  <div className="flex items-center justify-center gap-2">
                    <Icon className={`w-5 h-5 ${isActive ? 'text-emerald-600' : 'text-gray-400 group-hover:text-gray-500'}`} />
                    <span className="font-['Poppins',sans-serif] font-medium">{tab.label}</span>
                  </div>
                  {isActive && (
                    <p className="text-[11px] text-gray-500 mt-1 font-['Poppins',sans-serif]">
                      {tab.description}
                    </p>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {ActiveComponent && <ActiveComponent />}
        </div>
      </div>
    </div>
  );
};

export default Settings;
