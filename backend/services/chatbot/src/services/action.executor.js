/**
 * Action Executor for Chatbot Action Assistant
 * Gateway for checking permissions, ownership, confirmation requirements, and audit logging.
 */

const { ACTION_TYPES, CONFIRM_REQUIRED } = require('./action.types');
const logger = require('../../../../shared/common/logger');

const DOWNSTREAM_TIMEOUT_MS = 5000;

function withTimeout(promise, ms = DOWNSTREAM_TIMEOUT_MS) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error(`Downstream API timeout after ${ms}ms`)), ms)
    )
  ]);
}

class ActionExecutor {
  constructor(apiClient = null, chatRepo = null) {
    this.apiClient = apiClient;
    this.chatRepo = chatRepo;
    // Temporary database in-memory mock for rate limiting
    this.writeLimitMap = new Map();
  }

  /**
   * Check if the user session has permissions to execute actionType
   * @param {object} session 
   * @param {string} actionType 
   * @returns {boolean}
   */
  checkPermission(session, actionType) {
    if (!session || !actionType) return false;

    const userType = session.userType || session.user_type || 'customer';

    // POS-specific write actions
    const employeeOnlyActions = [
      ACTION_TYPES.POS_ADD_ITEM,
      ACTION_TYPES.CREATE_ORDER,
      ACTION_TYPES.UPDATE_ORDER
    ];

    if (employeeOnlyActions.includes(actionType) && userType !== 'employee') {
      logger.warn({ actionType, userType, sessionId: session.id }, 'Permission check failed: Employee-only action attempted by non-employee');
      return false;
    }

    return true;
  }

  /**
   * Check if customer owns the resource (e.g. order)
   * Wait for implementation detailing order fetch from order service
   * @param {object} session 
   * @param {string} actionType 
   * @param {object} payload 
   * @returns {Promise<boolean>}
   */
  async checkOwnership(session, actionType, payload) {
    // Employees bypass ownership validation
    const userType = session.userType || session.user_type || 'customer';
    if (userType === 'employee') return true;

    if (actionType === ACTION_TYPES.CANCEL_ORDER || actionType === ACTION_TYPES.TRACK_ORDER) {
      const orderId = payload.orderId;
      if (!orderId) return false;

      if (!this.apiClient) {
        logger.warn({ orderId }, 'ApiClient not available for ownership check, falling back to false');
        return false;
      }

      const response = await withTimeout(this.apiClient.getOrderById(orderId));
      if (!response || !response.success || !response.data) {
        logger.warn({ orderId }, 'Failed to fetch order for ownership validation');
        return false;
      }

      const order = response.data;
      const customerId = session.userId || session.user_id;

      // Ensure customer only modifies their own order
      if (Number(order.customerId || order.customer_id) !== Number(customerId)) {
        logger.warn({ orderId, orderCustomerId: order.customerId, sessionCustomerId: customerId }, 'Ownership check failed: Customer does not own the order');
        return false;
      }
    }

    return true;
  }

  /**
   * Determine if action type requires confirmation before executing
   * @param {string} actionType 
   * @returns {boolean}
   */
  requireConfirmation(actionType) {
    return CONFIRM_REQUIRED.includes(actionType);
  }

  /**
   * Check rate limiting: max 5 write actions / session / 5 minutes
   * @param {number} sessionId 
   * @returns {boolean}
   */
  checkRateLimit(sessionId) {
    const now = Date.now();
    const timeframeMs = 5 * 60 * 1000; // 5 minutes

    if (!this.writeLimitMap.has(sessionId)) {
      this.writeLimitMap.set(sessionId, []);
    }

    const timestamps = this.writeLimitMap.get(sessionId);
    // Clean up expired timestamps
    const activeTimestamps = timestamps.filter(ts => now - ts < timeframeMs);

    if (activeTimestamps.length >= 5) {
      logger.warn({ sessionId, count: activeTimestamps.length }, 'Rate limit exceeded for write actions');
      return false;
    }

    activeTimestamps.push(now);
    this.writeLimitMap.set(sessionId, activeTimestamps);
    return true;
  }

  /**
   * Execute an action after traversing permissions, ownership and confirmations checkpoints
   * @param {object} session 
   * @param {string} actionType 
   * @param {object} payload 
   * @returns {Promise<object>}
   */
  async execute(session, actionType, payload) {
    const sessionId = session.id;
    const userId = session.userId || session.user_id;

    // 1. Rate Limiting Check
    if (!this.checkRateLimit(sessionId)) {
      return { success: false, error: 'Rate limit exceeded. Please try again after 5 minutes.' };
    }

    // 2. Permission Check
    if (!this.checkPermission(session, actionType)) {
      return { success: false, error: 'Access denied: You do not have permission to perform this action.' };
    }

    // 3. Ownership Check
    const isOwner = await this.checkOwnership(session, actionType, payload);
    if (!isOwner) {
      return { success: false, error: 'Access denied: You are not authorized to modify this resource.' };
    }

    // 4. Confirmation Routing
    if (this.requireConfirmation(actionType) && !payload.confirmed) {
      // Setup confirmation payload
      return {
        success: true,
        requiresConfirmation: true,
        message: 'This operation requires your confirmation.',
        action: {
          type: actionType,
          payload
        }
      };
    }

    // 5. Downstream API execution
    let apiResult = null;
    try {
      if (!this.apiClient) {
        return { success: false, error: 'API Client not configured' };
      }

      switch (actionType) {
        case ACTION_TYPES.CANCEL_ORDER:
          apiResult = await withTimeout(this.apiClient.cancelOrder(payload.orderId));
          break;
        case ACTION_TYPES.CREATE_ORDER:
          apiResult = await withTimeout(this.apiClient.createOrder(payload.orderData));
          break;
        case ACTION_TYPES.UPDATE_ORDER:
          apiResult = await withTimeout(this.apiClient.updateOrderItems(payload.orderId, payload.items));
          break;
        default:
          // Client-side actions do not hit API downstream immediately.
          // Return success with action instruction for frontend dispatch.
          apiResult = { success: true, data: { actionExecuted: 'client_delegated' } };
          break;
      }
    } catch (error) {
      logger.error({ error, actionType, payload }, 'Execution failed in downstream service');
      apiResult = { success: false, error: 'Failed to communicate with downstream microservice: ' + error.message };
    }

    // 6. DB Audit Log (Skeleton)
    await this.auditLog(userId, sessionId, actionType, payload, apiResult);

    return apiResult;
  }

  /**
   * Logs write operations to the audit log table
   * @param {number} userId 
   * @param {number} sessionId 
   * @param {string} actionType 
   * @param {object} payload 
   * @param {object} result 
   */
  async auditLog(userId, sessionId, actionType, payload, result) {
    logger.info({ userId, sessionId, actionType, payload, result }, 'Action Audit Log Entry');
    if (this.chatRepo && typeof this.chatRepo.createAuditLog === 'function') {
      try {
        await this.chatRepo.createAuditLog(userId, sessionId, actionType, payload, result);
      } catch (err) {
        logger.error({ err }, 'Failed to save audit log entry to database');
      }
    }
  }
}

module.exports = ActionExecutor;
