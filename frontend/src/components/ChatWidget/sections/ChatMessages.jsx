import React, { useRef, useEffect } from 'react'
import { useChat } from '../../../contexts/ChatContext'
import { MessageBubble } from '../components/MessageBubble'
import { TypingIndicator } from '../components/TypingIndicator'
import { ProductCard } from '../components/ProductCard'
import { WelcomeScreen } from '../components/WelcomeScreen'

export const ChatMessages = () => {
  const { messages, streamingText, isTyping, products, suggestedPrompts, sendMessage } = useChat()
  const messagesEndRef = useRef(null)

  // Auto-scroll on new content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText, suggestedPrompts])

  const hasMessages = messages.length > 0 || streamingText

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 custom-scrollbar bg-gray-50">
      {/* Welcome screen (empty state) */}
      {!hasMessages && (
        <WelcomeScreen onSelectPrompt={sendMessage} />
      )}

      {/* Message list */}
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}

      {/* Product cards (after last assistant message) */}
      {products && products.length > 0 && (
        <div className="space-y-2">
          {products.map((product, i) => (
            <ProductCard key={i} product={product} />
          ))}
        </div>
      )}

      {/* Suggestion chips (from HELP or data intents) */}
      {suggestedPrompts && suggestedPrompts.length > 0 && !isTyping && !streamingText && (
        <div className="flex flex-wrap gap-1.5 ml-9 mt-1 animate-fade-in">
          {suggestedPrompts.map((prompt, i) => (
            <button
              key={i}
              onClick={() => sendMessage(prompt)}
              className="text-xs px-2.5 py-1 rounded-full border border-gray-200 text-gray-500 bg-white hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600 hover:scale-[1.03] active:scale-[0.97] transition-all duration-150 cursor-pointer"
            >
              {prompt}
            </button>
          ))}
        </div>
      )}

      {/* Streaming text (live typing effect) */}
      {streamingText && (
        <MessageBubble
          message={{ role: 'assistant', content: streamingText }}
          isStreaming={true}
        />
      )}

      {/* Typing indicator (before stream starts) */}
      {isTyping && !streamingText && (
        <TypingIndicator />
      )}

      <div ref={messagesEndRef} />
    </div>
  )
}
