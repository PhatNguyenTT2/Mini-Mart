/**
 * Read Handler — Read-only data query handlers.
 * Handles: CHECK_STOCK, CHECK_PRICE, ORDER_STATUS, SEARCH_PRODUCT, RECOMMENDATION.
 * These intents never mutate data, only query microservices.
 */

const { getPersonalizationContext, getCoPurchaseHint } = require('../context.helper');
const logger = require('../../../../../shared/common/logger');

class ReadHandler {
  constructor(ctx) {
    this.chatRepo = ctx.chatRepo;
    this.hfClient = ctx.hfClient;
    this.apiClient = ctx.apiClient;
    this.ragService = ctx.ragService;
    this.copurchaseRepo = ctx.copurchaseRepo;
    this.utils = ctx.utils;
  }

  async handleRecommendation(session, userMessage, intentMeta = {}) {
    if (this.ragService === undefined && process.env.NODE_ENV !== 'test') {
      // RAG model is loading (~87s on cold start). Wait with polling instead of fallback.
      const maxWaitMs = 90_000;
      const pollMs = 3_000;
      const start = Date.now();
      logger.info({ sessionId: session.id }, 'RAG not ready yet, waiting for hot-swap...');
      while (Date.now() - start < maxWaitMs) {
        await new Promise(r => setTimeout(r, pollMs));
        if (this.ragService) break;
      }
      if (!this.ragService) {
        logger.warn({ sessionId: session.id }, 'RAG still not ready after timeout, using fallback');
        return this.handleSearchProductFallback(session.id, userMessage);
      }
    } else if (!this.ragService) {
      return this.handleSearchProductFallback(session.id, userMessage);
    }

    const storeId = session.store_id || 1;
    const customerId = session.user_type === 'customer'
      ? (session.metadata?.customerId || session.user_id)
      : null;
    const chatHistory = await this.utils.getRecentHistory(session.id);

    const result = (intentMeta && intentMeta.isTransactional)
      ? await this.ragService.recommend(userMessage, storeId, customerId, chatHistory, intentMeta)
      : await this.ragService.recommend(userMessage, storeId, customerId, chatHistory);

    return {
      content: result.content,
      products: result.products,
      ragMetadata: result.metadata
    };
  }

  async handleCheckStock(session, userMessage) {
    const sessionId = session.id;
    const storeId = session.store_id || 1;
    const isCustomer = session.user_type === 'customer';
    const keyword = this.utils.extractKeyword(userMessage, ['tồn kho', 'còn hàng', 'còn không', 'hết hàng', 'có còn', 'còn bao nhiêu', 'còn', 'stock']);

    if (!this.apiClient) return this.utils.fallbackNoApi('CHECK_STOCK', keyword);

    // 1. Pronoun fallback resolution
    // NOTE: Cannot use \b word boundaries — JS treats Vietnamese diacritics (ệ,ê,ô) as non-\w
    let product = null;
    const pronouns = ['nó', 'cái đó', 'cái này', 'sản phẩm đó', 'sản phẩm này', 'đó', 'này', 'kệ', 'trên kệ', 'bao nhiêu'];
    const kwLower = (keyword || '').toLowerCase();
    const isPronoun = !keyword || keyword === userMessage
      || pronouns.some(p => kwLower === p || kwLower.includes(p));

    if (isPronoun) {
      const lastMentioned = session.metadata?.lastMentionedProducts || [];
      if (lastMentioned.length > 0) {
        product = lastMentioned[0];
      } else {
        return {
          intent: 'CHECK_STOCK',
          reply: 'Bạn muốn kiểm tra tồn kho sản phẩm nào? Vui lòng cho biết tên sản phẩm.',
          products: null
        };
      }
    }

    if (!product) {
      const resolved = await this.utils.resolveProductsByRAG(keyword, storeId, 1);
      if (!resolved.products.length) {
        return this.utils.enrichWithAI(sessionId, userMessage,
          `[DATA] Không tìm thấy sản phẩm "${keyword}" trong hệ thống.`,
          { userType: session.user_type });
      }
      product = resolved.products[0];
    }

    const stockResult = await this.apiClient.getInventorySummary(storeId, product.id);
    const items = Array.isArray(stockResult.data) ? stockResult.data : [];
    const stock = items.find(i => String(i.productId || i.id) === String(product.id));

    // 2. Fetch product shelf locations from map data
    let locationStr = 'Chưa xếp trên kệ';
    try {
      const mapRes = await this.apiClient.getStoreMapData(storeId);
      if (mapRes.success && Array.isArray(mapRes.data)) {
        const blocks = mapRes.data;
        const matchingLocations = [];

        blocks.forEach(block => {
          (block.locations || []).forEach(loc => {
            const hasProduct = (loc.products || []).some(p => String(p.productId) === String(product.id));
            if (hasProduct) {
              matchingLocations.push(`${block.name} → ${loc.name}`);
            }
          });
        });

        if (matchingLocations.length > 0) {
          locationStr = matchingLocations.join(', ');
        }
      }
    } catch (err) {
      logger.error({ err, productId: product.id }, 'Failed to fetch shelf location');
    }

    let stockInfo;
    if (stock) {
      if (isCustomer) {
        const onShelf = stock.quantityOnShelf || 0;
        stockInfo = onShelf > 0
          ? `Sản phẩm "${product.name}": Đang có ${onShelf} sản phẩm trên kệ.`
          : `Sản phẩm "${product.name}": Hiện tạm hết hàng trên kệ.`;
      } else {
        stockInfo = `Sản phẩm "${product.name}" (ID: ${product.id}): ` +
          `On-hand: ${stock.quantityOnHand || 0}, On-shelf: ${stock.quantityOnShelf || 0}, ` +
          `Reserved: ${stock.quantityReserved || 0}, Available: ${stock.quantityAvailable || 0}. ` +
          `📍 Vị trí trên kệ: ${locationStr}`;
      }
    } else {
      stockInfo = isCustomer
        ? `Sản phẩm "${product.name}": Chưa có dữ liệu tồn kho.`
        : `Sản phẩm "${product.name}": Chưa có dữ liệu tồn kho. 📍 Vị trí trên kệ: ${locationStr}`;
    }

    let customerContext = null, coPurchaseHint = '';
    if (isCustomer) {
      const customerId = session.metadata?.customerId || session.user_id;
      [customerContext, coPurchaseHint] = await Promise.all([
        getPersonalizationContext(this.apiClient, customerId),
        getCoPurchaseHint(this.copurchaseRepo, [product.id], storeId)
      ]);
    }

    const aiResponse = await this.utils.enrichWithAI(sessionId, userMessage,
      `[DATA] ${stockInfo}`, {
      apiCalled: 'inventory:summary',
      userType: session.user_type,
      customerContext,
      coPurchaseHint
    });

    return {
      ...aiResponse,
      products: [{
        id: product.id,
        name: product.name,
        unitPrice: product.unitPrice,
        image: product.image,
        quantityOnShelf: stock?.quantityOnShelf || 0
      }]
    };
  }

  async handleCheckPrice(session, userMessage) {
    const sessionId = session.id;
    const storeId = session.store_id || 1;
    const isCustomer = session.user_type === 'customer';
    const keyword = this.utils.extractKeyword(userMessage, ['giá', 'bao nhiêu', 'price', 'giá bán', 'giá tiền']);

    if (!this.apiClient) return this.utils.fallbackNoApi('CHECK_PRICE', keyword);

    const resolved = await this.utils.resolveProductsByRAG(keyword, storeId, 5);
    if (!resolved.products.length) {
      return this.utils.enrichWithAI(sessionId, userMessage,
        `[DATA] Không tìm thấy sản phẩm "${keyword}" trong hệ thống.`,
        { userType: session.user_type });
    }

    // FTS-only denoising: keep only products that matched keyword search (have FTS boost)
    // This prevents semantic noise (e.g. "red bull" returning "Gạo ST25")
    let products = resolved.products;
    const ftsMatched = products.filter(p => p._ragScore >= 0.8 || (p._ftsMatch));
    if (ftsMatched.length > 0) products = ftsMatched;

    let priceList;
    // Enrich ALL products with real-time stock (both customer and employee need accurate stock)
    let enrichedProducts = await Promise.all(products.map(async p => {
      try {
        const stock = await this.apiClient.getInventorySummary(storeId, p.id);
        const item = stock.data?.[0];
        return { ...p, quantityOnShelf: item?.quantityOnShelf || 0 };
      } catch {
        return { ...p, quantityOnShelf: p.quantityOnShelf || 0 };
      }
    }));

    if (isCustomer) {
      priceList = enrichedProducts.map(p => {
        const status = p.quantityOnShelf > 0 ? `còn ${p.quantityOnShelf} trên kệ` : 'tạm hết hàng';
        return `- ${p.name}: ${Number(p.unitPrice || 0).toLocaleString('vi-VN')}đ (${status})`;
      }).join('\n');
    } else {
      priceList = enrichedProducts.map(p =>
        `- ${p.name} (ID: ${p.id}): ${Number(p.unitPrice || 0).toLocaleString('vi-VN')}đ`
      ).join('\n');
    }

    let customerContext = null, coPurchaseHint = '';
    if (isCustomer) {
      const customerId = session.metadata?.customerId || session.user_id;
      const productIds = products.map(p => p.id);
      [customerContext, coPurchaseHint] = await Promise.all([
        getPersonalizationContext(this.apiClient, customerId),
        getCoPurchaseHint(this.copurchaseRepo, productIds, storeId)
      ]);
    }

    const aiResponse = await this.utils.enrichWithAI(sessionId, userMessage,
      `[DATA] Kết quả tìm kiếm giá:\n${priceList}`, {
      apiCalled: 'catalog:products',
      userType: session.user_type,
      customerContext,
      coPurchaseHint
    });

    return {
      ...aiResponse,
      products: (enrichedProducts || products).map(p => ({
        id: p.id,
        name: p.name,
        unitPrice: p.unitPrice,
        image: p.image,
        quantityOnShelf: p.quantityOnShelf || 0
      }))
    };
  }

  async handleOrderStatus(session, userMessage) {
    const sessionId = session.id;
    const isCustomer = session.user_type === 'customer';
    const orderId = this.utils.extractOrderId(userMessage);

    if (!this.apiClient) return this.utils.fallbackNoApi('ORDER_STATUS', orderId);

    const statusLabels = {
      draft: 'Nháp', shipping: 'Đang giao', delivered: 'Đã giao',
      cancelled: 'Đã hủy', refunded: 'Đã hoàn tiền', completed: 'Hoàn thành'
    };
    const paymentLabels = {
      pending: 'Chờ thanh toán', partial: 'Thanh toán một phần', paid: 'Đã thanh toán',
      failed: 'Thanh toán thất bại', refunded: 'Đã hoàn tiền', partial_refund: 'Hoàn tiền một phần'
    };

    if (orderId) {
      const result = await this.apiClient.getOrderById(orderId);
      if (result.success && result.data?.order) {
        const o = result.data.order;
        const statusVi = statusLabels[o.status] || o.status;
        const paymentVi = paymentLabels[o.paymentStatus] || o.paymentStatus;

        let info;
        if (isCustomer) {
          info = `Đơn hàng ${o.orderNumber}:\n` +
            `- Trạng thái: ${statusVi}\n` +
            `- Thanh toán: ${paymentVi}\n` +
            `- Tổng tiền: ${Number(o.total || 0).toLocaleString('vi-VN')}đ`;

          if (o.deliveryType === 'delivery') {
            info += `\n- Giao hàng: ${o.address || 'Chưa có địa chỉ'}`;
          }
        } else {
          info = `Đơn hàng ${o.orderNumber} (ID: ${o.id}):\n` +
            `- Trạng thái: ${statusVi} (${o.status})\n` +
            `- Thanh toán: ${paymentVi} (${o.paymentStatus})\n` +
            `- Loại: ${o.deliveryType === 'delivery' ? 'Giao hàng' : 'Nhận tại cửa hàng'}\n` +
            `- Tổng tiền: ${Number(o.total || 0).toLocaleString('vi-VN')}đ` +
            (o.shippingFee > 0 ? ` (Phí ship: ${Number(o.shippingFee).toLocaleString('vi-VN')}đ)` : '') +
            (o.discountPercentage > 0 ? ` (Giảm: ${o.discountPercentage}%)` : '') +
            `\n- KH: #${o.customerId} | NV: #${o.createdBy} | Ngày: ${new Date(o.orderDate).toLocaleDateString('vi-VN')}`;
        }

        if (o.details?.length) {
          const detailLines = o.details.map((d, i) =>
            `  ${i + 1}. ${d.productName} x${d.quantity} — ${Number(d.totalPrice || 0).toLocaleString('vi-VN')}đ`
          ).join('\n');
          info += `\nChi tiết đơn hàng:\n${detailLines}`;
        }

        return this.utils.enrichWithAI(sessionId, userMessage, `[DATA] ${info}`, {
          apiCalled: 'order:detail',
          userType: session.user_type
        });
      }
      return this.utils.enrichWithAI(sessionId, userMessage,
        `[DATA] Không tìm thấy đơn hàng #${orderId}.`,
        { userType: session.user_type });
    }

    const filters = isCustomer ? { customerId: (session.metadata?.customerId || session.user_id) } : {};
    const result = await this.apiClient.getOrders(filters);
    if (result.success && result.data?.orders?.length) {
      const recent = result.data.orders.slice(0, 5);
      const list = recent.map(o => {
        const statusVi = statusLabels[o.status] || o.status;
        const paymentVi = paymentLabels[o.paymentStatus] || o.paymentStatus;
        return `- ${o.orderNumber}: ${statusVi} | ${paymentVi} | ${Number(o.total || 0).toLocaleString('vi-VN')}đ`;
      }).join('\n');
      return this.utils.enrichWithAI(sessionId, userMessage,
        `[DATA] ${recent.length} đơn hàng gần nhất:\n${list}`,
        { apiCalled: 'order:list', userType: session.user_type });
    }

    return this.utils.enrichWithAI(sessionId, userMessage,
      `[DATA] Chưa có đơn hàng nào.`,
      { userType: session.user_type });
  }

  async handleSearchProduct(session, userMessage) {
    if (this.ragService === undefined && process.env.NODE_ENV !== 'test') {
      // Wait for RAG hot-swap (same as handleRecommendation)
      const maxWaitMs = 90_000;
      const pollMs = 3_000;
      const start = Date.now();
      while (Date.now() - start < maxWaitMs) {
        await new Promise(r => setTimeout(r, pollMs));
        if (this.ragService) break;
      }
    }

    if (this.ragService) {
      const storeId = (typeof session === 'object') ? (session.store_id || 1) : 1;
      const customerId = (typeof session === 'object' && session.user_type === 'customer')
        ? (session.metadata?.customerId || session.user_id)
        : null;
      const sessionId = (typeof session === 'object') ? session.id : session;
      const chatHistory = await this.utils.getRecentHistory(sessionId);

      const result = await this.ragService.recommend(
        userMessage, storeId, customerId, chatHistory
      );
      return {
        content: result.content,
        products: result.products,
        ragMetadata: result.metadata
      };
    }

    const sessionId = (typeof session === 'object') ? session.id : session;
    return this.handleSearchProductFallback(sessionId, userMessage);
  }

  async handleSearchProductFallback(sessionId, userMessage) {
    const keyword = this.utils.extractKeyword(userMessage,
      ['tìm', 'search', 'có gì', 'sản phẩm nào', 'gợi ý', 'muốn mua', 'cần mua', 'mua đồ', 'đề xuất', 'mua cho']);

    if (!this.apiClient) return this.utils.fallbackNoApi('SEARCH_PRODUCT', keyword);

    const result = await this.apiClient.searchProducts(keyword);
    if (!result.success || !result.data?.products?.length) {
      return this.utils.enrichWithAI(sessionId, userMessage,
        `[DATA] Không tìm thấy sản phẩm nào với từ khóa "${keyword}".`);
    }

    const products = result.data.products.slice(0, 8);
    const list = products.map(p =>
      `- ${p.name} | ${Number(p.unitPrice || 0).toLocaleString('vi-VN')}đ | ${p.isActive !== false ? 'Đang bán' : 'Ngừng bán'}`
    ).join('\n');

    return this.utils.enrichWithAI(sessionId, userMessage,
      `[DATA] Tìm thấy ${result.data.products.length} sản phẩm:\n${list}`, { apiCalled: 'catalog:search' });
  }
}

module.exports = ReadHandler;
