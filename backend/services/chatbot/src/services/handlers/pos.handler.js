/**
 * POS Handler — Employee-only POS operations.
 * Handles: POS_ADD_ITEM, CREATE_ORDER, PAYMENT_CHECK.
 */

const logger = require('../../../../../shared/common/logger');

class PosHandler {
  constructor(ctx) {
    this.chatRepo = ctx.chatRepo;
    this.apiClient = ctx.apiClient;
    this.ragService = ctx.ragService;
    this.utils = ctx.utils;
    this.actionExecutor = ctx.utils.actionExecutor;
  }

  async handlePosAddItem(session, userMessage) {
    const sessionId = session.id;
    const storeId = session.store_id || 1;
    const metadata = session.metadata || {};

    let { quantity, productKeyword } = this.utils.extractQuantityAndProduct(userMessage);

    let productCandidates = [];
    let isAmbiguous = false;

    const isPronoun = !productKeyword || ['nó', 'cái đó', 'cái này', 'sản phẩm đó', 'sản phẩm này', 'đó', 'này'].some(p => (productKeyword || '').toLowerCase().includes(p));

    if (isPronoun) {
      const lastMentioned = metadata.lastMentionedProducts || [];
      if (lastMentioned.length === 1) {
        const resolved = lastMentioned[0];
        return this.executePosAddItem(session, resolved, quantity);
      } else if (lastMentioned.length > 1) {
        productCandidates = lastMentioned;
        isAmbiguous = true;
      } else {
        return {
          intent: 'POS_ADD_ITEM',
          reply: 'Tôi chưa rõ bạn muốn thêm sản phẩm nào vào đơn POS. Vui lòng nói tên sản phẩm.',
          products: null
        };
      }
    } else {
      const resolved = await this.utils.resolveProductsByRAG(productKeyword, storeId, 5);
      productCandidates = resolved.products;
      if (productCandidates.length === 0) {
        return {
          intent: 'POS_ADD_ITEM',
          reply: `Không tìm thấy sản phẩm nào khớp với từ khóa "${productKeyword}" để thêm vào đơn POS.`,
          products: null
        };
      } else if (productCandidates.length > 1) {
        const topScore = productCandidates[0]._ragScore || 0;
        const secondScore = productCandidates[1]._ragScore || 0;
        if (topScore >= 0.75 && (topScore - secondScore) >= 0.1) {
          isAmbiguous = false;
        } else {
          isAmbiguous = true;
        }
      }
    }

    if (isAmbiguous) {
      metadata.pendingAction = {
        type: 'POS_ADD_ITEM',
        state: 'CLARIFYING',
        data: {
          quantity,
          candidates: productCandidates.map(p => ({
            id: p.id,
            name: p.name,
            unitPrice: p.unitPrice || p.price || p.unit_price
          }))
        }
      };
      await this.chatRepo.updateSessionMetadata(sessionId, metadata);

      const list = productCandidates.map((p, i) => `[${i + 1}] ${p.name} (${Number(p.unitPrice || p.price || p.unit_price).toLocaleString('vi-VN')}đ)`).join('\n');
      return {
        intent: 'POS_ADD_ITEM',
        reply: `Tôi tìm thấy một vài sản phẩm phù hợp. Bạn muốn thêm sản phẩm nào vào POS?\n${list}`,
        products: productCandidates
      };
    }

    return this.executePosAddItem(session, productCandidates[0], quantity);
  }

  async executePosAddItem(session, product, quantity) {
    const actionPayload = {
      productId: product.id,
      quantity,
      name: product.name,
      price: product.unitPrice || product.price || product.unit_price,
      isPerishable: product.isPerishable || product.is_perishable || false
    };

    const result = await this.actionExecutor.execute(session, 'POS_ADD_ITEM', actionPayload);
    if (!result.success) {
      return {
        intent: 'POS_ADD_ITEM',
        reply: `Thêm vào POS thất bại: ${result.error}`,
        products: null
      };
    }

    return {
      intent: 'POS_ADD_ITEM',
      reply: `Đã thêm ${quantity} "${product.name}" vào POS thành công.`,
      products: [{
        ...product,
        quantityOnShelf: result.data?.quantityOnShelf ?? product.quantityOnShelf
      }],
      action: {
        type: 'POS_ADD_ITEM',
        payload: actionPayload
      }
    };
  }

  async processOrderCollection(session, userMessage, context = {}) {
    const sessionId = session.id;
    const storeId = session.store_id || 1;
    const metadata = session.metadata || {};

    const lowerMsg = userMessage.toLowerCase().trim();
    const cleanMsg = lowerMsg.replace(/^(tạo đơn|lập hóa đơn|đặt hàng)\b/, '').trim();

    if (cleanMsg.length === 0) {
      metadata.pendingAction = {
        type: 'CREATE_ORDER',
        state: 'COLLECTING',
        data: { items: [] }
      };
      await this.chatRepo.updateSessionMetadata(sessionId, metadata);
      return {
        intent: 'CREATE_ORDER',
        reply: 'Vui lòng cung cấp danh sách sản phẩm và số lượng cần tạo đơn (ví dụ: "2 Coca, 1 Sting").',
        products: null
      };
    }

    const parts = cleanMsg.split(/[,;\n]/);
    const items = [];

    for (const part of parts) {
      const trimmed = part.trim();
      if (!trimmed) continue;

      const match = trimmed.match(/^(\d+)\s+(.+)$/) || trimmed.match(/^(.+)\s+(\d+)$/);
      let quantity = 1;
      let productKeyword = trimmed;

      if (match) {
        if (trimmed.match(/^(\d+)/)) {
          quantity = parseInt(match[1], 10);
          productKeyword = match[2].trim();
        } else {
          productKeyword = match[1].trim();
          quantity = parseInt(match[2], 10);
        }
      }

      productKeyword = productKeyword.replace(/^(hộp|lon|chai|gói|cái|chiếc)\s+/i, '').trim();

      if (productKeyword) {
        const resolved = await this.utils.resolveProductsByRAG(productKeyword, storeId, 1);
        if (resolved.products && resolved.products.length > 0) {
          const p = resolved.products[0];
          items.push({
            productId: p.id,
            name: p.name,
            quantity,
            price: p.unitPrice || p.price || p.unit_price
          });
        }
      }
    }

    if (items.length === 0) {
      return {
        intent: 'CREATE_ORDER',
        reply: 'Không thể nhận diện sản phẩm trong yêu cầu của bạn. Vui lòng thử lại với định dạng: "Số lượng + Tên sản phẩm" (ví dụ: "2 Coca").',
        products: null
      };
    }

    const isCustomer = session.userType === 'customer' || session.user_type === 'customer';
    const customerId = isCustomer
      ? session.user_id
      : ((context && context.selectedCustomer && context.selectedCustomer.id !== 'virtual-guest')
        ? context.selectedCustomer.id
        : null);

    const actionPayload = {
      orderData: {
        customer_id: customerId,
        delivery_type: 'pickup',
        items: items.map(it => ({
          product_id: it.productId,
          product_name: it.name,
          quantity: it.quantity,
          unit_price: it.price
        }))
      },
      items
    };

    const result = await this.actionExecutor.execute(session, 'CREATE_ORDER', actionPayload);

    if (result.requiresConfirmation) {
      metadata.pendingAction = {
        type: 'CREATE_ORDER',
        state: 'CONFIRMING',
        data: actionPayload
      };
      await this.chatRepo.updateSessionMetadata(sessionId, metadata);

      const itemListStr = items.map(it => `- ${it.name} x${it.quantity}`).join('\n');
      return {
        intent: 'CREATE_ORDER',
        reply: `Bạn có chắc muốn tạo đơn hàng mới với các sản phẩm sau không?\n${itemListStr}\nVui lòng nhập "Đồng ý" hoặc "Hủy bỏ".`,
        products: null
      };
    }

    return {
      intent: 'CREATE_ORDER',
      reply: `Đơn hàng mới đã được tạo thành công: ID #${result.id || result.orderId}`,
      action: { type: 'CREATE_ORDER', payload: actionPayload }
    };
  }

  async handlePosHoldOrder(session, userMessage) {
    return {
      intent: 'POS_HOLD_ORDER',
      reply: 'Đang gửi yêu cầu lưu hóa đơn tạm (Hold Order) lên POS...',
      action: { type: 'POS_HOLD_ORDER' },
      products: null
    };
  }

  async handlePosCheckout(session, userMessage) {
    return {
      intent: 'POS_CHECKOUT',
      reply: 'Đang xử lý kích hoạt giao diện thanh toán (Payment) trên POS...',
      action: { type: 'POS_CHECKOUT' },
      products: null
    };
  }

  async handlePaymentCheck(session, userMessage) {
    if (!this.apiClient) {
      return {
        intent: 'PAYMENT_CHECK',
        reply: 'Dịch vụ thanh toán chưa được định cấu hình.',
        products: null
      };
    }

    const match = userMessage.match(/#?(\d+)/);
    const orderId = match ? parseInt(match[1], 10) : null;

    if (!orderId) {
      return {
        intent: 'PAYMENT_CHECK',
        reply: 'Vui lòng cung cấp mã đơn hàng cần kiểm tra thanh toán (ví dụ: "Kiểm tra thanh toán đơn #123").',
        products: null
      };
    }

    try {
      const orderRes = await this.apiClient.getOrderById(orderId);
      if (!orderRes || !orderRes.success || !orderRes.data) {
        return {
          intent: 'PAYMENT_CHECK',
          reply: `Không tìm thấy đơn hàng #${orderId}.`,
          products: null
        };
      }

      const status = orderRes.data.paymentStatus || orderRes.data.payment_status || 'unpaid';
      const statusMap = {
        paid: 'Đã thanh toán',
        unpaid: 'Chưa thanh toán',
        refunded: 'Đã hoàn tiền'
      };

      const translateStatus = statusMap[status] || status;

      return {
        intent: 'PAYMENT_CHECK',
        reply: `Trạng thái thanh toán của đơn hàng #${orderId} hiện tại là: **${translateStatus}**.`,
        products: null
      };
    } catch (err) {
      return {
        intent: 'PAYMENT_CHECK',
        reply: `Kiểm tra thanh toán thất bại: ${err.message}`,
        products: null
      };
    }
  }
}

module.exports = PosHandler;
