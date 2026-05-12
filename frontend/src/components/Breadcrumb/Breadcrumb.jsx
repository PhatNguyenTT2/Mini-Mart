import React from 'react';
import { Link } from 'react-router-dom';
import { Home, ChevronRight } from 'lucide-react';

export const Breadcrumb = ({ items }) => {
  return (
    <nav className="flex items-center gap-2 text-sm" aria-label="Breadcrumb">
      <ol className="flex items-center gap-2">
        {items.map((item, index) => (
          <li key={index} className="flex items-center gap-2">
            {/* Item */}
            <div className="flex items-center gap-2">
              {/* Icon (only for first item - Home) */}
              {index === 0 && (
                <Home className="w-4 h-4 text-emerald-600" />
              )}

              {/* Link or Text */}
              {item.href ? (
                <Link
                  to={item.href}
                  className={`${index === items.length - 1
                      ? 'text-gray-600 cursor-default pointer-events-none'
                      : 'text-emerald-600 hover:text-emerald-700 hover:underline'
                    }`}
                >
                  {item.label}
                </Link>
              ) : (
                <span className="text-gray-600">{item.label}</span>
              )}
            </div>

            {/* Separator (not for last item) */}
            {index < items.length - 1 && (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
};
