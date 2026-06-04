import { io } from 'socket.io-client'

/**
 * Chat Socket.IO Service (Singleton) — Customer Edition
 * Supports dual-auth: JWT (customerToken) or guestId (UUID)
 * Connection: /ws/chat → nginx → chatbot:3008
 */
class ChatSocketService {
  constructor() {
    this.socket = null
    this.connected = false
  }

  connect(token, guestId) {
    const authKey = token || guestId;
    if (this.socket?.connected) {
      if (this._lastAuthKey === authKey) return this.socket;
      console.log('[CustomerChat] Identity changed, forcing reconnection');
      this.disconnect();
    }
    this._lastAuthKey = authKey;

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
        console.warn('[CustomerChat] Invalid VITE_API_URL, falling back to origin.', error)
      }
    }

    this.socket = io(wsUrl, {
      path: '/ws/chat',
      auth: token ? { token } : { guestId },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: 10
    })

    this.socket.on('connect', () => {
      this.connected = true
      console.log('[CustomerChat] Connected:', this.socket.id)
    })

    this.socket.on('disconnect', (reason) => {
      this.connected = false
      console.log('[CustomerChat] Disconnected:', reason)
    })

    this.socket.on('connect_error', (err) => {
      console.error('[CustomerChat] Connection error:', err.message)
    })

    return this.socket
  }

  getSocket() {
    return this.socket
  }

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

  disconnect() {
    if (this.socket) {
      this.socket.removeAllListeners()
      this.socket.disconnect()
      this.socket = null
      this.connected = false
    }
  }
}

const chatSocketService = new ChatSocketService()
export default chatSocketService
