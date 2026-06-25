/**
 * Entity Manager Handler — Supports Store Manager actions for Customers, Suppliers, and Inventory.
 * Intents:
 * - MANAGE_CUSTOMER_SEARCH
 * - MANAGE_CUSTOMER_UPDATE
 * - MANAGE_CUSTOMER_LIST
 * - MANAGE_SUPPLIER_LIST
 * - MANAGE_SUPPLIER_SEARCH
 * - MANAGE_INVENTORY_CHECK
 * - MANAGE_INVENTORY_STOCKOUT
 * - MANAGE_INVENTORY_VIEW
 */

const logger = require('../../../../../shared/common/logger');

class EntityManagerHandler {
  constructor(ctx) {
    this.chatRepo = ctx.chatRepo;
    this.apiClient = ctx.apiClient;
    this.utils = ctx.utils;
    this.actionExecutor = ctx.utils.actionExecutor;
  }

  // 1. MANAGE_CUSTOMER_SEARCH
  async handleCustomerSearch(session, userMessage) {
    // Extract customer query
    const keywords = ['tìm khách hàng', 'tìm kiếm khách hàng', 'tìm khách', 'search khách hàng', 'search khách', 'tìm kiếm', 'tìm', 'thông tin khách hàng', 'tra cứu khách hàng'];
    let query = userMessage.toLowerCase();
    for (const kw of keywords) {
      if (query.includes(kw)) {
        const idx = query.indexOf(kw) + kw.length;
        query = userMessage.slice(idx).trim();
        break;
      }
    }
    query = query.trim();

    if (!query) {
      return {
        intent: 'MANAGE_CUSTOMER_SEARCH',
        reply: 'Vui lòng nhập tên hoặc số điện thoại khách hàng cần tìm (ví dụ: "Tìm khách hàng Ngo Xuan Phuc").',
        products: null
      };
    }

    const result = await this.apiClient.searchCustomers({ search: query });
    const customers = result.data?.customers || [];
    if (!result.success || customers.length === 0) {
      return {
        intent: 'MANAGE_CUSTOMER_SEARCH',
        reply: `Không tìm thấy khách hàng nào khớp với: "${query}".`,
        products: null
      };
    }

    const customer = customers[0];

    // Save last searched customer in session metadata
    const metadata = session.metadata || {};
    metadata.lastSearchedCustomer = {
      id: customer.id,
      name: customer.fullName || customer.fullName || customer.username,
      phone: customer.phoneNumber || customer.phone || 'N/A',
      customerType: customer.customerType || customer.customer_type || 'Retail'
    };
    await this.chatRepo.updateSessionMetadata(session.id, metadata);

    // Try to get latest order
    let orderSuffix = '';
    try {
      const ordersRes = await this.apiClient.getOrders({ customerId: customer.id });
      if (ordersRes.success && ordersRes.data && ordersRes.data.length > 0) {
        const lastOrder = ordersRes.data[0];
        orderSuffix = ` Đơn hàng gần nhất: ORD-${lastOrder.id || lastOrder.orderNumber}.`;
      }
    } catch (err) {
      logger.error({ err }, 'Failed to fetch last order for customer search');
    }

    return {
      intent: 'MANAGE_CUSTOMER_SEARCH',
      reply: `Tìm thấy: Khách hàng ${metadata.lastSearchedCustomer.name}, số ĐT: ${metadata.lastSearchedCustomer.phone}, Hạng: ${metadata.lastSearchedCustomer.customerType}.${orderSuffix}`,
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: `/customers?search=${encodeURIComponent(customer.fullName || customer.username)}` }
      }
    };
  }

  // 2. MANAGE_CUSTOMER_UPDATE
  async handleCustomerUpdate(session, userMessage) {
    const metadata = session.metadata || {};
    const lastCustomer = metadata.lastSearchedCustomer;
    if (!lastCustomer) {
      return {
        intent: 'MANAGE_CUSTOMER_UPDATE',
        reply: 'Vui lòng tìm kiếm khách hàng trước (ví dụ: "Tìm khách hàng Ngo Xuan Phuc").',
        products: null
      };
    }

    // Extract tier (e.g. VIP, Retail)
    let newTier = 'VIP'; // Default fallback
    const msgLower = userMessage.toLowerCase();
    if (msgLower.includes('retail') || msgLower.includes('thường') || msgLower.includes('thường dân')) {
      newTier = 'Retail';
    } else if (msgLower.includes('vip')) {
      newTier = 'VIP';
    } else if (msgLower.includes('silver') || msgLower.includes('bạc')) {
      newTier = 'Silver';
    } else if (msgLower.includes('gold') || msgLower.includes('vàng')) {
      newTier = 'Gold';
    }

    const actionPayload = {
      customerId: lastCustomer.id,
      newTier
    };

    const confirmResult = await this.actionExecutor.execute(session, 'MANAGE_CUSTOMER_UPDATE', actionPayload);

    if (confirmResult.requiresConfirmation) {
      metadata.pendingAction = {
        type: 'MANAGE_CUSTOMER_UPDATE',
        state: 'CONFIRMING',
        data: actionPayload
      };
      await this.chatRepo.updateSessionMetadata(session.id, metadata);

      return {
        intent: 'MANAGE_CUSTOMER_UPDATE',
        reply: `Xác nhận nâng hạng Khách hàng ${lastCustomer.name} lên ${newTier}? (Vui lòng trả lời "Đồng ý" hoặc "Hủy bỏ")`,
        products: null
      };
    }

    if (!confirmResult.success) {
      return {
        intent: 'MANAGE_CUSTOMER_UPDATE',
        reply: `Không thể nâng hạng khách hàng: ${confirmResult.error}`,
        products: null
      };
    }

    return {
      intent: 'MANAGE_CUSTOMER_UPDATE',
      reply: `Đã cập nhật hạng ${newTier} thành công cho khách hàng ${lastCustomer.name}.`,
      products: null
    };
  }

  // 3. MANAGE_CUSTOMER_LIST
  handleCustomerList(session, userMessage) {
    // Extract filter if any (e.g. vip, retail)
    let path = '/customers';
    const msgLower = userMessage.toLowerCase();
    if (msgLower.includes('vip')) {
      path = '/customers?type=vip';
    }

    return {
      intent: 'MANAGE_CUSTOMER_LIST',
      reply: 'Đang mở danh sách khách hàng...',
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path }
      }
    };
  }

  // 4. MANAGE_SUPPLIER_LIST
  handleSupplierList(session) {
    return {
      intent: 'MANAGE_SUPPLIER_LIST',
      reply: 'Đang chuyển bạn đến danh sách nhà cung cấp...',
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: '/suppliers' }
      }
    };
  }

  // 5. MANAGE_SUPPLIER_SEARCH
  async handleSupplierSearch(session, userMessage) {
    const keywords = ['tìm nhà cung cấp', 'tìm kiếm nhà cung cấp', 'tìm ncc', 'search nhà cung cấp', 'search ncc', 'thông tin nhà cung cấp', 'thông tin ncc', 'tìm'];
    let query = userMessage.toLowerCase();
    for (const kw of keywords) {
      if (query.includes(kw)) {
        const idx = query.indexOf(kw) + kw.length;
        query = userMessage.slice(idx).trim();
        break;
      }
    }
    query = query.trim();

    if (!query) {
      return {
        intent: 'MANAGE_SUPPLIER_SEARCH',
        reply: 'Vui lòng nhập tên nhà cung cấp cần tìm (ví dụ: "Tìm nhà cung cấp Trung Nguyên").',
        products: null
      };
    }

    const result = await this.apiClient.getSuppliers({ search: query });
    if (!result.success || !result.data || result.data.length === 0) {
      return {
        intent: 'MANAGE_SUPPLIER_SEARCH',
        reply: `Không tìm thấy nhà cung cấp nào khớp với tên: "${query}".`,
        products: null
      };
    }

    const supplier = result.data[0];
    const contact = supplier.contactPhone || supplier.phone || 'N/A';
    const email = supplier.contactEmail || supplier.email || 'N/A';

    return {
      intent: 'MANAGE_SUPPLIER_SEARCH',
      reply: `Tìm thấy nhà cung cấp: **${supplier.companyName || supplier.name || 'N/A'}**\n* Địa chỉ: ${supplier.address || 'N/A'}\n* Số điện thoại: ${contact}\n* Email: ${email}`,
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: `/suppliers?search=${encodeURIComponent(supplier.companyName || supplier.name || '')}` }
      }
    };
  }

  // 6. MANAGE_INVENTORY_CHECK
  async handleInventoryCheck(session) {
    const storeId = session.storeId || session.store_id || 1;
    const result = await this.apiClient.getInventorySummary(storeId);
    if (!result.success || !result.data) {
      return {
        intent: 'MANAGE_INVENTORY_CHECK',
        reply: `Không thể kiểm tra tồn kho: ${result.error}`,
        products: null
      };
    }

    const items = result.data || [];
    const totalItems = items.length;
    const totalQty = items.reduce((acc, curr) => acc + (curr.quantityOnShelf || 0) + (curr.quantityInWarehouse || 0), 0);

    return {
      intent: 'MANAGE_INVENTORY_CHECK',
      reply: `### 📦 TỔNG HỢP TỒN KHO CỬA HÀNG
Hiện cửa hàng có **${totalItems} mặt hàng** đang được quản lý.
* **Tổng số lượng thực tế:** ${totalQty} sản phẩm (bao gồm cả trên kệ và trong kho).

Bạn có thể quản lý chi tiết định mức hoặc xuất nhập kho tại giao diện quản lý kho.`,
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: '/inventory/management' }
      }
    };
  }

  // 7. MANAGE_INVENTORY_STOCKOUT
  async handleInventoryStockout(session, userMessage) {
    const storeId = session.storeId || session.store_id || 1;
    const result = await this.apiClient.getInventorySummary(storeId);
    if (!result.success || !result.data) {
      return {
        intent: 'MANAGE_INVENTORY_STOCKOUT',
        reply: `Không thể kiểm tra sản phẩm hết hàng: ${result.error}`,
        products: null
      };
    }

    const items = result.data || [];
    const msg = (userMessage || '').toLowerCase();

    // Check query types
    const checkWarehouse = msg.includes('trong kho') || msg.includes('kho chính') || msg.includes('kho');
    const checkShelf = msg.includes('trên kệ') || msg.includes('kệ') || msg.includes('quầy') || msg.includes('trên quầy') || msg.includes('kệ hàng');

    // Filter items
    let reply = '';

    if (checkWarehouse && !checkShelf) {
      // Out of stock in warehouse ONLY
      const outOfStockWarehouse = items.filter(p => (p.quantityOnHand || 0) === 0);
      if (outOfStockWarehouse.length === 0) {
        reply = 'Tuyệt vời! Hiện tại không có sản phẩm nào bị hết hàng trong kho.';
      } else {
        const listText = outOfStockWarehouse.slice(0, 5).map((p, idx) =>
          `${idx + 1}. **${p.product?.name || `Product #${p.productId}`}** (Mã: ${p.product?.productCode || 'N/A'}): Hết hàng trong kho (Còn ${p.quantityOnShelf || 0} SP trên kệ)`
        ).join('\n');
        reply = `### CẢNH BÁO HẾT HÀNG TRONG KHO\nPhát hiện **${outOfStockWarehouse.length} mặt hàng** đã hết hoàn toàn trong kho chính:\n\n${listText}${outOfStockWarehouse.length > 5 ? `\n... và ${outOfStockWarehouse.length - 5} sản phẩm khác.` : ''}`;
      }
    } else if (checkShelf && !checkWarehouse) {
      // Out of stock on shelf ONLY (Trống kệ)
      const outOfStockShelf = items.filter(p => (p.quantityOnShelf || 0) === 0);
      if (outOfStockShelf.length === 0) {
        reply = 'Tuyệt vời! Hiện tại không có sản phẩm nào bị trống trên kệ.';
      } else {
        const listText = outOfStockShelf.slice(0, 5).map((p, idx) =>
          `${idx + 1}. **${p.product?.name || `Product #${p.productId}`}** (Mã: ${p.product?.productCode || 'N/A'}): Trống kệ (${p.quantityOnHand || 0} SP trong kho)`
        ).join('\n');
        reply = `### CẢNH BÁO TRỐNG KỆ (STOCKOUT ON SHELF)\nPhát hiện **${outOfStockShelf.length} mặt hàng** đã hết hoàn toàn trên kệ trưng bày:\n\n${listText}${outOfStockShelf.length > 5 ? `\n... và ${outOfStockShelf.length - 5} sản phẩm khác.` : ''}\n\nĐề xuất: Nên thực hiện châm hàng (trưng bày bổ sung) từ kho chính lên kệ.`;
      }
    } else {
      // General out of stock or check both
      const outOfStockWarehouse = items.filter(p => (p.quantityOnHand || 0) === 0);
      const outOfStockShelf = items.filter(p => (p.quantityOnShelf || 0) === 0);

      const parts = [];
      parts.push(`### TỔNG HỢP SẢN PHẨM HẾT HÀNG`);

      if (outOfStockWarehouse.length === 0) {
        parts.push(`* **Trong kho:** Không có sản phẩm nào hết hàng.`);
      } else {
        const listText = outOfStockWarehouse.slice(0, 3).map(p =>
          `  * **${p.product?.name || `Product #${p.productId}`}** (${p.product?.productCode || 'N/A'}): Hết hàng trong kho (Còn ${p.quantityOnShelf || 0} SP trên kệ)`
        ).join('\n');
        parts.push(`* **Trong kho (${outOfStockWarehouse.length} SP hết):**\n${listText}${outOfStockWarehouse.length > 3 ? `\n  * ... và ${outOfStockWarehouse.length - 3} SP khác.` : ''}`);
      }

      if (outOfStockShelf.length === 0) {
        parts.push(`* **Trên kệ:** Không có sản phẩm nào trống kệ.`);
      } else {
        const listText = outOfStockShelf.slice(0, 3).map(p =>
          `  * **${p.product?.name || `Product #${p.productId}`}** (${p.product?.productCode || 'N/A'}): Trống kệ (${p.quantityOnHand || 0} SP trong kho)`
        ).join('\n');
        parts.push(`* **Trên kệ (${outOfStockShelf.length} SP hết):**\n${listText}${outOfStockShelf.length > 3 ? `\n  * ... và ${outOfStockShelf.length - 3} SP khác.` : ''}`);
      }

      reply = parts.join('\n\n');
    }

    return {
      intent: 'MANAGE_INVENTORY_STOCKOUT',
      reply,
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: '/inventory/management' }
      }
    };
  }

  // 8. MANAGE_INVENTORY_VIEW
  handleInventoryView(session) {
    return {
      intent: 'MANAGE_INVENTORY_VIEW',
      reply: 'Đang mở giao diện quản lý tồn kho và sơ đồ kệ hàng...',
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: '/inventory/management' }
      }
    };
  }

  // 9. MANAGE_BATCH_DISCOUNT
  async handleBatchDiscount(session, userMessage) {
    const storeId = session.storeId || session.store_id || 1;
    const metadata = session.metadata || {};

    // Extract discount percentage
    let discountPercentage = null;
    const pctMatch = userMessage.match(/(\d+)\s*%/);
    if (pctMatch) {
      discountPercentage = parseInt(pctMatch[1]);
    } else {
      const numMatch = userMessage.match(/\b([1-9]\d?)\b/);
      if (numMatch) {
        discountPercentage = parseInt(numMatch[1]);
      }
    }

    if (discountPercentage === null) {
      return {
        intent: 'MANAGE_BATCH_DISCOUNT',
        reply: 'Vui lòng cung cấp mức phần trăm giảm giá cần áp dụng (ví dụ: "Giảm giá 15% bánh Nabati").',
        products: null
      };
    }

    // Extract product keyword
    let productKeyword = userMessage;
    const keywords = ['giảm giá', 'chiết khấu', 'sale', 'hạ giá', 'set giảm giá', 'discount', 'áp dụng giảm giá'];
    for (const kw of keywords) {
      const idx = productKeyword.toLowerCase().indexOf(kw);
      if (idx !== -1) {
        productKeyword = productKeyword.substring(0, idx) + ' ' + productKeyword.substring(idx + kw.length);
      }
    }
    productKeyword = productKeyword.replace(/\d+\s*%/g, ' ').replace(/\b\d+\b/g, ' ').replace(/[?.!,]/g, ' ');

    // Strip Vietnamese stopwords to clean RAG search query safely without relying on broken \b
    let cleanedKeyword = ' ' + productKeyword.toLowerCase().trim() + ' ';
    const stopwords = ['áp dụng', 'giúp', 'tôi', 'bạn', 'tạo', 'cho', 'của', 'với', 'và', 'thì',
      'sản phẩm', 'mặt hàng', 'lô hàng', 'tất cả', 'hết', 'các', 'những', 'này',
      'xin', 'vui lòng', 'hãy', 'cần', 'muốn', 'được'];
    for (const sw of stopwords) {
      cleanedKeyword = cleanedKeyword.replace(new RegExp(`\\s+${sw}\\s+`, 'gi'), ' ');
    }
    productKeyword = cleanedKeyword.replace(/\s+/g, ' ').trim();

    if (!productKeyword) {
      return {
        intent: 'MANAGE_BATCH_DISCOUNT',
        reply: 'Vui lòng nhập tên sản phẩm cần cấu hình giảm giá.',
        products: null
      };
    }

    const resolved = await this.utils.resolveProductsByRAG(productKeyword, storeId, 5);
    const productCandidates = resolved.products || [];

    if (productCandidates.length === 0) {
      return {
        intent: 'MANAGE_BATCH_DISCOUNT',
        reply: `Không tìm thấy sản phẩm nào khớp với từ khóa "${productKeyword}".`,
        products: null
      };
    }

    let isAmbiguous = false;
    if (productCandidates.length > 1) {
      const topScore = productCandidates[0]._ragScore || 0;
      const secondScore = productCandidates[1]._ragScore || 0;
      if (topScore >= 0.75 && (topScore - secondScore) >= 0.1) {
        isAmbiguous = false;
      } else {
        isAmbiguous = true;
      }
    }

    if (isAmbiguous) {
      metadata.pendingAction = {
        type: 'MANAGE_BATCH_DISCOUNT',
        state: 'CLARIFYING_DISCOUNT',
        data: {
          discountPercentage,
          candidates: productCandidates.map(p => ({
            id: p.id,
            name: p.name,
            isPerishable: p.isPerishable || p.is_perishable || false
          }))
        }
      };
      await this.chatRepo.updateSessionMetadata(session.id, metadata);

      const list = productCandidates.map((p, i) => `[${i + 1}] ${p.name}`).join('\n');
      return {
        intent: 'MANAGE_BATCH_DISCOUNT',
        reply: `Tôi tìm thấy một vài sản phẩm phù hợp. Bạn muốn áp dụng giảm giá cho sản phẩm nào?\n${list}`,
        products: productCandidates
      };
    }

    return this.executeBatchDiscountFlow(session, productCandidates[0], discountPercentage);
  }

  async executeBatchDiscountFlow(session, product, discountPercentage) {
    const storeId = session.storeId || session.store_id || 1;
    const metadata = session.metadata || {};

    const isPerishable = product.isPerishable || product.is_perishable || false;
    if (isPerishable) {
      return {
        intent: 'MANAGE_BATCH_DISCOUNT',
        reply: `Sản phẩm "${product.name}" thuộc nhóm hàng tươi sống/perishable. Yêu cầu chuyển đến màn hình Cấu hình Khuyến mãi để tránh sai lệch định giá tự động.`,
        action: {
          type: 'NAVIGATE',
          payload: { path: `/inventory/batches?productId=${product.id}` }
        }
      };
    }

    const batchesRes = await this.apiClient.getProductBatches(product.id);
    let hasConflict = false;
    let existingDiscount = 0;

    if (batchesRes?.success && batchesRes?.data) {
      const activeBatches = batchesRes.data.filter(b => b.status === 'active');
      for (const batch of activeBatches) {
        const discountVal = Number(batch.discount_percentage || batch.discountPercentage || 0);
        if (discountVal > 0) {
          hasConflict = true;
          existingDiscount = discountVal;
          break;
        }
      }
    }

    const actionPayload = {
      productId: product.id,
      discountPercentage,
      productName: product.name
    };

    if (hasConflict) {
      metadata.pendingAction = {
        type: 'MANAGE_BATCH_DISCOUNT',
        state: 'CONFIRMING',
        data: actionPayload
      };
      await this.chatRepo.updateSessionMetadata(session.id, metadata);

      return {
        intent: 'MANAGE_BATCH_DISCOUNT',
        reply: `⚠️ Sản phẩm "${product.name}" hiện đang có lô hàng giảm giá ${existingDiscount}%. Bạn có muốn ghi đè thành ${discountPercentage}% cho tất cả lô hàng không? (Đồng ý/Hủy bỏ)`
      };
    }

    const confirmResult = await this.actionExecutor.execute(session, 'MANAGE_BATCH_DISCOUNT', actionPayload);

    if (confirmResult.requiresConfirmation) {
      metadata.pendingAction = {
        type: 'MANAGE_BATCH_DISCOUNT',
        state: 'CONFIRMING',
        data: actionPayload
      };
      await this.chatRepo.updateSessionMetadata(session.id, metadata);

      return {
        intent: 'MANAGE_BATCH_DISCOUNT',
        reply: `Xác nhận thiết lập giảm giá ${discountPercentage}% cho tất cả lô hàng của sản phẩm "${product.name}"? (Đồng ý/Hủy bỏ)`
      };
    }

    if (!confirmResult.success) {
      return {
        intent: 'MANAGE_BATCH_DISCOUNT',
        reply: `Không thể cập nhật giảm giá: ${confirmResult.error}`
      };
    }

    return {
      intent: 'MANAGE_BATCH_DISCOUNT',
      reply: `Đã áp dụng giảm giá ${discountPercentage}% cho các lô hàng của sản phẩm "${product.name}" thành công.`
    };
  }

  // 10. LOCATE_PRODUCT
  async handleLocateProduct(session, userMessage) {
    const storeId = session.storeId || session.store_id || 1;

    // Extract keyword by stripping locate/intent trigger words
    const triggerWords = ['vị trí', 'ở đâu', 'nằm ở', 'chỗ nào', 'location', 'kệ nào', 'kho nào', 'tìm vị trí', 'tìm', 'kiểm tra'];
    let keyword = userMessage.toLowerCase();
    for (const tw of triggerWords) {
      keyword = keyword.replace(tw, '');
    }
    keyword = keyword.replace(/[?.,!:-]/g, '').trim();

    if (!keyword) {
      return {
        intent: 'LOCATE_PRODUCT',
        reply: 'Vui lòng nhập tên sản phẩm bạn muốn tìm vị trí (ví dụ: "Vị trí Bia Heineken").',
        products: null
      };
    }

    // Resolve product ID using RAG
    let resolvedProduct = null;
    try {
      const resolved = await this.utils.resolveProductsByRAG(keyword, storeId, 1);
      const productCandidates = resolved.products || [];
      if (productCandidates.length > 0) {
        resolvedProduct = productCandidates[0];
      }
    } catch (err) {
      logger.error({ err }, 'Failed to resolve product by RAG for LOCATE_PRODUCT');
    }

    if (!resolvedProduct) {
      return {
        intent: 'LOCATE_PRODUCT',
        reply: `Không tìm thấy sản phẩm nào khớp với từ khóa: "${keyword}".`,
        products: null
      };
    }

    const productId = resolvedProduct.id;
    const productName = resolvedProduct.name;

    // Fetch map data to search location
    let locationsFound = [];
    try {
      const mapRes = await this.apiClient.getStoreMapData(storeId);
      if (mapRes && mapRes.success && mapRes.data) {
        const blocks = mapRes.data;
        for (const block of blocks) {
          for (const loc of (block.locations || [])) {
            const hasProduct = (loc.products || []).find(p => String(p.productId) === String(productId));
            if (hasProduct) {
              locationsFound.push({
                blockName: block.name,
                blockType: block.type,
                locationName: loc.name,
                quantity: hasProduct.totalOnShelf || 0
              });
            }
          }
        }
      }
    } catch (err) {
      logger.error({ err }, 'Failed to fetch store map data or parse locations');
    }

    if (locationsFound.length === 0) {
      return {
        intent: 'LOCATE_PRODUCT',
        reply: `Sản phẩm **${productName}** hiện chưa được sắp xếp vị trí nào trên kệ/kho.`,
        products: [resolvedProduct],
        action: {
          type: 'NAVIGATE',
          payload: {
            path: `/inventory/locations?highlight=${productId}`,
            productName
          }
        }
      };
    }

    const locLines = locationsFound.map(lf => {
      const typeText = lf.blockType === 'store_shelf' ? 'Kệ cửa hàng' : 'Kho trung tâm';
      return `- **${lf.locationName}** thuộc block *${lf.blockName}* (${typeText}), số lượng: **${lf.quantity}**`;
    }).join('\n');

    const reply = `Tìm thấy vị trí cho sản phẩm **${productName}**:\n${locLines}\n\nTôi đang hiển thị bản đồ và làm nổi bật (highlight) kệ hàng chứa sản phẩm này cho bạn.`;

    return {
      intent: 'LOCATE_PRODUCT',
      reply,
      products: [resolvedProduct],
      action: {
        type: 'NAVIGATE',
        payload: {
          path: `/inventory/locations?highlight=${productId}`,
          productName
        }
      }
    };
  }
}

module.exports = EntityManagerHandler;
