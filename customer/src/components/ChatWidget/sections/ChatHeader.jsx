import { Bot, Minus, RotateCcw, WifiOff } from 'lucide-react'
import { useChat } from '../../../contexts/ChatContext'

export const ChatHeader = () => {
  const { isConnected, setIsOpen, startNewSession } = useChat()

  return (
    <div className="flex-shrink-0">
      {/* Main header — emerald theme */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-emerald-600 to-emerald-700 text-white rounded-t-2xl">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center">
            <Bot size={18} />
          </div>
          <div>
            <p className="font-semibold text-sm">Shopping Assistant</p>
            <p className="text-[10px] text-emerald-100">
              {isConnected ? 'Online' : 'Connecting...'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={startNewSession}
            className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
            title="New conversation"
          >
            <RotateCcw size={16} />
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1.5 rounded-lg hover:bg-white/20 transition-colors"
            title="Minimize"
          >
            <Minus size={16} />
          </button>
        </div>
      </div>

      {/* Connection banner */}
      {!isConnected && (
        <div className="bg-amber-50 text-amber-700 text-xs text-center py-1.5 flex items-center justify-center gap-1.5 border-b border-amber-200">
          <WifiOff size={12} />
          <span>Reconnecting...</span>
        </div>
      )}
    </div>
  )
}
