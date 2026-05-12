import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingCart, User, Search, X, LogOut, Store } from 'lucide-react';
import { useCart } from '../../../../contexts/CartContext';
import { useAuth } from '../../../../contexts/AuthContext';
import { useChat } from '../../../../contexts/ChatContext';
import productService from '../../../../services/productService';

export const SearchBarSection = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const searchTimerRef = useRef(null);
  const dropdownRef = useRef(null);
  const { getCartCount, setIsCartOpen } = useCart();
  // Removed unused selectedStore
  const { user, isLoggedIn, logout } = useAuth();
  const { setIsOpen, sendMessage } = useChat();
  const navigate = useNavigate();

  const formatVND = (amount) =>
    new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);

  useEffect(() => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);

    if (!searchQuery.trim() || searchQuery.trim().length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      return;
    }

    setShowDropdown(true);
    setIsSearching(true);

    searchTimerRef.current = setTimeout(async () => {
      try {
        const res = await productService.searchProducts(searchQuery.trim(), 5);
        setSearchResults(res.data?.products || []);
      } catch (err) {
        console.error('Search error', err);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(searchTimerRef.current);
  }, [searchQuery]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setShowDropdown(false);
      // Fallback navigate to home with query or just scroll
      navigate('/');
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="w-full bg-white border-b border-gray-100 py-4 px-4 lg:px-8">
      <div className="max-w-7xl mx-auto flex items-center gap-8">
        {/* Logo — no store name underneath */}
        <Link to="/" className="shrink-0 no-underline group">
          <span className="font-bold text-2xl text-gray-800 flex items-center gap-1.5">
            <Store className="w-8 h-8 text-emerald-600" /> <span className="text-emerald-600 group-hover:text-emerald-700 transition-colors">Mart</span>
          </span>
        </Link>

        {/* Centered Search Bar */}
        <div ref={dropdownRef} className="flex-1 max-w-2xl mx-auto relative">
          <form onSubmit={handleSearchSubmit}>
            <div className="flex items-center border-2 border-gray-200 rounded-xl overflow-hidden focus-within:border-emerald-500 transition-colors bg-gray-50 focus-within:bg-white">
              <label htmlFor="search-input" className="sr-only">Search products</label>
              <input
                id="search-input"
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search products..."
                className="flex-1 h-12 px-5 text-sm text-gray-700 placeholder-gray-400 bg-transparent border-none outline-none focus:ring-0 [&::-webkit-search-cancel-button]:hidden"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => { setSearchQuery(''); setShowDropdown(false); }}
                  className="p-2 text-gray-400 hover:text-gray-600 transition-colors bg-transparent border-none"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
              <button
                type="submit"
                className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-semibold px-6 h-12 transition-colors shrink-0"
              >
                <Search className="w-4 h-4" />
                <span className="hidden sm:inline">Search</span>
              </button>
            </div>
          </form>

          {/* Autocomplete Dropdown */}
          {showDropdown && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl shadow-xl border border-gray-100 overflow-hidden z-50">
              {isSearching ? (
                <div className="p-4 text-center text-sm text-gray-500">Searching...</div>
              ) : searchResults.length > 0 ? (
                <ul className="max-h-96 overflow-y-auto m-0 p-0 list-none">
                  {searchResults.map((product) => (
                    <li key={product.id} className="border-b border-gray-50 last:border-0">
                      <button
                        type="button"
                        onClick={() => {
                          setShowDropdown(false);
                          setSearchQuery('');
                          navigate(`/product/${product.id}`);
                        }}
                        className="w-full text-left flex items-center gap-3 p-3 hover:bg-emerald-50 transition-colors border-none bg-transparent"
                      >
                        {product.image ? (
                          <img src={product.image} alt={product.name} className="w-10 h-10 object-cover rounded" />
                        ) : (
                          <div className="w-10 h-10 bg-gray-100 rounded flex items-center justify-center">
                            <span className="text-[10px] text-gray-400">No Img</span>
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                          <h4 className="text-sm font-medium text-gray-800 truncate m-0 leading-tight">{product.name}</h4>
                          <span className="text-xs text-emerald-600 font-bold">{formatVND(product.unitPrice)}</span>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="p-6 text-center bg-gray-50">
                  <p className="text-sm text-gray-600 mb-3">No matching products found.</p>
                  <button
                    type="button"
                    onClick={() => {
                      setShowDropdown(false);
                      setIsOpen(true);
                      sendMessage(`I am looking for: ${searchQuery}. Can you give me some suggestions?`);
                    }}
                    className="text-sm bg-emerald-100 text-emerald-700 px-4 py-2 rounded-lg font-medium hover:bg-emerald-200 transition-colors inline-flex items-center gap-2 border-none cursor-pointer"
                  >
                    <Search className="w-4 h-4" />
                    Need something else? Let AI Assistant suggest for you
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Cart + Account */}
        <nav className="flex items-center gap-5 shrink-0" aria-label="Quick actions">
          {isLoggedIn && (
            <Link to="/orders" className="flex items-center gap-2 no-underline group" aria-label="Orders">
              <div className="relative">
                <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5 text-gray-600 group-hover:text-emerald-600 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                </svg>
              </div>
              <span className="hidden md:block text-sm text-gray-600 group-hover:text-emerald-600 transition-colors font-medium">
                Orders
              </span>
            </Link>
          )}

          <button 
            type="button"
            onClick={() => setIsCartOpen(true)} 
            className="flex items-center gap-2 bg-transparent border-none cursor-pointer group" 
            aria-label="Cart"
          >
            <div className="relative">
              <ShoppingCart className="w-5 h-5 text-gray-600 group-hover:text-emerald-600 transition-colors" />
              {getCartCount() > 0 && (
                <span className="absolute -top-2 -right-2 bg-emerald-500 text-white text-[10px] font-bold min-w-[18px] h-[18px] flex items-center justify-center rounded-full px-1">
                  {getCartCount()}
                </span>
              )}
            </div>
            <span className="hidden md:block text-sm text-gray-600 group-hover:text-emerald-600 transition-colors font-medium">
              Cart
            </span>
          </button>

          {isLoggedIn ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-emerald-100 text-emerald-700 rounded-full flex items-center justify-center text-sm font-bold">
                  {(user?.fullName || user?.username || 'U').charAt(0).toUpperCase()}
                </div>
                <span className="hidden md:block text-sm text-gray-700 font-medium max-w-[120px] truncate">
                  {user?.fullName || user?.username}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1 text-gray-400 hover:text-red-500 transition-colors bg-transparent border-none cursor-pointer p-1"
                title="Logout"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <Link to="/login" className="flex items-center gap-2 no-underline group" aria-label="Account">
              <User className="w-5 h-5 text-gray-500 group-hover:text-emerald-600 transition-colors" />
              <span className="hidden md:block text-sm text-gray-600 group-hover:text-emerald-600 transition-colors font-medium">
                Login
              </span>
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
};

