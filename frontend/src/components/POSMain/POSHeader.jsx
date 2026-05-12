import React from 'react';

export const POSHeader = ({ currentEmployee, currentTime, onLogout }) => {
  return (
    <div className="bg-emerald-600 text-white p-4 shadow-lg flex items-center justify-between">
      <div className="flex items-center gap-3">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="5" width="18" height="14" rx="2" stroke="currentColor" strokeWidth="2" />
          <path d="M3 10h18" stroke="currentColor" strokeWidth="2" />
          <circle cx="7" cy="15" r="1" fill="currentColor" />
        </svg>
        <div>
          <h1 className="text-[20px] font-bold font-['Poppins',sans-serif]">
            POS Terminal
          </h1>
          <p className="text-[12px] font-['Poppins',sans-serif] text-emerald-100">
            {currentEmployee?.fullName || 'Employee'} (ID: {currentEmployee?.id || 'N/A'})
            {currentEmployee?.role && (
              <span className="ml-2 px-2 py-0.5 bg-emerald-500 rounded text-[10px] font-semibold">
                {currentEmployee.role}
              </span>
            )}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="text-right mr-4">
          <p className="text-[12px] font-['Poppins',sans-serif] text-emerald-100">
            {currentTime.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
          <p className="text-[14px] font-semibold font-['Poppins',sans-serif]">
            {currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </p>
        </div>
        <button
          onClick={onLogout}
          className="px-4 py-2 bg-white text-emerald-600 rounded-lg hover:bg-emerald-50 transition-colors text-[13px] font-semibold font-['Poppins',sans-serif] flex items-center gap-2"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>Logout</span>
          <span className="text-[10px] font-normal opacity-70">(Ctrl+L)</span>
        </button>
      </div>
    </div>
  );
};
