import React from 'react';
import { LoginSignupSection } from '../components/LoginSignup';

const LoginSignup = () => {
  return (
    <div className="min-h-screen bg-[#f8f8f8]">
      {/* Simple Header */}
      <div className="bg-white border-b border-[#ececec] py-4 px-8">
        <div className="max-w-[1440px] mx-auto">
          <h1 className="font-['Quicksand',sans-serif] font-bold text-[24px] text-[#3bb77e]">
            Mart Admin
          </h1>
        </div>
      </div>

      {/* Login/Signup Form */}
      <LoginSignupSection />

      {/* Simple Footer */}
      <div className="bg-white border-t border-[#ececec] py-6 px-8 mt-auto">
        <div className="max-w-[1440px] mx-auto text-center">
          <p className="font-['Lato',sans-serif] text-[#7e7e7e] text-[14px]">
            © 2025 Mart Admin Dashboard. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginSignup;
