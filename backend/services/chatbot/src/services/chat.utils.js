/**
 * Chat Utility Functions — Shared helpers for all chat handlers.
 * Extracted from ChatService to follow SRP (Single Responsibility Principle).
 *
 * Contains: product resolution (RAG + catalog), keyword extraction,
 * AI enrichment, clarification state machine, and generic responses.
 */

const ActionExecutor = require('./action.executor');
const { ACTION_TYPES } = require('./action.types');
const logger = require('../../../../shared/common/logger');

class ChatUtils {
  constructor(ctx) {
    this.chatRepo = ctx.chatRepo;
    this.hfClient = ctx.hfClient;
    this.apiClient = ctx.apiClient;
    this.ragService = ctx.ragService;
    this.actionExecutor = new ActionExecutor(ctx.apiClient, ctx.chatRepo);
  }

  // ── Product Resolution ────────────────────────

  /**
   * RAG Entity Resolution — Tìm sản phẩm bằng vector search (ngữ nghĩa).
   * Fallback sang catalog API (SQL ILIKE) nếu RAG không có kết quả.
   *
   * @param {string} keyword - tên viết tắt/gõ tay từ user
   * @param {number} storeId
   * @param {number} limit - số SP tối đa
   * @returns {{ products: object[], source: 'rag'|'catalog'|null }}
   */
  async resolveProductsByRAG(keyword, storeId, limit = 5) {
    if (this.ragService?.embeddingClient?.isReady) {
      try {
        const queryVector = await this.ragService.embeddingClient.embed(keyword);
        const ragResults = await this.ragService.knowledgeRepo.searchSemantic(
          queryVector, storeId, limit
        );

        const relevant = ragResults.filter(r => r.score >= 0.7);
        if (relevant.length > 0) {
          logger.info({ keyword, source: 'rag', count: relevant.length, topScore: relevant[0].score }, 'RAG entity resolution hit');
          return {
            source: 'rag',
            products: relevant.map(r => ({
              id: r.product_id,
              name: r.content.match(/"([^"]+)"/)?.[1] || `Product ${r.product_id}`,
              unitPrice: Number(r.unit_price),
              categoryName: r.category_name,
              quantityOnShelf: r.quantity_on_shelf,
              image: null,
              _ragScore: r.score
            }))
          };
        }
        logger.debug({ keyword, topScore: ragResults[0]?.score || 0 }, 'RAG entity resolution miss — below threshold');
      } catch (err) {
        logger.warn({ err, keyword }, 'RAG entity resolution failed — falling back to catalog');
      }
    }

    if (this.apiClient) {
      const result = await this.apiClient.searchProducts(keyword);
      if (result.success && result.data?.products?.length) {
        logger.info({ keyword, source: 'catalog', count: result.data.products.length }, 'Catalog fallback hit');
        return {
          source: 'catalog',
          products: result.data.products.slice(0, limit)
        };
      }
    }

    logger.info({ keyword }, 'Product resolution failed — no results from RAG or catalog');
    return { source: null, products: [] };
  }

  // ── Text Extraction ───────────────────────────

  extractQuantityAndProduct(message) {
    const triggerWords = ['thêm vào giỏ hàng', 'thêm vào giỏ', 'bỏ vào giỏ', 'cho vào giỏ', 'giỏ hàng', 'mua', 'lấy', 'thêm', 'xóa khỏi giỏ hàng', 'xóa khỏi giỏ', 'bỏ khỏi giỏ', 'loại bỏ khỏi giỏ', 'xóa', 'bỏ', 'tăng số lượng', 'giảm số lượng', 'thay đổi số lượng', 'cập nhật', 'sửa'];
    const stopWords = ['vào', 'cho', 'khỏi', 'ra', 'xuống', 'lên', 'thành', 'số lượng', 'của', 'tôi', 'hộ', 'giúp', 'cái', 'chai', 'lon', 'hộp', 'gói', 'bịch', 'tuýp', 'chiếc', 'bao', 'kg', 'g'];

    let cleaned = message.toLowerCase();
    for (const word of triggerWords) {
      cleaned = cleaned.replace(word, '');
    }

    const qtyMatch = cleaned.match(/\b(\d+)\b/);
    let quantity = 1;
    if (qtyMatch) {
      quantity = parseInt(qtyMatch[1], 10);
      cleaned = cleaned.replace(qtyMatch[0], '');
    }

    for (const stop of stopWords) {
      cleaned = cleaned.replace(new RegExp(`\\b${stop}\\b`, 'g'), '');
    }

    const productKeyword = cleaned.replace(/[?.!,]/g, '').replace(/\s+/g, ' ').trim();
    return { quantity, productKeyword };
  }

  extractKeyword(message, triggerWords) {
    const lower = message.toLowerCase();
    const sorted = [...triggerWords].sort((a, b) => b.length - a.length);

    for (const trigger of sorted) {
      const idx = lower.indexOf(trigger);
      if (idx !== -1) {
        const after = message.substring(idx + trigger.length).trim();
        const before = message.substring(0, idx).trim();

        const fillerWords = ['không', 'nào', 'đi', 'nhé', 'vậy', 'ạ', 'đây', 'kia', 'thế', 'rồi', 'chưa', 'hả', 'hở', 'nha', 'luôn', 'tiền', 'vậy', 'hết'];
        const afterClean = after.replace(/[?!.,;:]/g, '').trim().toLowerCase();
        const isAfterFiller = !afterClean || fillerWords.includes(afterClean);

        let keyword = (isAfterFiller && before) ? before : (after || before);

        for (const filler of fillerWords) {
          const regex = new RegExp(`\\s+${filler}\\s*$`, 'i');
          keyword = keyword.replace(regex, '').trim();
        }

        const noiseWords = ['sản phẩm', 'mặt hàng', 'sp', 'của', 'cái', 'con', 'loại', 'hàng', 'về', 'cho', 'tôi', 'mình', 'xem', 'kiểm tra', 'check'];
        for (const noise of noiseWords) {
          if (keyword.toLowerCase().startsWith(noise)) {
            keyword = keyword.substring(noise.length).trim();
          }
        }

        return keyword.replace(/[?!.,;:]/g, '').trim() || message;
      }
    }
    return message;
  }

  extractOrderId(message) {
    const match = message.match(/#?(\d{1,10})/);
    return match ? match[1] : null;
  }

  // ── AI Enrichment ─────────────────────────────

  async enrichWithAI(sessionId, userMessage, dataContext, {
    apiCalled = null,
    userType = 'employee',
    customerContext = null,
    coPurchaseHint = ''
  } = {}) {
    const chatHistory = await this.chatRepo.getRecentContext(sessionId, 5);
    const isCustomer = userType === 'customer';

    let systemHint;
    if (isCustomer) {
      const personalizationLine = customerContext?.prompt ? `\n${customerContext.prompt}` : '';
      const coPurchaseLine = coPurchaseHint ? `\n${coPurchaseHint}` : '';
      systemHint = `Bạn là nhân viên tư vấn siêu thị POSMART. Đóng vai trả lời khách hàng bằng tiếng Việt.\n` +
        `Quy tắc: Tùy biến cách diễn đạt tự nhiên, đa dạng. Nếu có thông tin mua kèm, gợi ý tự nhiên. Ngắn gọn, tối đa 3-4 câu.` +
        `${personalizationLine}${coPurchaseLine}`;
    } else {
      systemHint = `Bạn là trợ lý tra cứu cho nhân viên siêu thị POSMART. Trả lời chính xác, ngắn gọn, dựa trên dữ liệu hệ thống. Dùng định dạng số liệu rõ ràng.`;
    }

    const messages = [
      ...chatHistory.map(m => ({ role: m.role, content: m.content })),
      { role: 'user', content: `${userMessage}\n\n${dataContext}\n\n${systemHint}` }
    ];

    const aiResponse = await this.hfClient.chatCompletion(messages);
    return { ...aiResponse, apiCalled };
  }

  fallbackNoApi(intent, keyword) {
    return {
      content: `Tôi hiểu bạn muốn ${intent === 'CHECK_STOCK' ? 'kiểm tra tồn kho' :
        intent === 'CHECK_PRICE' ? 'kiểm tra giá' :
          intent === 'ORDER_STATUS' ? 'tra cứu đơn hàng' :
            'tìm sản phẩm'}${keyword ? ` "${keyword}"` : ''}. ` +
        `Hiện tại hệ thống đang kết nối, vui lòng thử lại sau.`,
      model: null,
      latencyMs: 0,
      apiCalled: null
    };
  }

  // ── Generic Handlers ──────────────────────────

  handleHelp() {
    const helpText = `Tôi có thể giúp bạn kiểm tra tồn kho, giá sản phẩm, trạng thái đơn hàng và gợi ý sản phẩm. Bạn muốn thử tính năng nào?`;

    return {
      content: helpText,
      model: null,
      latencyMs: 0,
      suggested_prompts: [
        'Kiểm tra tồn kho sữa',
        'Giá bán mì Hảo Hảo',
        'Đơn hàng gần đây',
        'Gợi ý sản phẩm bán chạy',
        'Tìm kiếm gia vị'
      ]
    };
  }

  async handleFreeChat(sessionId, userMessage) {
    const chatHistory = await this.chatRepo.getRecentContext(sessionId, 8);
    const messages = [
      ...chatHistory.map(m => ({ role: m.role, content: m.content })),
      { role: 'user', content: userMessage }
    ];

    return await this.hfClient.chatCompletion(messages);
  }

  async getRecentHistory(sessionId) {
    try {
      const messages = await this.chatRepo.getRecentContext(sessionId, 6);
      return messages.map(m => ({ role: m.role, content: m.content }));
    } catch (err) {
      logger.warn({ err, sessionId }, 'Failed to get chat history');
      return [];
    }
  }

  // ── State Machine: Clarification ──────────────

  /**
   * Handle multi-turn clarification states (CLARIFYING / CONFIRMING / COLLECTING).
   * Returns null if no pending action, or a response object if state was handled.
   * @param {object} session
   * @param {string} userMessage
   * @param {object} handlers - { executeAddToCart, executePosAddItem, processOrderCollection }
   */
  async handleClarification(session, userMessage, handlers = {}) {
    const metadata = session.metadata || {};
    const pending = metadata.pendingAction;
    if (!pending || !pending.state) return null;

    const candidates = pending.data.candidates || [];
    const quantity = pending.data.quantity || 1;

    if (pending.state === 'COLLECTING') {
      if (pending.type === 'CREATE_ORDER' && handlers.processOrderCollection) {
        return handlers.processOrderCollection(session, userMessage);
      }
    }

    if (pending.state === 'CLARIFYING') {
      const match = userMessage.match(/\[?(\d+)\]?/);
      let selectedProduct = null;

      if (match) {
        const index = parseInt(match[1], 10) - 1;
        if (index >= 0 && index < candidates.length) {
          selectedProduct = candidates[index];
        }
      }

      if (!selectedProduct) {
        const lowerMsg = userMessage.toLowerCase().trim();
        selectedProduct = candidates.find(c =>
          c.name.toLowerCase().includes(lowerMsg) ||
          lowerMsg.includes(c.name.toLowerCase())
        );
      }

      if (selectedProduct) {
        delete metadata.pendingAction;
        session.metadata = metadata;
        await this.chatRepo.updateSessionMetadata(session.id, metadata);

        if (pending.type === 'ADD_TO_CART' && handlers.executeAddToCart) {
          return handlers.executeAddToCart(session, selectedProduct, quantity);
        }
        if (pending.type === 'POS_ADD_ITEM' && handlers.executePosAddItem) {
          return handlers.executePosAddItem(session, selectedProduct, quantity);
        }
      }

      const list = candidates.map((p, i) => `[${i + 1}] ${p.name} (${Number(p.unitPrice || p.price || p.unit_price).toLocaleString('vi-VN')}đ)`).join('\n');
      return {
        intent: pending.type,
        reply: `Vui lòng chọn chính xác số thứ tự sản phẩm bên dưới bằng cách nhập số (ví dụ: 1 hoặc 2):\n${list}`,
        products: candidates
      };
    }

    if (pending.state === 'CONFIRMING') {
      const lowerMsg = userMessage.toLowerCase().trim();
      const isConfirmed = /(?:^|\s)(đồng ý|xác nhận|có|yes|ok|đúng thế|chắc chắn)(?:\s|$)/i.test(lowerMsg);
      const isRejected = /(?:^|\s)(không|hủy bỏ|no|cancel|đừng|bỏ qua)(?:\s|$)/i.test(lowerMsg);

      if (isConfirmed) {
        delete metadata.pendingAction;
        session.metadata = metadata;
        await this.chatRepo.updateSessionMetadata(session.id, metadata);

        const actionPayload = { ...pending.data, confirmed: true };
        const result = await this.actionExecutor.execute(session, pending.type, actionPayload);

        if (!result.success) {
          return {
            intent: pending.type,
            reply: `Thực hiện thất bại: ${result.error}`,
            products: null
          };
        }

        let replyMsg = 'Thực hiện hành động thành công.';
        if (pending.type === 'CANCEL_ORDER') {
          replyMsg = `Đã hủy đơn hàng #${pending.data.orderId} thành công.`;
        } else if (pending.type === 'CREATE_ORDER') {
          replyMsg = `Đã tạo đơn hàng mới thành công. ID đơn hàng: #${result.id || result.orderId || 'N/A'}`;
        }

        return {
          intent: pending.type,
          reply: replyMsg,
          products: null,
          action: {
            type: pending.type,
            payload: actionPayload
          }
        };
      } else if (isRejected) {
        delete metadata.pendingAction;
        session.metadata = metadata;
        await this.chatRepo.updateSessionMetadata(session.id, metadata);

        return {
          intent: pending.type,
          reply: 'Đã hủy yêu cầu thực hiện hành động.',
          products: null
        };
      }

      return {
        intent: pending.type,
        reply: `Hành động này chưa được xác nhận. Vui lòng nhập "Đồng ý" hoặc "Hủy bỏ" để tiếp tục.`,
        products: null
      };
    }

    return null;
  }
}

module.exports = ChatUtils;
