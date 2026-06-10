/**
 * Permission constants and utilities
 */

// All available permissions in the system
export const PERMISSIONS = {
  VIEW_DASHBOARD: 'view_dashboard',
  MANAGE_PRODUCTS: 'manage_products',
  MANAGE_CATEGORIES: 'manage_categories',
  MANAGE_ORDERS: 'manage_orders',
  MANAGE_CUSTOMERS: 'manage_customers',
  MANAGE_SUPPLIERS: 'manage_suppliers',
  MANAGE_EMPLOYEES: 'manage_employees',
  MANAGE_POS: 'manage_POS',
  MANAGE_ROLES: 'manage_roles',
  MANAGE_INVENTORY: 'manage_inventory',
  VIEW_REPORTS: 'view_reports',
  MANAGE_PAYMENTS: 'manage_payments',
  MANAGER_SETTING: 'manager_setting',
  ADMIN_SETTING: 'admin_setting',
  VIEW_NOTIFICATIONS: 'view_notifications'
}

// Permission labels for UI display
export const PERMISSION_LABELS = {
  [PERMISSIONS.VIEW_DASHBOARD]: 'View Dashboard',
  [PERMISSIONS.MANAGE_PRODUCTS]: 'Manage Products',
  [PERMISSIONS.MANAGE_CATEGORIES]: 'Manage Categories',
  [PERMISSIONS.MANAGE_ORDERS]: 'Manage Orders',
  [PERMISSIONS.MANAGE_CUSTOMERS]: 'Manage Customers',
  [PERMISSIONS.MANAGE_SUPPLIERS]: 'Manage Suppliers',
  [PERMISSIONS.MANAGE_EMPLOYEES]: 'Manage Employees',
  [PERMISSIONS.MANAGE_POS]: 'Manage POS',
  [PERMISSIONS.MANAGE_ROLES]: 'Manage Roles',
  [PERMISSIONS.MANAGE_INVENTORY]: 'Manage Inventory',
  [PERMISSIONS.VIEW_REPORTS]: 'View Reports',
  [PERMISSIONS.MANAGE_PAYMENTS]: 'Manage Payments',
  [PERMISSIONS.MANAGER_SETTING]: 'Manage Setting',
  [PERMISSIONS.ADMIN_SETTING]: 'Admin Setting',
  [PERMISSIONS.VIEW_NOTIFICATIONS]: 'View Notifications'
}

/**
 * Check if user has a specific permission
 * @param {Object} user - User object from authService
 * @param {string} permission - Permission to check
 * @returns {boolean}
 */
export const hasPermission = (user, permission) => {
  if (!user) return false
  if (user.role === 'Super Admin') return true
  if (!user.permissions) return false
  return user.permissions.includes(permission)
}

/**
 * Check if user has any of the specified permissions
 * @param {Object} user - User object from authService
 * @param {Array<string>} permissions - Array of permissions to check
 * @returns {boolean}
 */
export const hasAnyPermission = (user, permissions) => {
  if (!user) return false
  if (user.role === 'Super Admin') return true
  if (!user.permissions) return false
  return permissions.some(permission => user.permissions.includes(permission))
}

/**
 * Check if user has all of the specified permissions
 * @param {Object} user - User object from authService
 * @param {Array<string>} permissions - Array of permissions to check
 * @returns {boolean}
 */
export const hasAllPermissions = (user, permissions) => {
  if (!user) return false
  if (user.role === 'Super Admin') return true
  if (!user.permissions) return false
  return permissions.every(permission => user.permissions.includes(permission))
}

/**
 * Get user's permissions as array
 * @param {Object} user - User object from authService
 * @returns {Array<string>}
 */
export const getUserPermissions = (user) => {
  return user?.permissions || []
}
