/**
 * Order Handler — Customer order tracking and cancellation.
 * Handles: TRACK_ORDER, CANCEL_ORDER.
 */

class OrderHandler {
  constructor(ctx) {
    this.chatRepo = ctx.chatRepo;
    this.apiClient = ctx.apiClient;
    this.utils = ctx.utils;
    this.actionExecutor = ctx.utils.actionExecutor;
  }

  async handleTrackOrder(session, message) {
    const orderId = this.utils.extractOrderId(message);
    if (!orderId) {
      return {
        intent: 'TRACK_ORDER',
        reply: 'Vui lòng cung cấp mã đơn hàng cần theo dõi (ví dụ: Đơn hàng #123).',
        products: null
      };
    }

    const actionPayload = { orderId };
    const result = await this.actionExecutor.execute(session, 'TRACK_ORDER', actionPayload);
    if (!result.success) {
      return {
        intent: 'TRACK_ORDER',
        reply: `Không thể theo dõi đơn hàng: ${result.error}`,
        products: null
      };
    }

    const userType = session.userType || session.user_type || 'customer';
    if (userType === 'employee') {
      return {
        intent: 'TRACK_ORDER',
        reply: `Đang mở lịch sử đơn hàng và lọc đến đơn #${orderId}.`,
        products: null,
        action: {
          type: 'OPEN_MODAL',
          payload: { modal: 'POSEmployeeOrdersModal', searchQuery: `ORD-${orderId}` }
        }
      };
    }

    return {
      intent: 'TRACK_ORDER',
      reply: `Đang chuyển hướng bạn đến giao diện chi tiết đơn hàng #${orderId}.`,
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: `/orders/${orderId}` }
      }
    };
  }

  async handleCustomerCancelOrder(session, message) {
    const orderId = this.utils.extractOrderId(message);
    if (!orderId) {
      return {
        intent: 'CANCEL_ORDER',
        reply: 'Vui lòng cung cấp mã đơn hàng cần hủy (ví dụ: Hủy đơn hàng #123).',
        products: null
      };
    }

    const actionPayload = { orderId };
    const confirmResult = await this.actionExecutor.execute(session, 'CANCEL_ORDER', actionPayload);

    if (confirmResult.requiresConfirmation) {
      const metadata = session.metadata || {};
      metadata.pendingAction = {
        type: 'CANCEL_ORDER',
        state: 'CONFIRMING',
        data: actionPayload
      };
      await this.chatRepo.updateSessionMetadata(session.id, metadata);

      return {
        intent: 'CANCEL_ORDER',
        reply: `Bạn có chắc chắn muốn hủy đơn hàng #${orderId} không? Vui lòng nhập "Đồng ý" hoặc "Hủy bỏ".`,
        products: null
      };
    }

    if (!confirmResult.success) {
      return {
        intent: 'CANCEL_ORDER',
        reply: `Không thể hủy đơn hàng #${orderId}: ${confirmResult.error}`,
        products: null
      };
    }

    return {
      intent: 'CANCEL_ORDER',
      reply: `Hủy đơn hàng #${orderId} thành công.`,
      products: null,
      action: {
        type: 'CANCEL_ORDER',
        payload: actionPayload
      }
    };
  }
  handleViewOrderHistory(session) {
    return {
      intent: 'VIEW_ORDER_HISTORY',
      reply: 'Đang mở lịch sử đơn hàng của bạn...',
      products: null,
      action: {
        type: 'OPEN_MODAL',
        payload: { modal: 'POSEmployeeOrdersModal' }
      }
    };
  }
}

module.exports = OrderHandler;
