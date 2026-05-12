import { MapPin, Phone, Mail } from 'lucide-react';

const ACCOUNT_LINKS = ['Login', 'View Cart', 'Track Order'];

export default function AboutSection() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
      {/* Store Info */}
      <div>
        <div className="mb-4">
          <span className="font-bold text-2xl text-gray-800">
            🛒 <span className="text-emerald-600">Mart</span>
          </span>
        </div>
        <p className="text-gray-600 text-sm mb-5">Online Shopping Platform</p>
        <div className="space-y-3">
          <div className="flex items-start gap-2 text-sm text-gray-600">
            <MapPin className="w-4 h-4 mt-0.5 shrink-0 text-emerald-500" />
            <div>
              <span className="font-semibold text-gray-700">Address: </span>
              <span>Thu Duc, Ho Chi Minh City</span>
            </div>
          </div>
          <div className="flex items-start gap-2 text-sm text-gray-600">
            <Phone className="w-4 h-4 mt-0.5 shrink-0 text-emerald-500" />
            <div>
              <span className="font-semibold text-gray-700">Hotline: </span>
              <a href="tel:1900888123" className="text-emerald-600 no-underline">1900-888-123</a>
            </div>
          </div>
          <div className="flex items-start gap-2 text-sm text-gray-600">
            <Mail className="w-4 h-4 mt-0.5 shrink-0 text-emerald-500" />
            <div>
              <span className="font-semibold text-gray-700">Email: </span>
              <a href="mailto:support@mart.com" className="text-emerald-600 no-underline">support@mart.com</a>
            </div>
          </div>
        </div>
      </div>

      {/* Account */}
      <div>
        <h3 className="font-bold text-gray-800 text-xl mb-4">Account</h3>
        <ul className="space-y-2 list-none p-0 m-0">
          {ACCOUNT_LINKS.map((link) => (
            <li key={link}>
              <a href="#" className="text-gray-600 text-sm hover:text-emerald-600 transition-colors no-underline">{link}</a>
            </li>
          ))}
        </ul>
      </div>

      {/* Payment */}
      <div>
        <h3 className="font-bold text-gray-800 text-xl mb-2">Safe Payment</h3>
        <p className="text-gray-500 text-sm mb-4">Secure payment gateway</p>
        <div className="flex gap-3 items-center">
          <div className="bg-gray-100 rounded-lg px-4 py-2 text-gray-700 text-xs font-bold">VISA</div>
          <div className="bg-gray-100 rounded-lg px-4 py-2 text-gray-700 text-xs font-bold">MasterCard</div>
          <div className="bg-gray-100 rounded-lg px-4 py-2 text-gray-700 text-xs font-bold">Momo</div>
        </div>
      </div>
    </div>
  );
}
