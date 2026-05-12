import React, { useState, useEffect } from 'react';
import { href, Link, useLocation, useNavigate } from 'react-router-dom';
import {
  ChevronDown,
  ChevronRight,
  LayoutGrid,
  ShoppingBag,
  Package2,
  User,
  ClipboardList,
  Mail,
  MessageSquare,
  CheckSquare,
  UserCircle,
  Shield,
  AlertTriangle,
  Settings,
  DollarSign,
  Users,
  User2Icon,
  LogOut,
  Menu,
  CarTaxiFront,
  CassetteTapeIcon,
  BookAIcon,
  PanelTopInactiveIcon,
  LucideStore,
  LucideAArrowDown,
  ReceiptEuro
} from 'lucide-react';
import authService from '../../../../services/authService';
import { hasPermission, PERMISSIONS } from '../../../../utils/permissions';

export const NavigationMenuSection = ({ isCollapsed, toggleCollapse }) => {
  // Lấy trạng thái từ localStorage khi component mount
  const [openDropdowns, setOpenDropdowns] = useState(() => {
    const savedState = localStorage.getItem('sidebarDropdownState');
    return savedState ? JSON.parse(savedState) : {};
  });
  const location = useLocation();
  const navigate = useNavigate();
  const currentUser = authService.getUser();

  // Lưu trạng thái vào localStorage mỗi khi thay đổi
  useEffect(() => {
    localStorage.setItem('sidebarDropdownState', JSON.stringify(openDropdowns));
  }, [openDropdowns]);

  const toggleDropdown = (itemName) => {
    setOpenDropdowns(prev => ({
      ...prev,
      [itemName]: !prev[itemName]
    }));
  };

  const handleSignOut = async () => {
    try {
      await authService.logout();
      navigate('/');
    } catch (error) {
      console.error('Sign out error:', error);
      // Still navigate to login even if logout API fails
      navigate('/');
    }
  };

  const menuItems = [
    {
      category: 'Management',
      items: [
        {
          name: 'Dashboard',
          icon: LayoutGrid,
          href: '/dashboard',
          permission: PERMISSIONS.VIEW_DASHBOARD
        },
        {
          name: 'Orders',
          icon: ShoppingBag,
          arrow: false,
          href: '/orders',
          permission: PERMISSIONS.MANAGE_ORDERS
        },
        {
          name: 'Categories',
          icon: BookAIcon,
          href: '/categories',
          permission: PERMISSIONS.MANAGE_CATEGORIES
        },
        {
          name: 'Products',
          icon: Package2,
          arrow: true,
          permission: PERMISSIONS.MANAGE_PRODUCTS,
          submenu: [
            { name: 'List', href: '/products/' },
            { name: 'View', href: '/products/view' },
            { name: 'QR Codes', href: '/product-qr-codes' }
          ]
        },
        {
          name: 'Customers',
          icon: User,
          href: '/customers',
          permission: PERMISSIONS.MANAGE_CUSTOMERS
        },
        {
          name: 'Suppliers',
          icon: User2Icon,
          href: '/suppliers',
          permission: PERMISSIONS.MANAGE_SUPPLIERS
        },
        {
          name: 'Inventory',
          icon: LucideStore,
          arrow: true,
          permission: PERMISSIONS.MANAGE_INVENTORY,
          submenu: [
            { name: 'Management', href: '/inventory/management' },
            { name: 'Purchase Orders', href: '/inventory/purchase-orders' },
            { name: 'Stock Outs', href: '/inventory/stock-outs' },
            { name: 'Locations', href: '/inventory/locations' }
          ]
        },
        {
          name: 'Payments',
          icon: DollarSign,
          href: '/payments',
          permission: PERMISSIONS.MANAGE_PAYMENTS
        },
        {
          name: 'Reports',
          icon: ReceiptEuro,
          arrow: true,
          permission: PERMISSIONS.VIEW_REPORTS,
          submenu: [
            { name: 'Sales', href: '/reports/sales' },
            { name: 'Purchase', href: '/reports/purchase' },
            { name: 'Profit', href: '/reports/profit' },
            { name: 'Inventory', href: '/reports/inventory' },
            { name: 'Employee Sales', href: '/reports/employee-sales' },
            { name: 'Customer Sales', href: '/reports/customer-sales' }
          ]
        },
      ],
    },
    {
      category: 'Admin',
      items: [
        {
          name: 'Users',
          icon: Users,
          arrow: true,
          submenu: [
            {
              name: 'Employees',
              href: '/employees',
              permission: PERMISSIONS.MANAGE_EMPLOYEES
            },
            {
              name: 'Roles',
              href: '/roles',
              permission: PERMISSIONS.MANAGE_ROLES
            },
            {
              name: 'POS',
              href: '/pos-management',
              permission: PERMISSIONS.MANAGE_POS
            }
          ]
        },
        {
          name: 'Settings',
          icon: Settings,
          href: '/settings',
          permission: PERMISSIONS.MANAGE_SETTINGS
        }
      ],
    },
  ];

  // Filter menu items based on user permissions
  const filterMenuByPermissions = (items) => {
    return items
      .map(category => ({
        ...category,
        items: category.items.filter(item => {
          // If item has no permission requirement, show it
          if (!item.permission && !item.submenu) return true;

          // If item has permission requirement, check it
          if (item.permission) {
            return hasPermission(currentUser, item.permission);
          }

          // If item has submenu, filter submenu items
          if (item.submenu) {
            const filteredSubmenu = item.submenu.filter(subitem => {
              if (!subitem.permission) return true;
              return hasPermission(currentUser, subitem.permission);
            });

            // Only show parent if it has visible submenu items
            if (filteredSubmenu.length > 0) {
              item.submenu = filteredSubmenu;
              return true;
            }
            return false;
          }

          return true;
        })
      }))
      .filter(category => category.items.length > 0); // Remove empty categories
  };

  const filteredMenuItems = filterMenuByPermissions(menuItems);

  return (
    <nav className="pb-4 flex flex-col h-full">
      <div className="flex-1">
        {filteredMenuItems.map((menu, index) => (
          <div key={index}>
            {!isCollapsed && (
              <h3 className="text-xs text-gray-500 uppercase tracking-wider font-bold my-4 px-4">
                {menu.category}
              </h3>
            )}
            <ul>
              {menu.items.map((item, itemIndex) => {
                const isActive = item.href === location.pathname;
                const hasActiveSubmenu = item.submenu?.some(sub => sub.href === location.pathname);

                return (
                  <li key={itemIndex}>
                    <div>
                      {item.arrow ? (
                        <div
                          onClick={() => {
                            if (isCollapsed) {
                              toggleCollapse();
                              // Set dropdown to open after sidebar expands
                              setTimeout(() => toggleDropdown(item.name), 100);
                            } else {
                              toggleDropdown(item.name);
                            }
                          }}
                          className={`flex items-center justify-between py-2 rounded-full text-sm cursor-pointer ${isCollapsed ? 'px-2 justify-center' : 'px-4'
                            } ${hasActiveSubmenu
                              ? 'bg-emerald-50 text-emerald-600'
                              : 'text-gray-700 hover:bg-emerald-50'
                            }`}
                          title={isCollapsed ? item.name : ''}
                        >
                          <div className={`flex items-center ${isCollapsed ? '' : ''}`}>
                            <div className="p-2 rounded-full">
                              <item.icon className="w-5 h-5 text-gray-500" />
                            </div>
                            {!isCollapsed && <span className="ml-3">{item.name}</span>}
                          </div>
                          {!isCollapsed && (
                            <>
                              {item.badge && (
                                <span className="bg-emerald-500 text-white text-xs font-bold rounded-full px-2 py-1">
                                  {item.badge}
                                </span>
                              )}
                              {openDropdowns[item.name] ? (
                                <ChevronDown className="w-4 h-4 text-gray-500" />
                              ) : (
                                <ChevronRight className="w-4 h-4 text-gray-500" />
                              )}
                              {item.new && (
                                <span className="bg-emerald-500 text-white text-xs font-bold rounded-md px-2 py-1">
                                  New
                                </span>
                              )}
                            </>
                          )}
                        </div>
                      ) : (
                        <Link
                          to={item.href}
                          className={`flex items-center justify-between py-2 rounded-full text-sm ${isCollapsed ? 'px-2 justify-center' : 'px-4'
                            } ${isActive
                              ? 'bg-emerald-500 text-white'
                              : 'text-gray-700 hover:bg-emerald-50'
                            }`}
                          title={isCollapsed ? item.name : ''}
                        >
                          <div className={`flex items-center ${isCollapsed ? '' : ''}`}>
                            <div className={`p-2 rounded-full ${isActive ? 'bg-emerald-100' : ''}`}>
                              <item.icon
                                className={`w-5 h-5 ${isActive ? 'text-emerald-600' : 'text-gray-500'
                                  }`}
                              />
                            </div>
                            {!isCollapsed && <span className="ml-3">{item.name}</span>}
                          </div>
                          {!isCollapsed && (
                            <>
                              {item.badge && (
                                <span className="bg-emerald-500 text-white text-xs font-bold rounded-full px-2 py-1">
                                  {item.badge}
                                </span>
                              )}
                              {item.new && (
                                <span className="bg-emerald-500 text-white text-xs font-bold rounded-md px-2 py-1">
                                  New
                                </span>
                              )}
                            </>
                          )}
                        </Link>
                      )}

                      {/* Submenu dropdown */}
                      {item.arrow && item.submenu && !isCollapsed && openDropdowns[item.name] && (
                        <ul className="ml-8 mt-1 mb-2 space-y-1">
                          {item.submenu.map((subitem, subIndex) => {
                            const isSubmenuActive = subitem.href === location.pathname;

                            return (
                              <li key={subIndex}>
                                <Link
                                  to={subitem.href}
                                  className={`block py-2 px-4 text-sm rounded-lg transition-colors ${isSubmenuActive
                                    ? 'text-emerald-600 bg-emerald-50 font-medium'
                                    : 'text-gray-600 hover:text-emerald-600 hover:bg-emerald-50'
                                    }`}
                                >
                                  {subitem.name}
                                </Link>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>

      {/* Collapse Button - Menu item style */}
      <div className="mt-4 px-4">
        <button
          onClick={toggleCollapse}
          className={`w-full flex items-center py-2 rounded-full text-sm text-gray-700 hover:bg-emerald-50 transition-colors ${isCollapsed ? 'px-2 justify-center' : 'px-4'
            }`}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <div className="p-2 rounded-full">
            <Menu className="w-5 h-5 text-gray-500" />
          </div>
          {!isCollapsed && <span className="ml-3">Collapse</span>}
        </button>
      </div>

      {/* Sign Out Button - Đồng bộ với menu */}
      <div className="px-4 pb-4">
        <button
          onClick={handleSignOut}
          className={`w-full flex items-center py-2 rounded-full text-sm text-gray-700 hover:bg-emerald-50 transition-colors ${isCollapsed ? 'px-2 justify-center' : 'px-4'
            }`}
          title={isCollapsed ? 'Sign Out' : ''}
        >
          <div className="p-2 rounded-full">
            <LogOut className="w-5 h-5 text-gray-500" />
          </div>
          {!isCollapsed && <span className="ml-3">Sign Out</span>}
        </button>
      </div>
    </nav>
  );
};
