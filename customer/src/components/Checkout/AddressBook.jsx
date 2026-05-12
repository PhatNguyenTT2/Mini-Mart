import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { MapPin, Trash2, CheckCircle2 } from 'lucide-react';

export function AddressBook({ onSelect }) {
  const { user } = useAuth();
  const [addresses, setAddresses] = useState([]);

  useEffect(() => {
    if (!user) return;
    try {
      const saved = localStorage.getItem(`saved_addresses_${user.id || user.customerId}`);
      if (saved) {
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setAddresses(JSON.parse(saved));
      }
    } catch (err) {
      console.error('Failed to load addresses', err);
    }
  }, [user]);

  const handleDelete = (index) => {
    const newAddresses = addresses.filter((_, i) => i !== index);
    setAddresses(newAddresses);
    localStorage.setItem(`saved_addresses_${user.id || user.customerId}`, JSON.stringify(newAddresses));
  };

  if (addresses.length === 0) {
    return null; // Don't show if empty
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
      <h2 className="font-bold text-gray-800 text-xl mb-4">Saved Addresses</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {addresses.map((addr, index) => (
          <div 
            key={index}
            className={`relative border rounded-lg p-4 cursor-pointer transition-colors ${addr.isDefault ? 'border-emerald-500 bg-emerald-50' : 'border-gray-200 hover:border-emerald-300'}`}
            onClick={() => onSelect(addr)}
          >
            {addr.isDefault && (
              <span className="absolute top-3 right-3 text-emerald-500 text-xs font-bold px-2 py-1 bg-emerald-100 rounded-full">
                Default
              </span>
            )}
            <div className="flex items-start gap-3">
              <MapPin className="w-5 h-5 text-gray-400 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold text-gray-800 text-sm">{addr.fullName}</p>
                <p className="text-gray-500 text-xs mb-1">{addr.phone}</p>
                <p className="text-gray-600 text-sm line-clamp-2">{addr.address}</p>
              </div>
            </div>
            <div className="absolute bottom-3 right-3 flex gap-2">
              <button 
                onClick={(e) => { e.stopPropagation(); handleDelete(index); }}
                className="text-gray-400 hover:text-red-500 transition-colors"
                title="Delete address"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
