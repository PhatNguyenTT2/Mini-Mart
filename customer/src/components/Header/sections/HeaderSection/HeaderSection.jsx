import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, Phone, Store } from 'lucide-react';
import { useStore } from '../../../../contexts/StoreContext';

export const HeaderSection = () => {
  const { stores, selectedStore, selectStore } = useStore();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const navigationItems = [
    { label: 'Home', to: '/' },
    { label: 'Promotions', to: '/#promotions', anchor: true },
    { label: 'New Arrivals', to: '/#new-arrivals', anchor: true },
    { label: 'Login', to: '/login' },
  ];

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
                    <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Switch Store</span>
                  </div>
                  {stores.map((store) => (
                    <button
                      key={store.id}
                      onClick={() => {
                        selectStore(store);
                        setIsDropdownOpen(false);
                      }}
                      className={`w-full text-left px-4 py-2.5 text-sm transition-colors flex items-center gap-2 ${
                        selectedStore.id === store.id
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

        {/* Hotline */}
        <div className="hidden sm:flex items-center gap-2">
          <Phone className="w-4 h-4 text-emerald-500" />
          <a href="tel:1900888123" className="font-bold text-emerald-600 text-base no-underline">
            1900-888-123
          </a>
          <span className="text-xs text-gray-400">24/7 Support</span>
        </div>
      </nav>
    </header>
  );
};
