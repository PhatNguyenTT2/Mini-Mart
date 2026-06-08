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
    const keywords = ['tìm khách hàng', 'tìm kiếm khách hàng', 'tìm khách', 'search khách hàng', 'search khách', 'tìm kiếm', 'tìm'];
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
      products: null
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
    const keywords = ['tìm nhà cung cấp', 'tìm kiếm nhà cung cấp', 'tìm ncc', 'search nhà cung cấp', 'search ncc', 'tìm'];
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
      reply: `Tìm thấy nhà cung cấp: **${supplier.name}**\n* Địa chỉ: ${supplier.address || 'N/A'}\n* Số điện thoại: ${contact}\n* Email: ${email}`,
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: `/suppliers?search=${encodeURIComponent(supplier.name)}` }
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
        reply = `### 🚨 CẢNH BÁO HẾT HÀNG TRONG KHO\nPhát hiện **${outOfStockWarehouse.length} mặt hàng** đã hết hoàn toàn trong kho chính:\n\n${listText}${outOfStockWarehouse.length > 5 ? `\n... và ${outOfStockWarehouse.length - 5} sản phẩm khác.` : ''}`;
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
        reply = `### 🚨 CẢNH BÁO TRỐNG KỆ (STOCKOUT ON SHELF)\nPhát hiện **${outOfStockShelf.length} mặt hàng** đã hết hoàn toàn trên kệ trưng bày:\n\n${listText}${outOfStockShelf.length > 5 ? `\n... và ${outOfStockShelf.length - 5} sản phẩm khác.` : ''}\n\nĐề xuất: Nên thực hiện châm hàng (trưng bày bổ sung) từ kho chính lên kệ.`;
      }
    } else {
      // General out of stock or check both
      const outOfStockWarehouse = items.filter(p => (p.quantityOnHand || 0) === 0);
      const outOfStockShelf = items.filter(p => (p.quantityOnShelf || 0) === 0);

      const parts = [];
      parts.push(`### 📋 TỔNG HỢP SẢN PHẨM HẾT HÀNG`);

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
}

module.exports = EntityManagerHandler;
