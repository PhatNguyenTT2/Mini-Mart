import React from 'react';
import { SearchNotificationSection } from './sections/SearchNotificationSection';
import { useTranslation } from 'react-i18next';

export const Header = () => {
  const { t, i18n } = useTranslation();

  return (
    <header className="bg-emerald-50 flex items-center justify-between px-6 py-4 flex-shrink-0">
      <div>
        <h1 className="text-2xl font-medium text-gray-800">{t('common.dashboard', 'Overview')}</h1>
      </div>

      <div className="flex items-center space-x-4">
        <SearchNotificationSection />

        <div className="flex items-center space-x-1 bg-white border border-gray-200 rounded-lg p-1 shadow-sm">
          <button
            onClick={() => i18n.changeLanguage('vi')}
            className={`text-xs font-semibold px-2 py-1 rounded transition-colors ${i18n.language?.startsWith('vi') ? 'bg-emerald-100 text-emerald-700' : 'text-gray-500 hover:bg-gray-100'}`}
          >
            VI
          </button>
          <button
            onClick={() => i18n.changeLanguage('en')}
            className={`text-xs font-semibold px-2 py-1 rounded transition-colors ${i18n.language?.startsWith('en') ? 'bg-emerald-100 text-emerald-700' : 'text-gray-500 hover:bg-gray-100'}`}
          >
            EN
          </button>
        </div>
      </div>
    </header>
  );
};
