import React, { useState, useRef } from 'react'
import { Send } from 'lucide-react'
import { useChat } from '../../../contexts/ChatContext'

export const ChatInput = () => {
  const [text, setText] = useState('')
  const inputRef = useRef(null)
  const { canSend, isConnected, isTyping, streamingText, sendMessage } = useChat()

  // Edge Case C: lock input during streaming/typing/disconnect
  const isLocked = !canSend

  const handleSend = () => {
    if (isLocked || !text.trim()) return
    sendMessage(text)
    setText('')
    inputRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const getPlaceholder = () => {
    if (!isConnected) return 'Đang kết nối lại...'
    if (isTyping || streamingText) return 'Đang trả lời...'
    return 'Nhập tin nhắn...'
  }

  return (
    <div className="flex-shrink-0 flex items-center gap-2 px-3 py-2.5 border-t border-gray-200 bg-white rounded-b-2xl">
      <input
        ref={inputRef}
        type="text"
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isLocked}
        placeholder={getPlaceholder()}
        className={`flex-1 px-3 py-2 text-sm rounded-xl border border-gray-200 outline-none transition-all
          ${isLocked
            ? 'bg-gray-50 text-gray-400 cursor-not-allowed'
            : 'bg-white text-gray-800 focus:border-blue-400 focus:ring-1 focus:ring-blue-100'
          }`}
      />
      <button
        onClick={handleSend}
        disabled={isLocked || !text.trim()}
        className={`p-2 rounded-xl transition-all ${
          isLocked || !text.trim()
            ? 'bg-gray-100 text-gray-300 cursor-not-allowed'
            : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
        }`}
      >
        <Send size={16} />
      </button>
    </div>
  )
}
