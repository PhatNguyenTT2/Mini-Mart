import { Phone } from 'lucide-react';

export default function InformationSection() {
  return (
    <div className="border-t border-gray-200 py-4">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex flex-wrap items-center justify-between gap-6">
          {/* Copyright */}
          <p className="text-gray-400 text-sm">
            © 2026 Mart — Online Shopping
            <br />
            All rights reserved
          </p>

          {/* Hotline */}
          <div className="flex items-center gap-3">
            <Phone className="w-6 h-6 text-emerald-500 opacity-50" />
            <div>
              <a href="tel:1900888123" className="font-bold text-emerald-600 text-xl leading-tight no-underline block">
                1900-888-123
              </a>
              <p className="text-gray-400 text-xs tracking-wide">24/7 Support</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
