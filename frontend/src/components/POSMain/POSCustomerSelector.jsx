import React, { useState, useEffect, useRef } from 'react';
import { Search, User, UserPlus, X } from 'lucide-react';
import posDataService from '../../services/posDataService';
import { POSAddCustomerModal } from './POSAddCustomerModal';

/**
 * POSCustomerSelector Component
 * Handles customer selection for POS orders
 * 
 * Features:
 * - Auto-load default guest customer
 * - Search customers by name/phone
 * - Quick select guest customer
 * - Create new customer inline
 * - Display customer type and discount
 */
export const POSCustomerSelector = ({ selectedCustomer, onCustomerChange, customerDiscounts }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [guestCustomer, setGuestCustomer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showNewCustomerModal, setShowNewCustomerModal] = useState(false);
  const searchInputRef = useRef(null);

  // Load default guest customer on mount
  useEffect(() => {
    const loadGuestCustomer = async () => {
      try {
        const response = await posDataService.getDefaultGuest();
        const guest = response.data.customer;
        setGuestCustomer(guest);

        // Auto-select guest if no customer selected
        if (!selectedCustomer) {
          onCustomerChange(guest);
        }
      } catch (error) {
        console.error('Error loading guest customer:', error);
      }
    };

    loadGuestCustomer();
  }, []);

  // Search customers with debounce
  useEffect(() => {
    if (!searchTerm.trim()) {
      setSearchResults([]);
      setShowSearchDropdown(false);
      return;
    }

    const delaySearch = setTimeout(async () => {
      try {
        setLoading(true);
        const response = await posDataService.searchCustomers(searchTerm.trim(), 10);
        const customers = response.data?.customers || [];

        // Filter out guest customers from search results (they are walk-in, no need to search)
        const filteredCustomers = customers.filter(c => c.customerType !== 'guest');
        setSearchResults(filteredCustomers);
        setShowSearchDropdown(true);
      } catch (error) {
        console.error('Error searching customers:', error);
        setSearchResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(delaySearch);
  }, [searchTerm]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchInputRef.current && !searchInputRef.current.contains(event.target)) {
        setShowSearchDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectCustomer = (customer) => {
    onCustomerChange(customer);
    setSearchTerm('');
    setShowSearchDropdown(false);
    searchInputRef.current?.blur();
  };

  const handleSelectGuest = () => {
    if (guestCustomer) {
      onCustomerChange(guestCustomer);
      setSearchTerm('');
      setShowSearchDropdown(false);
    }
  };

  const handleClearCustomer = () => {
    if (guestCustomer) {
      onCustomerChange(guestCustomer);
    }
  };

  // Handle customer creation success
  const handleCustomerCreated = async () => {
    // Reload guest customer to refresh state
    try {
      const response = await posDataService.getDefaultGuest();
      const guest = response.data.customer;
      setGuestCustomer(guest);
    } catch (error) {
      console.error('Error reloading guest customer:', error);
    }
  };

  const getDiscountPercentage = (customerType) => {
    if (!customerDiscounts) {
      const defaultDiscounts = {
        guest: 0,
        retail: 10,
        wholesale: 15,
        vip: 20
      };
      return defaultDiscounts[customerType] || 0;
    }
    return customerDiscounts[customerType] || 0;
  };

  const getCustomerTypeLabel = (type) => {
    const labels = {
      guest: 'Guest',
      retail: 'Retail',
      wholesale: 'Wholesale',
      vip: 'VIP'
    };
    return labels[type] || type;
  };

  const getCustomerTypeBadgeColor = (type) => {
    const colors = {
      guest: 'bg-gray-100 text-gray-700',
      retail: 'bg-blue-100 text-blue-700',
      wholesale: 'bg-purple-100 text-purple-700',
      vip: 'bg-yellow-100 text-yellow-700'
    };
    return colors[type] || 'bg-gray-100 text-gray-700';
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[13px] font-semibold font-['Poppins',sans-serif] text-gray-700">Customer</h3>
        {selectedCustomer && selectedCustomer.customerType !== 'guest' && (
          <button
            onClick={handleClearCustomer}
            className="text-xs text-gray-500 hover:text-red-600 flex items-center gap-1"
            title="Switch to guest customer"
          >
            <X className="h-3 w-3" />
            Clear
          </button>
        )}
      </div>

      {/* Quick Actions */}
      <div className="flex gap-2 mb-2">
        <button
          onClick={handleSelectGuest}
          disabled={!guestCustomer}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-2 bg-gray-50 hover:bg-gray-100 border border-gray-300 rounded text-[12px] font-medium font-['Poppins',sans-serif] text-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <User className="h-3.5 w-3.5" />
          Guest
        </button>
        <button
          onClick={() => setShowNewCustomerModal(true)}
          className="flex items-center justify-center gap-1.5 px-2 py-2 bg-blue-50 hover:bg-blue-100 border border-blue-300 rounded text-[12px] font-medium font-['Poppins',sans-serif] text-blue-700 transition-colors"
          title="Create new customer"
        >
          <UserPlus className="h-3.5 w-3.5" />
          <span>New</span>
        </button>
      </div>

      {/* Search Input */}
      <div className="relative" ref={searchInputRef}>
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by name, phone..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onFocus={() => searchResults.length > 0 && setShowSearchDropdown(true)}
            className="w-full pl-9 pr-3 py-1.5 border border-gray-300 rounded text-[12px] font-['Poppins',sans-serif] focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          {loading && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent"></div>
            </div>
          )}
        </div>

        {/* Search Dropdown */}
        {showSearchDropdown && searchResults.length > 0 && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto">
            {searchResults.map((customer) => (
              <button
                key={customer.id}
                onClick={() => handleSelectCustomer(customer)}
                className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b border-gray-100 last:border-0 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {customer.fullName}
                    </p>
                    <p className="text-xs text-gray-500 truncate">
                      {customer.phone || 'No phone'}
                    </p>
                  </div>
                  <span className={`ml-2 px-2 py-1 text-xs font-medium rounded-full whitespace-nowrap ${getCustomerTypeBadgeColor(customer.customerType)}`}>
                    {getCustomerTypeLabel(customer.customerType)}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* No Results */}
        {showSearchDropdown && searchTerm && !loading && searchResults.length === 0 && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg p-4 text-center">
            <p className="text-sm text-gray-500">Customer not found</p>
            <button
              onClick={() => setShowNewCustomerModal(true)}
              className="mt-2 text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Create new customer
            </button>
          </div>
        )}
      </div>

      {/* Selected Customer Display */}
      {selectedCustomer && (
        <div className="mt-3 p-2.5 bg-gradient-to-r from-blue-50 to-indigo-50 rounded border border-blue-200">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5 mb-1">
                <p className="text-[12px] font-semibold font-['Poppins',sans-serif] text-gray-900 truncate">
                  {selectedCustomer.fullName}
                </p>
                <span className={`px-1.5 py-0.5 text-[10px] font-medium font-['Poppins',sans-serif] rounded-full ${getCustomerTypeBadgeColor(selectedCustomer.customerType)}`}>
                  {getCustomerTypeLabel(selectedCustomer.customerType)}
                </span>
              </div>
              <p className="text-[10px] font-['Poppins',sans-serif] text-gray-600 truncate">
                {selectedCustomer.phone || 'No phone'}
              </p>
              {selectedCustomer.customerCode && !selectedCustomer.isVirtual && (
                <p className="text-[10px] font-['Poppins',sans-serif] text-gray-500 mt-0.5">
                  {selectedCustomer.customerCode}
                </p>
              )}
            </div>

            {/* Discount Badge */}
            <div className="ml-2 text-right">
              <p className="text-[10px] font-['Poppins',sans-serif] text-gray-500">Discount</p>
              <p className="text-[16px] font-bold font-['Poppins',sans-serif] text-green-600">
                {getDiscountPercentage(selectedCustomer.customerType)}%
              </p>
            </div>
          </div>
        </div>
      )}

      {/* POS Add Customer Modal */}
      <POSAddCustomerModal
        isOpen={showNewCustomerModal}
        onClose={() => setShowNewCustomerModal(false)}
        onSuccess={handleCustomerCreated}
      />
    </div>
  );
};
