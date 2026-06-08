import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import chatSocketService from '../services/chatSocketService'

const ChatContext = createContext(null)

const SESSION_KEY_PREFIX = 'customer_chat_session'
const GUEST_ID_KEY = 'customer_guest_id'

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
      const token = localStorage.getItem('customerToken')
      if (!token) return null
      const payload = JSON.parse(atob(token.split('.')[1]))
      return payload.id || payload.userId || null
    } catch {
      return null
    }
  }, [])

  const getSessionKey = useCallback(() => {
    const uid = getUserId()
    return uid ? `${SESSION_KEY_PREFIX}_${uid}` : SESSION_KEY_PREFIX
  }, [getUserId])

  const canSend = !isTyping && !streamingText && isConnected

  // ── Lazy Socket connection: only connect when chat is opened ──
  useEffect(() => {
    if (!isOpen) return // Don't connect until user opens the chat widget

    const token = localStorage.getItem('customerToken')

    // Guest fallback: generate UUID if no token
    let guestId = null
    if (!token) {
      guestId = localStorage.getItem(GUEST_ID_KEY)
      if (!guestId) {
        guestId = crypto.randomUUID()
        localStorage.setItem(GUEST_ID_KEY, guestId)
      }
    }

    const socket = chatSocketService.connect(token, guestId)
    if (!socket) return

    const handleConnect = () => setIsConnected(true)
    const handleDisconnect = () => setIsConnected(false)
    const handleReconnectFailed = () => {
      setError('Chat server connection failed. Please reload the page.')
    }
    socket.on('connect', handleConnect)
    socket.on('disconnect', handleDisconnect)
    socket.on('reconnect_failed', handleReconnectFailed)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsConnected(socket.connected)

    const unsubReady = chatSocketService.onSessionReady((data) => {
      setSessionId(data.sessionId)
      setMessages(data.messages?.map(m => ({
        role: m.role,
        content: m.content,
        timestamp: m.created_at
      })) || [])
      setError(null)

      if (!data.restored) {
        localStorage.setItem(getSessionKey(), String(data.sessionId))
      }
    })

    const unsubChunk = chatSocketService.onStreamChunk((data) => {
      setStreamingText(prev => prev + data.text)
    })

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

      // Dispatch action to Customer UI (cart, navigation, etc.)
      if (data.action) {
        window.dispatchEvent(
          new CustomEvent('posmart:customer_chat_action', { detail: data.action })
        );
      }
    })

    const unsubTyping = chatSocketService.onTyping((data) => {
      setIsTyping(data.is_typing)
    })

    const unsubError = chatSocketService.onError((data) => {
      setError(data.error?.message || 'Unknown error')
      setIsTyping(false)
      setStreamingText('')
    })

    // Auto-join session on first connect
    const handleFirstConnect = () => {
      if (!initializedRef.current) {
        initializedRef.current = true
        const savedSessionId = localStorage.getItem(getSessionKey())
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
  }, [isOpen, getSessionKey])

  // ── Actions ──
  const toggleChat = useCallback(() => {
    setIsOpen(prev => !prev)
  }, [])

  const sendMessage = useCallback((text) => {
    if (!canSend || !sessionId || !text.trim()) return

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
      localStorage.removeItem(getSessionKey())
    }
  }, [sessionId, getSessionKey])

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

// eslint-disable-next-line react-refresh/only-export-components
export const useChat = () => {
  const context = useContext(ChatContext)
  if (!context) {
    throw new Error('useChat must be used within ChatProvider')
  }
  return context
}

export default ChatContext
