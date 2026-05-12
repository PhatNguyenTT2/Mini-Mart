import { useNotifications } from '../../contexts/NotificationContext'
import { ToastNotification } from './ToastNotification'

export const ToastContainer = () => {
  const { toasts, removeToast } = useNotifications()

  if (toasts.length === 0) {
    return null
  }

  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none">
      {toasts.map((toast) => (
        <div key={toast.toastId} className="pointer-events-auto">
          <ToastNotification
            notification={toast}
            onClose={() => removeToast(toast.toastId)}
          />
        </div>
      ))}
    </div>
  )
}
