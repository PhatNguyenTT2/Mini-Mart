import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import authService from '../services/authService'

/**
 * Get first accessible route based on user permissions
 */
const getFirstAccessibleRoute = (permissions) => {
  if (!permissions || permissions.length === 0) {
    return '/no-access'
  }

  // Priority order of routes
  const routePermissionMap = [
    { route: '/dashboard', permission: 'view_dashboard' },
    { route: '/products/list', permission: 'manage_products' },
    { route: '/orders', permission: 'manage_orders' },
    { route: '/customers', permission: 'manage_customers' },
    { route: '/employees', permission: 'manage_employees' },
    { route: '/categories', permission: 'manage_categories' },
    { route: '/suppliers', permission: 'manage_suppliers' },
    { route: '/inventory/management', permission: 'manage_inventory' },
    { route: '/payments', permission: 'manage_payments' },
    { route: '/reports/sales', permission: 'view_reports' },
    { route: '/pos-management', permission: 'manage_POS' },
    { route: '/roles', permission: 'manage_roles' },
  ]

  for (const { route, permission } of routePermissionMap) {
    if (permissions.includes(permission)) {
      return route
    }
  }

  return '/no-access'
}

/**
 * Protected Route Component
 * Redirects to login if user is not authenticated
 * Optionally checks for specific permission
 */
export default function ProtectedRoute({ children, requiredPermission }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [isAuthorized, setIsAuthorized] = useState(null)

  useEffect(() => {
    const checkAuth = () => {
      // Check if authenticated
      if (!authService.isAuthenticated()) {
        navigate('/', { replace: true })
        return
      }

      // Get user data
      const user = authService.getUser()

      // Check if user has any permissions at all
      if (!user || !user.permissions || user.permissions.length === 0) {
        // User has no permissions, redirect to no-access page
        if (location.pathname !== '/no-access') {
          navigate('/no-access', { replace: true })
        }
        return
      }

      // If no specific permission required, just check authentication
      if (!requiredPermission) {
        setIsAuthorized(true)
        return
      }

      // Check if user has the required permission (or has 'all' permission)
      const hasPermission = user.permissions.includes('all') || user.permissions.includes(requiredPermission)

      if (!hasPermission) {
        // Find first accessible route for this user
        const firstRoute = getFirstAccessibleRoute(user.permissions)

        // Prevent redirect loop
        if (location.pathname !== firstRoute) {
          navigate(firstRoute, {
            replace: true,
            state: {
              error: 'You do not have permission to access this page'
            }
          })
        } else {
          // This shouldn't happen, but just in case
          setIsAuthorized(false)
        }
        return
      }

      setIsAuthorized(true)
    }

    checkAuth()
  }, [navigate, requiredPermission, location.pathname])

  // Show loading state while checking
  if (isAuthorized === null) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <svg className="animate-spin h-8 w-8 text-emerald-600 mx-auto mb-2" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-sm text-gray-600">Checking permissions...</p>
        </div>
      </div>
    )
  }

  // If authorized, render children
  if (isAuthorized) {
    return children
  }

  // Otherwise, render nothing (will redirect)
  return null
}
