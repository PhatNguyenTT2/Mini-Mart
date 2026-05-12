import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import chatSocketService from '../services/chatSocketService'

const ChatContext = createContext(null)

const STORAGE_KEY = 'posmart_chat_session'

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

  // Computed: can user send a message?
  const canSend = !isTyping && !streamingText && isConnected

  // ── Socket connection + event listeners ──
  useEffect(() => {
    const token = localStorage.getItem('adminToken')
    if (!token) return

    const socket = chatSocketService.connect(token)
    if (!socket) return

    // Connection state tracking (Edge Case B)
    const handleConnect = () => setIsConnected(true)
    const handleDisconnect = () => setIsConnected(false)
    socket.on('connect', handleConnect)
    socket.on('disconnect', handleDisconnect)
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
        localStorage.setItem(STORAGE_KEY, String(data.sessionId))
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
        const savedSessionId = localStorage.getItem(STORAGE_KEY)
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
      socket.off('connect', handleFirstConnect)
      unsubReady()
      unsubChunk()
      unsubComplete()
      unsubTyping()
      unsubError()
    }
  }, [])

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
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [sessionId])

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
