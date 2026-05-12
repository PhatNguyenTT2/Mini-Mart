import { useNavigate } from 'react-router-dom';
import { useStore } from '../contexts/StoreContext';
import { MapPin, Phone, Store, ChevronRight, ShoppingBag } from 'lucide-react';

export default function StoreSelection() {
  const { stores, loading, selectStore } = useStore();
  const navigate = useNavigate();

  const handleSelectStore = (store) => {
    selectStore(store);
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 via-white to-teal-50 flex flex-col">
      {/* Header */}
      <header className="py-8">
        <div className="max-w-5xl mx-auto px-4 text-center">
          <span className="font-bold text-3xl text-gray-800 flex items-center justify-center gap-2">
            🛒 <span className="text-emerald-600">Mart</span>
          </span>
          <p className="text-gray-400 text-sm mt-1 tracking-wide">Online Shopping</p>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-5xl mx-auto px-4 pb-16 w-full">
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-emerald-400 to-teal-500 rounded-3xl mb-5 shadow-lg shadow-emerald-200">
            <ShoppingBag className="w-9 h-9 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-800 mb-3">Welcome! Select Your Store</h1>
          <p className="text-gray-500 max-w-md mx-auto text-base leading-relaxed">
            Choose a store location to browse products with accurate pricing and availability.
          </p>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <div className="animate-spin rounded-full h-10 w-10 border-[3px] border-emerald-200 border-t-emerald-500" />
              <span className="text-sm text-gray-400">Loading stores...</span>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && stores.length === 0 && (
          <div className="text-center py-16">
            <Store className="w-14 h-14 text-gray-200 mx-auto mb-4" />
            <p className="text-gray-400 text-base">No stores available at the moment.</p>
          </div>
        )}

        {/* Store Grid */}
        {!loading && stores.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {stores.map((store, index) => (
              <button
                key={store.id}
                onClick={() => handleSelectStore(store)}
                className="bg-white border border-gray-100 rounded-2xl p-6 text-left transition-all duration-300 hover:shadow-xl hover:border-emerald-400 hover:-translate-y-1 group cursor-pointer"
                style={{
                  animation: `fadeInUp 0.4s ease-out ${index * 100}ms both`,
                }}
              >
                {/* Store Icon + Name */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-gradient-to-br from-emerald-50 to-teal-50 rounded-xl flex items-center justify-center group-hover:from-emerald-100 group-hover:to-teal-100 transition-all">
                      <Store className="w-5 h-5 text-emerald-600" />
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-800 group-hover:text-emerald-600 transition-colors text-base">
                        {store.name}
                      </h3>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-emerald-500 group-hover:translate-x-0.5 transition-all" />
                </div>

                {/* Details */}
                <div className="space-y-2 mb-4">
                  {store.address && (
                    <div className="flex items-start gap-2 text-sm text-gray-500">
                      <MapPin className="w-4 h-4 mt-0.5 shrink-0 text-gray-300" />
                      <span className="line-clamp-2 leading-relaxed">{store.address}</span>
                    </div>
                  )}
                  {store.phone && (
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Phone className="w-4 h-4 shrink-0 text-gray-300" />
                      <span>{store.phone}</span>
                    </div>
                  )}
                </div>

                {/* CTA */}
                <div className="pt-3 border-t border-gray-100 flex items-center justify-between">
                  <span className="text-sm font-bold text-emerald-600 group-hover:text-emerald-700 transition-colors">
                    Shop at this store
                  </span>
                  <span className="text-emerald-500 text-lg group-hover:translate-x-0.5 transition-transform">→</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="py-4 text-center">
        <p className="text-xs text-gray-300">© 2026 Mart — Online Shopping</p>
      </footer>

      {/* Animation keyframes */}
      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
