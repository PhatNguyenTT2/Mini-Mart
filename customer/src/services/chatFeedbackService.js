import api from './api'

/**
 * Chatbot Feedback Service — Fire-and-forget tracking
 * Tracks recommendation funnel: clicked → added_to_cart
 * Purchase tracking is handled by backend ORDER_CONFIRMED subscriber
 * 
 * Endpoint: POST /chatbot/feedback (matches Phase 4 feedback.routes.js)
 */
const chatFeedbackService = {
  /**
   * Track product click from chatbot recommendation
   * @param {number} productId
   * @param {number} storeId
   * @param {string} source - recommendation source (CF, apriori, content, etc.)
   */
  trackClick: (productId, storeId, source) => {
    api.post('/chatbot/feedback', {
      productId,
      storeId,
      source,
      action: 'clicked'
    }).catch(() => {}) // Fire-and-forget
  },

  /**
   * Track add-to-cart from chatbot recommendation
   * @param {number} productId
   * @param {number} storeId
   * @param {string} source
   */
  trackAddToCart: (productId, storeId, source) => {
    api.post('/chatbot/feedback', {
      productId,
      storeId,
      source,
      action: 'added_to_cart'
    }).catch(() => {})
  },

  /**
   * Track hover dwell (>=1.5s) on recommended product
   * @param {number} productId
   * @param {number} storeId
   * @param {string} source - recommendation source
   * @param {number} dwellTimeMs - actual dwell duration in ms
   */
  trackHover: (productId, storeId, source, dwellTimeMs) => {
    api.post('/chatbot/feedback', {
      productId,
      storeId,
      source,
      action: 'hovered',
      dwellTimeMs
    }).catch(() => {})
  }
}

export default chatFeedbackService
