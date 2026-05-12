import { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'

const NotificationContext = createContext()

export const useNotifications = () => {
  const context = useContext(NotificationContext)
  if (!context) {
    throw new Error('useNotifications must be used within NotificationProvider')
  }
  return context
}

export const NotificationProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([])
  const [toasts, setToasts] = useState([])
  const [counts, setCounts] = useState({ total: 0, critical: 0, high: 0, warning: 0 })

  // Socket removed — will be reconnected via chatbot WS in future
  const isConnected = false

  // Track shown toast IDs to prevent duplicates
  const shownToastIds = useState(() => new Set())[0]

  // Remove toast
  const removeToast = useCallback((toastId) => {
    setToasts(prev => prev.filter(t => t.toastId !== toastId))
  }, [])

  // Add toast notification (with duplicate check)
  const addToast = useCallback((notification) => {
    if (shownToastIds.has(notification.id)) {
      return
    }

    shownToastIds.add(notification.id)

    const toast = {
      ...notification,
      toastId: `toast-${notification.id}-${Date.now()}`
    }

    setToasts(prev => [...prev, toast])

    setTimeout(() => {
      removeToast(toast.toastId)
      setTimeout(() => {
        shownToastIds.delete(notification.id)
      }, 5000)
    }, 10000)
  }, [removeToast, shownToastIds])

  // Add new notification
  const addNotification = useCallback((notification) => {
    setNotifications(prev => {
      const exists = prev.some(n => n.id === notification.id)
      if (exists) return prev

      let filtered = prev
      if (notification.id.startsWith('credit-') && notification.supplierId) {
        filtered = prev.filter(n =>
          !n.id.startsWith(`credit-${notification.supplierId}`)
        )
      }

      const newNotifications = [notification, ...filtered]

      const newCounts = {
        total: newNotifications.length,
        critical: newNotifications.filter(n => n.severity === 'critical').length,
        high: newNotifications.filter(n => n.severity === 'high').length,
        warning: newNotifications.filter(n => n.severity === 'warning').length
      }
      setCounts(newCounts)

      return newNotifications
    })

    addToast(notification)
  }, [addToast])

  // Set initial notifications (from API, no toast)
  const setInitialNotifications = useCallback((notificationList) => {
    setNotifications(notificationList)

    const newCounts = {
      total: notificationList.length,
      critical: notificationList.filter(n => n.severity === 'critical').length,
      high: notificationList.filter(n => n.severity === 'high').length,
      warning: notificationList.filter(n => n.severity === 'warning').length
    }
    setCounts(newCounts)
  }, [])

  // Clear all notifications
  const clearNotifications = useCallback(() => {
    setNotifications([])
    setCounts({ total: 0, critical: 0, high: 0, warning: 0 })
  }, [])

  const value = {
    notifications,
    toasts,
    counts,
    isConnected,
    addNotification,
    setInitialNotifications,
    removeToast,
    clearNotifications
  }

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  )
}
