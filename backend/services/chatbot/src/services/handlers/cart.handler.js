/**
 * Cart Handler — Customer shopping cart operations.
 * Handles: ADD_TO_CART, REMOVE_FROM_CART, UPDATE_CART_ITEM, VIEW_CART, CHECKOUT_GUIDE.
 * All operations use ActionExecutor for permission/audit enforcement.
 */

const logger = require('../../../../../shared/common/logger');

class CartHandler {
  constructor(ctx) {
    this.chatRepo = ctx.chatRepo;
    this.apiClient = ctx.apiClient;
    this.ragService = ctx.ragService;
    this.utils = ctx.utils;
    this.actionExecutor = ctx.utils.actionExecutor;
  }

  async handleAddToCart(session, userMessage) {
    const sessionId = session.id;
    const storeId = session.store_id || 1;
    const metadata = session.metadata || {};

    let { quantity, productKeyword } = this.utils.extractQuantityAndProduct(userMessage);

    // ── Index-based multi-add: "thêm 1, 3 vào giỏ" ──
    const lastMentioned = metadata.lastMentionedProducts || [];
    if (lastMentioned.length > 0) {
      const cleaned = userMessage.toLowerCase()
        .replace(/(?:thêm|bỏ|cho|đưa|để|lấy|mua)\s*/gi, '')
        .replace(/(?:vào\s*)?(?:giỏ\s*(?:hàng)?|đơn\s*(?:hàng)?)/gi, '')
        .replace(/(?:món|cái|sản phẩm|số|thứ tự)/gi, '')
        .replace(/(?:và|với)/g, ',')
        .trim();

      if (/^[0-9,\s]+$/.test(cleaned)) {
        const indices = cleaned.split(/[\s,]+/)
          .map(t => parseInt(t, 10))
          .filter(n => !isNaN(n));

        const allInBounds = indices.length > 0 && indices.every(n => n >= 1 && n <= lastMentioned.length);

        if (allInBounds) {
          return this._executeMultiAdd(session, lastMentioned, indices, quantity);
        }
      }
    }

    let productCandidates = [];
    let isAmbiguous = false;

    const isPronoun = !productKeyword || ['nó', 'cái đó', 'cái này', 'sản phẩm đó', 'sản phẩm này', 'đó', 'này'].some(p => (productKeyword || '').toLowerCase().includes(p));

    if (isPronoun) {
      const lastMentioned = metadata.lastMentionedProducts || [];
      if (lastMentioned.length === 1) {
        productCandidates = [lastMentioned[0]];
      } else if (lastMentioned.length > 1) {
        productCandidates = lastMentioned;
        isAmbiguous = true;
      } else {
        return {
          intent: 'ADD_TO_CART',
          reply: 'Bạn muốn thêm sản phẩm nào vào giỏ hàng? Vui lòng cho biết tên sản phẩm.',
          products: null
        };
      }
    } else {
      const resolved = await this.utils.resolveProductsByRAG(productKeyword, storeId, 5);
      if (!resolved.products.length) {
        return {
          intent: 'ADD_TO_CART',
          reply: `Không tìm thấy sản phẩm "${productKeyword}" tại chi nhánh hiện tại.`,
          products: null
        };
      }
      productCandidates = resolved.products;
      if (productCandidates.length > 1) {
        isAmbiguous = true;
      }
    }

    if (isAmbiguous) {
      metadata.pendingAction = {
        type: 'ADD_TO_CART',
        state: 'CLARIFYING',
        data: { quantity, candidates: productCandidates }
      };
      await this.chatRepo.updateSessionMetadata(sessionId, metadata);

      const list = productCandidates.map((p, i) => `[${i + 1}] ${p.name} (${Number(p.unitPrice || p.price || p.unit_price).toLocaleString('vi-VN')}đ)`).join('\n');
      const reply = `Tôi tìm thấy một vài sản phẩm phù hợp. Bạn muốn thêm sản phẩm nào?\n${list}\nVui lòng phản hồi số thứ tự (ví dụ: [1], [2], hoặc 1, 2).`;
      return {
        intent: 'ADD_TO_CART',
        reply,
        products: productCandidates
      };
    }

    const product = productCandidates[0];
    return this.executeAddToCart(session, product, quantity);
  }

  async executeAddToCart(session, product, quantity) {
    const storeId = session.store_id || 1;

    if (this.apiClient) {
      try {
        const stockResult = await this.apiClient.getInventorySummary(storeId, product.id);
        const items = Array.isArray(stockResult.data) ? stockResult.data : [];
        const stock = items.find(i => String(i.productId || i.id) === String(product.id));
        const onShelf = stock ? (stock.quantityOnShelf || 0) : 0;

        if (onShelf < quantity) {
          return {
            intent: 'ADD_TO_CART',
            reply: `Sản phẩm "${product.name}" hiện chỉ còn ${onShelf} sản phẩm trên kệ, không đủ số lượng ${quantity} yêu cầu.`,
            products: [product]
          };
        }
      } catch (err) {
        logger.warn({ err, productId: product.id }, 'Stock check failed in executeAddToCart, proceeding with caution');
      }
    }

    const actionPayload = {
      productId: product.id,
      quantity,
      name: product.name,
      price: product.unitPrice || product.price || product.unit_price,
      image: product.image || product.image_url || null
    };

    const result = await this.actionExecutor.execute(session, 'ADD_TO_CART', actionPayload);
    if (!result.success) {
      return {
        intent: 'ADD_TO_CART',
        reply: `Không thể thêm vào giỏ hàng: ${result.error}`,
        products: [product]
      };
    }

    // Attributed feedback for single-item add
    this._recordAttributedFeedback(session, product, storeId);

    // Stock re-check after execute (race condition guard)
    let stockWarning = '';
    if (this.apiClient) {
      try {
        const recheck = await this.apiClient.getInventorySummary(storeId, product.id);
        const items = Array.isArray(recheck.data) ? recheck.data : [];
        const stock = items.find(i => String(i.productId || i.id) === String(product.id));
        const currentShelf = stock ? (stock.quantityOnShelf || 0) : 0;
        if (currentShelf < quantity) {
          stockWarning = ` ⚠️ Lưu ý: tồn kho hiện tại (${currentShelf}) thấp hơn số lượng yêu cầu, vui lòng kiểm tra lại.`;
        }
      } catch (err) {
        logger.warn({ err, productId: product.id }, 'Stock re-check failed after ADD_TO_CART execute');
      }
    }

    return {
      intent: 'ADD_TO_CART',
      reply: `Đã thêm ${quantity} "${product.name}" vào giỏ hàng thành công.${stockWarning}`,
      products: [product],
      action: {
        type: 'ADD_TO_CART',
        payload: actionPayload
      }
    };
  }

  async handleRemoveFromCart(session, userMessage) {
    const storeId = session.store_id || 1;
    const { productKeyword } = this.utils.extractQuantityAndProduct(userMessage);

    let productCandidates = [];
    const isPronoun = !productKeyword || ['nó', 'cái đó', 'cái này', 'sản phẩm đó', 'sản phẩm này', 'đó', 'này'].some(p => (productKeyword || '').toLowerCase().includes(p));
    const metadata = session.metadata || {};

    if (isPronoun) {
      const lastMentioned = metadata.lastMentionedProducts || [];
      if (lastMentioned.length === 1) {
        productCandidates = [lastMentioned[0]];
      } else if (lastMentioned.length > 1) {
        productCandidates = lastMentioned;
      } else {
        return {
          intent: 'REMOVE_FROM_CART',
          reply: 'Bạn muốn xóa sản phẩm nào khỏi giỏ hàng? Vui lòng chỉ định tên sản phẩm.',
          products: null
        };
      }
    } else {
      const resolved = await this.utils.resolveProductsByRAG(productKeyword, storeId, 1);
      if (!resolved.products.length) {
        return {
          intent: 'REMOVE_FROM_CART',
          reply: `Không tìm thấy sản phẩm "${productKeyword}" để xóa khỏi giỏ hàng.`,
          products: null
        };
      }
      productCandidates = resolved.products;
    }

    const product = productCandidates[0];
    const actionPayload = {
      productId: product.id,
      name: product.name
    };

    const result = await this.actionExecutor.execute(session, 'REMOVE_FROM_CART', actionPayload);
    if (!result.success) {
      return {
        intent: 'REMOVE_FROM_CART',
        reply: `Không thể xóa khỏi giỏ hàng: ${result.error}`,
        products: [product]
      };
    }

    return {
      intent: 'REMOVE_FROM_CART',
      reply: `Đã xóa "${product.name}" khỏi giỏ hàng.`,
      products: [product],
      action: {
        type: 'REMOVE_FROM_CART',
        payload: actionPayload
      }
    };
  }

  async handleUpdateCartItem(session, userMessage) {
    const storeId = session.store_id || 1;
    const { quantity, productKeyword } = this.utils.extractQuantityAndProduct(userMessage);

    let productCandidates = [];
    const isPronoun = !productKeyword || ['nó', 'cái đó', 'cái này', 'sản phẩm đó', 'sản phẩm này', 'đó', 'này'].some(p => (productKeyword || '').toLowerCase().includes(p));
    const metadata = session.metadata || {};

    if (isPronoun) {
      const lastMentioned = metadata.lastMentionedProducts || [];
      if (lastMentioned.length === 1) {
        productCandidates = [lastMentioned[0]];
      } else {
        return {
          intent: 'UPDATE_CART_ITEM',
          reply: 'Bạn muốn cập nhật số lượng cho sản phẩm nào? Vui lòng nêu tên sản phẩm.',
          products: null
        };
      }
    } else {
      const resolved = await this.utils.resolveProductsByRAG(productKeyword, storeId, 1);
      if (!resolved.products.length) {
        return {
          intent: 'UPDATE_CART_ITEM',
          reply: `Không tìm thấy sản phẩm "${productKeyword}" để thay đổi số lượng.`,
          products: null
        };
      }
      productCandidates = resolved.products;
    }

    const product = productCandidates[0];

    if (this.apiClient) {
      try {
        const stockResult = await this.apiClient.getInventorySummary(storeId, product.id);
        const items = Array.isArray(stockResult.data) ? stockResult.data : [];
        const stock = items.find(i => String(i.productId || i.id) === String(product.id));
        const onShelf = stock ? (stock.quantityOnShelf || 0) : 0;

        if (onShelf < quantity) {
          return {
            intent: 'UPDATE_CART_ITEM',
            reply: `Không thể cập nhật: Sản phẩm "${product.name}" chỉ còn ${onShelf} sản phẩm trên kệ.`,
            products: [product]
          };
        }
      } catch (err) {
        logger.warn({ err, productId: product.id }, 'Stock check failed in handleUpdateCartItem');
      }
    }

    const actionPayload = {
      productId: product.id,
      quantity,
      name: product.name
    };

    const result = await this.actionExecutor.execute(session, 'UPDATE_CART_ITEM', actionPayload);
    if (!result.success) {
      return {
        intent: 'UPDATE_CART_ITEM',
        reply: `Không thể cập nhật số lượng: ${result.error}`,
        products: [product]
      };
    }

    return {
      intent: 'UPDATE_CART_ITEM',
      reply: `Đã cập nhật số lượng sản phẩm "${product.name}" thành ${quantity}.`,
      products: [product],
      action: {
        type: 'UPDATE_CART_ITEM',
        payload: actionPayload
      }
    };
  }

  handleViewCart(session) {
    return {
      intent: 'VIEW_CART',
      reply: 'Dưới đây là giỏ hàng hiện tại của bạn.',
      products: null,
      action: {
        type: 'VIEW_CART',
        payload: {}
      }
    };
  }

  handleCheckoutGuide(session) {
    return {
      intent: 'CHECKOUT_GUIDE',
      reply: 'Để thanh toán đơn hàng, bạn vui lòng nhấn vào nút "Thanh toán" ở góc phải giỏ hàng hoặc truy cập trực tiếp đường dẫn bên dưới.',
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: '/checkout' }
      }
    };
  }

  async _executeMultiAdd(session, lastMentioned, indices, quantity) {
    const storeId = session.store_id || 1;
    const items = [];
    const failedItems = [];
    const addedProducts = [];

    for (const idx of indices) {
      const product = lastMentioned[idx - 1];
      const result = await this.actionExecutor.execute(session, 'ADD_TO_CART', {
        productId: product.id,
        quantity,
        name: product.name,
        price: product.unitPrice || product.price || product.unit_price,
        image: product.image || null
      });

      if (result.success) {
        items.push({
          productId: product.id,
          name: product.name,
          price: product.unitPrice || product.price || product.unit_price,
          image: product.image || null,
          quantity
        });
        addedProducts.push(product);

        // Attributed feedback
        this._recordAttributedFeedback(session, product, storeId);
      } else {
        failedItems.push(product.name);
      }
    }

    if (items.length === 0) {
      return {
        intent: 'ADD_TO_CART',
        reply: `Không thể thêm sản phẩm vào giỏ hàng: ${failedItems.join(', ')}.`,
        products: null
      };
    }

    const names = items.map(i => `"${i.name}"`).join(', ');
    let reply = `Đã thêm ${items.length} sản phẩm vào giỏ hàng: ${names}.`;
    if (failedItems.length > 0) {
      reply += ` ⚠️ Không thể thêm: ${failedItems.join(', ')}.`;
    }

    return {
      intent: 'ADD_TO_CART',
      reply,
      products: addedProducts,
      action: {
        type: 'ADD_TO_CART',
        payload: { items }
      }
    };
  }

  _recordAttributedFeedback(session, product, storeId) {
    try {
      const hybridService = this.ragService?.hybridService;
      if (!hybridService) return;

      const customerId = session.metadata?.customerId || session.user_id;
      const parsedId = (customerId && !String(customerId).startsWith('guest_'))
        ? Number(customerId) : null;

      hybridService.recordFeedback(
        parsedId,
        product.id,
        storeId,
        product.topSource || 'content',
        'added_to_cart',
        String(session.id)
      ).catch(err => logger.warn({ err }, 'Feedback recording failed (non-critical)'));
    } catch (err) {
      logger.warn({ err }, 'Feedback attribution error (non-critical)');
    }
  }
}

module.exports = CartHandler;
