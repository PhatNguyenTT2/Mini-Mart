import { X, AlertCircle, AlertTriangle, Info, DollarSign, Clock } from 'lucide-react'

export const ToastNotification = ({ notification, onClose }) => {
  const getSeverityStyles = () => {
    switch (notification.severity) {
      case 'critical':
        return {
          container: 'bg-red-50 border-red-200',
          icon: 'text-red-600',
          title: 'text-red-900',
          message: 'text-red-700',
          closeBtn: 'text-red-400 hover:text-red-600'
        }
      case 'high':
        return {
          container: 'bg-orange-50 border-orange-200',
          icon: 'text-orange-600',
          title: 'text-orange-900',
          message: 'text-orange-700',
          closeBtn: 'text-orange-400 hover:text-orange-600'
        }
      case 'warning':
        return {
          container: 'bg-amber-50 border-amber-200',
          icon: 'text-amber-600',
          title: 'text-amber-900',
          message: 'text-amber-700',
          closeBtn: 'text-amber-400 hover:text-amber-600'
        }
      default:
        return {
          container: 'bg-blue-50 border-blue-200',
          icon: 'text-blue-600',
          title: 'text-blue-900',
          message: 'text-blue-700',
          closeBtn: 'text-blue-400 hover:text-blue-600'
        }
    }
  }

  const getSeverityIcon = () => {
    // Special icon for supplier credit notifications
    if (notification.type && notification.type.startsWith('credit_')) {
      return <DollarSign className="w-5 h-5" />
    }

    switch (notification.severity) {
      case 'critical':
        return <AlertCircle className="w-5 h-5" />
      case 'high':
        return <AlertTriangle className="w-5 h-5" />
      case 'warning':
        return <Clock className="w-5 h-5" />
      default:
        return <Info className="w-5 h-5" />
    }
  }

  const styles = getSeverityStyles()

  return (
    <div
      className={`${styles.container} rounded-lg border-2 shadow-lg p-4 min-w-[320px] max-w-[400px] animate-slide-in-right`}
      role="alert"
    >
      <div className="flex gap-3">
        <div className={`flex-shrink-0 ${styles.icon}`}>
          {getSeverityIcon()}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <p className={`text-[13px] font-semibold ${styles.title}`}>
              {notification.title}
            </p>
            <button
              onClick={onClose}
              className={`flex-shrink-0 ${styles.closeBtn} transition-colors`}
              aria-label="Close notification"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <p className={`text-[12px] ${styles.message} leading-relaxed`}>
            {notification.message}
          </p>

          {/* Additional details */}
          {notification.batchCode && (
            <div className="mt-2 text-[11px] text-gray-600">
              <span className="font-medium">Batch:</span> {notification.batchCode}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
