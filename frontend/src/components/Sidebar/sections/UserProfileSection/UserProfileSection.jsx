import React, { useState, useEffect } from 'react';
import authService from '../../../../services/authService';

export const UserProfileSection = ({ isCollapsed }) => {
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Lấy thông tin user từ localStorage hoặc API
    const loadUser = async () => {
      try {
        // Thử lấy từ localStorage trước
        const storedUser = authService.getUser();
        if (storedUser) {
          setUser(storedUser);
        } else if (authService.isAuthenticated()) {
          // Nếu không có trong localStorage nhưng có token, lấy từ API
          const currentUser = await authService.getCurrentUser();
          setUser(currentUser);
        }
      } catch (error) {
        console.error('Error loading user:', error);
      }
    };

    loadUser();
  }, []);

  // Default avatar nếu không có
  const defaultAvatar = 'https://ui-avatars.com/api/?name=' +
    encodeURIComponent(user?.fullName || user?.username || 'User') +
    '&background=10b981&color=fff&size=48';

  // Lấy role name từ role object hoặc fallback
  const getRoleName = () => {
    if (!user) return 'Loading...';

    // Nếu role là object có roleName
    if (user.role && typeof user.role === 'object') {
      return user.role.roleName || user.role.roleId || 'User';
    }

    // Nếu role là string (backward compatibility)
    if (typeof user.role === 'string') {
      return user.role.charAt(0).toUpperCase() + user.role.slice(1);
    }

    return 'User';
  };

  if (!user) {
    return (
      <div className={`bg-gray-50 rounded-lg mb-2 animate-pulse ${isCollapsed ? 'p-2' : 'p-3'}`}>
        {isCollapsed ? (
          <div className="w-10 h-10 rounded-full bg-gray-300 mx-auto"></div>
        ) : (
          <div className="flex items-center">
            <div className="w-12 h-12 rounded-full bg-gray-300 mr-3"></div>
            <div className="flex-1">
              <div className="h-4 bg-gray-300 rounded w-24 mb-2"></div>
              <div className="h-3 bg-gray-300 rounded w-16"></div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`bg-gray-50 rounded-lg mb-2 ${isCollapsed ? 'p-2' : 'p-3'}`} title={isCollapsed ? `${user.fullName || user.username} - ${getRoleName()}` : ''}>
      {isCollapsed ? (
        <div className="flex justify-center">
          <img
            src={user.avatar || defaultAvatar}
            alt="User Avatar"
            className="w-10 h-10 rounded-full object-cover"
            onError={(e) => {
              e.target.src = defaultAvatar;
            }}
          />
        </div>
      ) : (
        <div className="flex items-center">
          <img
            src={user.avatar || defaultAvatar}
            alt="User Avatar"
            className="w-12 h-12 rounded-full mr-3 object-cover"
            onError={(e) => {
              e.target.src = defaultAvatar;
            }}
          />
          <div>
            <p className="font-semibold text-emerald-600 text-sm">
              {user.fullName || user.username}
            </p>
            <p className="text-xs text-gray-500">
              {getRoleName()}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};