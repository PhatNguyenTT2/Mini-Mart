import React, { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';

/**
 * Component to display permission denied message on Dashboard
 * Shows when user is redirected from a page they don't have access to
 */
export const PermissionAlert = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [showAlert, setShowAlert] = React.useState(false);
  const [errorMessage, setErrorMessage] = React.useState('');

  useEffect(() => {
    if (location.state?.error) {
      setShowAlert(true);
      setErrorMessage(location.state.error);

      // Clear the error from location state
      window.history.replaceState({}, document.title);

      // Auto-hide after 5 seconds
      const timer = setTimeout(() => {
        setShowAlert(false);
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [location]);

  if (!showAlert) return null;

  return (
    <div className="fixed top-4 right-4 z-50 animate-slide-in-right">
      <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-lg shadow-lg max-w-md">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <ShieldAlert className="h-6 w-6 text-red-500" />
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-semibold text-red-800 font-['Poppins',sans-serif]">
              Access Denied
            </h3>
            <p className="mt-1 text-sm text-red-700 font-['Poppins',sans-serif]">
              {errorMessage}
            </p>
          </div>
          <div className="ml-4 flex-shrink-0">
            <button
              onClick={() => setShowAlert(false)}
              className="inline-flex text-red-400 hover:text-red-600 focus:outline-none"
            >
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
