import { io } from 'socket.io-client'

/**
 * Chat Socket.IO Service (Singleton)
 * Dedicated connection to /ws/chat namespace for real-time chat.
 * Pattern matches existing socketService.js
 */
class ChatSocketService {
  constructor() {
    this.socket = null
    this.connected = false
  }

  /**
   * Connect to chat WebSocket
   * @param {string} token - JWT auth token
   * @returns {import('socket.io-client').Socket}
   */
  connect(token) {
    if (this.socket?.connected) return this.socket

    const apiUrl = import.meta.env.VITE_API_URL
    let wsUrl = undefined
    if (apiUrl) {
      try {
        const parsedUrl = new URL(apiUrl)
        // Auto-upgrade to https if page is HTTPS
        if (window.location.protocol === 'https:' && parsedUrl.protocol === 'http:') {
          parsedUrl.protocol = 'https:'
        }
        wsUrl = parsedUrl.origin
      } catch (error) {
        console.warn('[ChatSocket] Invalid VITE_API_URL, falling back to origin.', error)
      }
    }

    this.socket = io(wsUrl, {
      path: '/ws/chat',
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 10
    })

    this.socket.on('connect', () => {
      this.connected = true
      console.log('[ChatSocket] Connected:', this.socket.id)
    })

    this.socket.on('disconnect', (reason) => {
      this.connected = false
      console.log('[ChatSocket] Disconnected:', reason)
    })

    this.socket.on('connect_error', (err) => {
      console.error('[ChatSocket] Connection error:', err.message)
    })

    return this.socket
  }

  /**
   * Get current socket instance
   * @returns {import('socket.io-client').Socket | null}
   */
  getSocket() {
    return this.socket
  }

  /**
   * Check connection status
   */
  isConnected() {
    return this.connected && this.socket?.connected
  }

  // ── Emit helpers ──

  joinSession(sessionId = null) {
    this.socket?.emit('chat:join_session', { sessionId })
  }

  sendMessage(sessionId, message) {
    this.socket?.emit('chat:send_message', { session_id: sessionId, message })
  }

  endSession(sessionId) {
    this.socket?.emit('chat:end_session', { session_id: sessionId })
  }

  // ── Listen helpers ──

  onSessionReady(cb) {
    this.socket?.on('chat:session_ready', cb)
    return () => this.socket?.off('chat:session_ready', cb)
  }

  onStreamChunk(cb) {
    this.socket?.on('chat:stream_chunk', cb)
    return () => this.socket?.off('chat:stream_chunk', cb)
  }

  onStreamComplete(cb) {
    this.socket?.on('chat:stream_complete', cb)
    return () => this.socket?.off('chat:stream_complete', cb)
  }

  onTyping(cb) {
    this.socket?.on('chat:typing', cb)
    return () => this.socket?.off('chat:typing', cb)
  }

  onError(cb) {
    this.socket?.on('chat:error', cb)
    return () => this.socket?.off('chat:error', cb)
  }

  /**
   * Disconnect and cleanup
   */
  disconnect() {
    if (this.socket) {
      this.socket.removeAllListeners()
      this.socket.disconnect()
      this.socket = null
      this.connected = false
      console.log('[ChatSocket] Disconnected manually')
    }
  }
}

const chatSocketService = new ChatSocketService()
export default chatSocketService
