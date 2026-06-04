import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import chatSocketService from '../services/chatSocketService'

const ChatContext = createContext(null)

const STORAGE_KEY_PREFIX = 'posmart_chat_session'

export const ChatProvider = ({ children }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [streamingText, setStreamingText] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [products, setProducts] = useState(null)
  const [suggestedPrompts, setSuggestedPrompts] = useState(null)
  const [error, setError] = useState(null)
  const initializedRef = useRef(false)

  // Derived user-scoped storage key helper
  const getUserId = useCallback(() => {
    try {
      const token = localStorage.getItem('adminToken') || localStorage.getItem('posToken')
      if (!token) return null
      const payload = JSON.parse(atob(token.split('.')[1]))
      return payload.id || payload.userId || null
    } catch {
      return null
    }
  }, [])

  const getStorageKey = useCallback(() => {
    const uid = getUserId()
    return uid ? `${STORAGE_KEY_PREFIX}_${uid}` : STORAGE_KEY_PREFIX
  }, [getUserId])

  // Computed: can user send a message?
  const canSend = !isTyping && !streamingText && isConnected

  // ── Socket connection + event listeners ──
  useEffect(() => {
    const token = localStorage.getItem('adminToken') || localStorage.getItem('posToken')
    if (!token) return

    const socket = chatSocketService.connect(token)
    if (!socket) return

    // Connection state tracking (Edge Case B)
    const handleConnect = () => setIsConnected(true)
    const handleDisconnect = () => setIsConnected(false)
    const handleReconnectFailed = () => {
      setError('Chat server connection failed. Please reload the page.')
    }
    socket.on('connect', handleConnect)
    socket.on('disconnect', handleDisconnect)
    socket.on('reconnect_failed', handleReconnectFailed)
    setIsConnected(socket.connected)

    // Session ready (restore or new)
    const unsubReady = chatSocketService.onSessionReady((data) => {
      setSessionId(data.sessionId)
      setMessages(data.messages?.map(m => ({
        role: m.role,
        content: m.content,
        timestamp: m.created_at
      })) || [])
      setError(null)

      // Edge Case A: write new sessionId if not restored
      if (!data.restored) {
        localStorage.setItem(getStorageKey(), String(data.sessionId))
      }
    })

    // Stream chunks — append to streaming text
    const unsubChunk = chatSocketService.onStreamChunk((data) => {
      setStreamingText(prev => prev + data.text)
    })

    // Stream complete — finalize message
    const unsubComplete = chatSocketService.onStreamComplete((data) => {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.fullText,
        intent: data.intent,
        timestamp: data.timestamp
      }])
      setStreamingText('')
      setIsTyping(false)
      setProducts(data.products || null)
      setSuggestedPrompts(data.suggestedPrompts || null)

      // Dispatch chat action to global listeners (e.g. POS page)
      if (data.action) {
        window.dispatchEvent(new CustomEvent('posmart:chat_action', { detail: data.action }));
      }
    })

    // Typing indicator
    const unsubTyping = chatSocketService.onTyping((data) => {
      setIsTyping(data.is_typing)
    })

    // Error handler
    const unsubError = chatSocketService.onError((data) => {
      setError(data.error?.message || 'Unknown error')
      setIsTyping(false)
      setStreamingText('')
    })

    // Auto-join session on first connect
    const handleFirstConnect = () => {
      if (!initializedRef.current) {
        initializedRef.current = true
        const savedSessionId = localStorage.getItem(getStorageKey())
        chatSocketService.joinSession(savedSessionId ? parseInt(savedSessionId) : null)
      }
    }

    if (socket.connected) {
      handleFirstConnect()
    } else {
      socket.once('connect', handleFirstConnect)
    }

    return () => {
      socket.off('connect', handleConnect)
      socket.off('disconnect', handleDisconnect)
      socket.off('reconnect_failed', handleReconnectFailed)
      socket.off('connect', handleFirstConnect)
      unsubReady()
      unsubChunk()
      unsubComplete()
      unsubTyping()
      unsubError()
    }
  }, [getStorageKey])

  // ── Actions ──
  const toggleChat = useCallback(() => {
    setIsOpen(prev => !prev)
  }, [])

  const sendMessage = useCallback((text) => {
    if (!canSend || !sessionId || !text.trim()) return

    // Add user message immediately
    setMessages(prev => [...prev, {
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toISOString()
    }])

    setIsTyping(true)
    setStreamingText('')
    setProducts(null)
    setSuggestedPrompts(null)
    setError(null)

    chatSocketService.sendMessage(sessionId, text.trim())
  }, [canSend, sessionId])

  const endSession = useCallback(() => {
    if (sessionId) {
      chatSocketService.endSession(sessionId)
      setSessionId(null)
      setMessages([])
      setProducts(null)
      localStorage.removeItem(getStorageKey())
    }
  }, [sessionId, getStorageKey])

  const startNewSession = useCallback(() => {
    setMessages([])
    setProducts(null)
    setError(null)
    initializedRef.current = false
    chatSocketService.joinSession(null)
  }, [])

  const value = {
    isOpen,
    sessionId,
    messages,
    streamingText,
    isTyping,
    isConnected,
    canSend,
    products,
    suggestedPrompts,
    error,
    toggleChat,
    sendMessage,
    endSession,
    startNewSession,
    setIsOpen
  }

  return (
    <ChatContext.Provider value={value}>
      {children}
    </ChatContext.Provider>
  )
}

export const useChat = () => {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within ChatProvider')
  }
  return context
}

export default ChatContext
