import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, Phone, Store } from 'lucide-react';
import { useStore } from '../../../../contexts/StoreContext';
import { useAuth } from '../../../../contexts/AuthContext';
import { useTranslation } from 'react-i18next';

export const HeaderSection = () => {
  const { t, i18n } = useTranslation();
  const { stores, selectedStore, selectStore } = useStore();
  const { isLoggedIn } = useAuth();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const navigationItems = [
    { label: t('common.home', 'Home'), to: '/' },
    { label: t('common.promotions', 'Promotions'), to: '/#promotions', anchor: true },
  ];

  if (!isLoggedIn) {
    navigationItems.push({ label: t('common.login', 'Login'), to: '/login' });
  }

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <header className="w-full bg-white border-b border-gray-100 px-4 lg:px-8">
      <nav className="max-w-7xl mx-auto flex items-center justify-between h-12" aria-label="Main navigation">
        <div className="flex items-center gap-1">
          {/* Store Dropdown — placed left, no "All Categories" button */}
          {selectedStore && (
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="flex items-center gap-1.5 bg-emerald-500 hover:bg-emerald-600 text-white font-semibold text-sm px-4 rounded-lg transition-colors h-9"
              >
                <Store className="w-3.5 h-3.5" />
                <span className="max-w-[160px] truncate">{selectedStore.name}</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              {isDropdownOpen && (
                <div className="absolute top-full left-0 mt-1 w-64 bg-white border border-gray-200 rounded-xl shadow-lg z-50 py-1 max-h-64 overflow-y-auto">
                  <div className="px-4 py-2 border-b border-gray-100">
                    <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{t('store.switch', 'Switch Store')}</span>
                  </div>
                  {stores.map((store) => (
                    <button
                      key={store.id}
                      onClick={() => {
                        selectStore(store);
                        setIsDropdownOpen(false);
                      }}
                      className={`w-full text-left px-4 py-2.5 text-sm transition-colors flex items-center gap-2 ${selectedStore.id === store.id
                        ? 'bg-emerald-50 text-emerald-700 font-medium'
                        : 'text-gray-700 hover:bg-gray-50'
                        }`}
                    >
                      <Store className="w-3.5 h-3.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <span className="block truncate">{store.name}</span>
                        {store.address && (
                          <span className="block text-xs text-gray-400 truncate">{store.address}</span>
                        )}
                      </div>
                      {selectedStore.id === store.id && (
                        <span className="text-emerald-500 text-xs font-bold">✓</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Nav Links */}
          <ul className="hidden md:flex items-center gap-0 list-none p-0 m-0 ml-2">
            {navigationItems.map((item) => (
              <li key={item.label}>
                {item.anchor ? (
                  <a
                    href={item.to}
                    className="font-medium text-sm text-gray-600 hover:text-emerald-600 transition-colors px-3 leading-[48px] no-underline"
                  >
                    {item.label}
                  </a>
                ) : (
                  <Link
                    to={item.to}
                    className="font-medium text-sm text-gray-600 hover:text-emerald-600 transition-colors px-3 leading-[48px] no-underline"
                  >
                    {item.label}
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </div>

        {/* Hotline & Language */}
        <div className="hidden sm:flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Phone className="w-4 h-4 text-emerald-500" />
            <a href="tel:1900888123" className="font-bold text-emerald-600 text-base no-underline">
              1900-888-123
            </a>
            <span className="text-xs text-gray-400">24/7 Support</span>
          </div>

          <div className="flex items-center gap-1 border-l border-gray-200 pl-3">
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
      </nav>
    </header>
  );
};
