/**
 * AIClient — Node.js Client with Circuit Breaker Pattern
 * 
 * Communicates with Python FastAPI AI Inference Service (ONNX Two-Tower Model).
 * Circuit Breaker States:
 *   - CLOSED: Normal operation, forwards requests to FastAPI.
 *   - OPEN: FastAPI is unreachable or failing. Immediately trips to fallback (returns null).
 *   - HALF_OPEN: Probe state after 30s reset timeout. Tests 1 request to check recovery.
 */
const logger = require('../../../../shared/common/logger');

class AIClient {
  constructor(baseUrl = process.env.AI_SERVICE_URL || 'http://localhost:8000', options = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.timeoutMs = options.timeoutMs ?? 300;
    this.failureThreshold = options.failureThreshold ?? 3;
    this.resetTimeoutMs = options.resetTimeoutMs ?? 30000;

    this.state = 'CLOSED'; // 'CLOSED' | 'OPEN' | 'HALF_OPEN'
    this.failureCount = 0;
    this.nextAttemptTime = 0;
    this.manuallyDisabled = false;
  }

  disable() {
    this.manuallyDisabled = true;
    logger.info('AIClient manually DISABLED by admin toggle');
  }

  enable() {
    this.manuallyDisabled = false;
    logger.info('AIClient manually ENABLED by admin toggle');
  }

  isDisabled() {
    return this.manuallyDisabled;
  }

  /**
   * Score candidate products using Deep Neural Two-Tower ONNX Model
   * 
   * @param {object} request
   * @param {number} request.storeId
   * @param {number|null} request.userId
   * @param {number|null} request.personaCluster
   * @param {number[]} request.candidateProductIds
   * @param {number|null} request.contextProductId
   * @returns {Promise<Array<{product_id: number, ai_score: number}>|null>} Null signals fallback
   */
  async scoreProducts({
    storeId,
    userId = null,
    personaCluster = null,
    candidateProductIds = [],
    contextProductId = null
  }) {
    if (!candidateProductIds || candidateProductIds.length === 0) {
      return [];
    }

    // Manual Disable Guard (Demo Fallback Toggle)
    if (this.manuallyDisabled) {
      logger.debug('AIClient is manually DISABLED — skipping AI Service (using Fallback)');
      return null;
    }

    // Circuit Breaker State Guard
    if (this.state === 'OPEN') {
      if (Date.now() >= this.nextAttemptTime) {
        this.state = 'HALF_OPEN';
        logger.info('AIClient Circuit Breaker entering HALF_OPEN probe state');
      } else {
        logger.debug('AIClient Circuit Breaker is OPEN — skipping AI Service (using Fallback)');
        return null;
      }
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const normalizedStoreId = Number(storeId);
      const normalizedCandidates = candidateProductIds.map(Number);
      if (!Number.isInteger(normalizedStoreId) || normalizedStoreId <= 0) {
        throw new TypeError('storeId must be a positive integer');
      }
      if (normalizedCandidates.length > 256 || normalizedCandidates.some(
        value => !Number.isInteger(value) || value <= 0
      ) || new Set(normalizedCandidates).size !== normalizedCandidates.length) {
        throw new TypeError('candidateProductIds must contain 1-256 unique positive integers');
      }
      const normalizedUserId = userId == null ? null : Number(userId);
      const normalizedPersona = personaCluster == null ? null : Number(personaCluster);
      const normalizedContext = contextProductId == null ? null : Number(contextProductId);
      if (normalizedUserId !== null && (!Number.isInteger(normalizedUserId) || normalizedUserId <= 0)) {
        throw new TypeError('userId must be null or a positive integer');
      }
      if (normalizedPersona !== null && (
        !Number.isInteger(normalizedPersona) || normalizedPersona < 0 || normalizedPersona > 7
      )) {
        throw new TypeError('personaCluster must be null or an integer from 0 to 7');
      }
      if (normalizedContext !== null && (!Number.isInteger(normalizedContext) || normalizedContext <= 0)) {
        throw new TypeError('contextProductId must be null or a positive integer');
      }

      const response = await fetch(`${this.baseUrl}/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          store_id: normalizedStoreId,
          user_id: normalizedUserId,
          persona_cluster: normalizedPersona,
          candidate_product_ids: normalizedCandidates,
          context_product_id: normalizedContext
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      const rankings = data?.rankings;
      if (!Array.isArray(rankings) || rankings.length !== normalizedCandidates.length) {
        throw new Error('AI response does not contain every requested candidate');
      }
      const expected = new Set(normalizedCandidates);
      const returned = new Set();
      const returnedRanks = new Set();
      for (const ranking of rankings) {
        const productId = Number(ranking?.product_id);
        const score = ranking?.ai_score;
        const rank = Number(ranking?.rank);
        if (
          !expected.has(productId) || returned.has(productId)
          || typeof score !== 'number' || !Number.isFinite(score)
          || !Number.isInteger(rank) || rank < 1 || rank > rankings.length
          || returnedRanks.has(rank)
        ) {
          throw new Error('AI response contains unknown, duplicate, or non-finite ranking data');
        }
        returned.add(productId);
        returnedRanks.add(rank);
      }

      // Request Succeeded -> Reset Circuit Breaker to CLOSED
      if (this.state !== 'CLOSED') {
        logger.info(`AIClient Circuit Breaker restored to CLOSED state (Latency: ${data.inference_ms}ms)`);
      }
      this.state = 'CLOSED';
      this.failureCount = 0;

      return rankings;

    } catch (err) {
      this._handleFailure(err);
      return null; // Return null to trigger Graceful Fallback
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Handle request failure and update Circuit Breaker state
   */
  _handleFailure(err) {
    this.failureCount++;
    const isTimeout = err.name === 'AbortError';
    logger.warn({
      err: err.message,
      isTimeout,
      failureCount: this.failureCount,
      threshold: this.failureThreshold,
      circuitState: this.state
    }, 'AIClient call failed');

    if (this.state === 'HALF_OPEN' || this.failureCount >= this.failureThreshold) {
      this.state = 'OPEN';
      this.nextAttemptTime = Date.now() + this.resetTimeoutMs;
      logger.error({
        nextAttemptMs: this.resetTimeoutMs,
        reason: err.message
      }, '🚨 AIClient Circuit Breaker TRIPPED to OPEN state! Falling back to White-box Ensemble.');
    }
  }

  /**
   * Health check endpoint probe
   */
  async isHealthy() {
    try {
      const res = await fetch(`${this.baseUrl}/health`, { signal: AbortSignal.timeout(1000) });
      return res.ok;
    } catch {
      return false;
    }
  }

  getState() {
    return {
      state: this.state,
      failureCount: this.failureCount,
      nextAttemptInMs: Math.max(0, this.nextAttemptTime - Date.now())
    };
  }
}

module.exports = AIClient;
