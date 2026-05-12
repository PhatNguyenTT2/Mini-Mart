import { MessageCircle, X } from 'lucide-react'
import { useChat } from '../../contexts/ChatContext'
import { ChatPanel } from './sections/ChatPanel'

export const ChatWidget = () => {
  const { isOpen, toggleChat } = useChat()

  return (
    <>
      {/* Chat Panel */}
      {isOpen && (
        <div className="fixed bottom-20 right-6 z-50 animate-slide-up">
          <ChatPanel />
        </div>
      )}

      {/* FAB Button */}
      <button
        id="customer-chat-fab"
        onClick={toggleChat}
        className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center transition-all duration-300 hover:scale-110 hover:shadow-xl ${
          isOpen
            ? 'bg-gray-600 hover:bg-gray-700'
            : 'bg-emerald-600 hover:bg-emerald-700'
        }`}
      >
        {isOpen ? (
          <X size={24} className="text-white" />
        ) : (
          <MessageCircle size={24} className="text-white" />
        )}
      </button>
    </>
  )
}

export default ChatWidget
