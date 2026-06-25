/**
 * Report Handler — Manager BI Statistics & Analytics reports.
 * Handles: REPORT_SALES, REPORT_TOP_PRODUCTS, REPORT_LOW_STOCK, REPORT_PROFIT.
 */

class ReportHandler {
  constructor(ctx) {
    this.chatRepo = ctx.chatRepo;
    this.apiClient = ctx.apiClient;
    this.utils = ctx.utils;
  }

  formatVND(amount) {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  }

  parseDates(message) {
    const now = new Date();
    const msg = message.toLowerCase();
    let startDate = new Date();
    let endDate = new Date();
    let period = 'month';

    if (msg.includes('hôm nay')) {
      startDate.setHours(0, 0, 0, 0);
      endDate.setHours(23, 59, 59, 999);
      period = 'today';
    } else if (msg.includes('hôm qua')) {
      startDate.setDate(now.getDate() - 1);
      startDate.setHours(0, 0, 0, 0);
      endDate.setDate(now.getDate() - 1);
      endDate.setHours(23, 59, 59, 999);
      period = 'custom';
    } else if (msg.includes('này') && (msg.includes('tuần') || msg.includes('tuần này'))) {
      const day = now.getDay() || 7;
      startDate.setDate(now.getDate() - day + 1);
      startDate.setHours(0, 0, 0, 0);
      endDate.setHours(23, 59, 59, 999);
      period = 'week';
    } else if (msg.includes('tháng này') || msg.includes('tháng')) {
      startDate.setDate(1);
      startDate.setHours(0, 0, 0, 0);
      endDate.setHours(23, 59, 59, 999);
      period = 'month';
    } else if (msg.includes('năm nay')) {
      startDate.setMonth(0, 1);
      startDate.setHours(0, 0, 0, 0);
      endDate.setHours(23, 59, 59, 999);
      period = 'year';
    } else {
      // Default: Last 30 days
      startDate.setDate(now.getDate() - 30);
      startDate.setHours(0, 0, 0, 0);
      endDate.setHours(23, 59, 59, 999);
      period = 'month';
    }

    return {
      startDate: startDate.toISOString(),
      endDate: endDate.toISOString(),
      period
    };
  }

  async handleSalesReport(session, userMessage) {
    const userType = session.userType || session.user_type || 'customer';
    if (userType !== 'manager') {
      return {
        intent: 'REPORT_SALES',
        reply: 'Từ chối truy cập: Chỉ Quản lý hoặc Admin mới có quyền xem báo cáo doanh thu.',
        products: null
      };
    }

    const { startDate, endDate, period } = this.parseDates(userMessage);
    const result = await this.apiClient.getSalesReport({ startDate, endDate });

    if (!result.success) {
      return {
        intent: 'REPORT_SALES',
        reply: `Không thể tải báo cáo doanh thu: ${result.error}`,
        products: null
      };
    }

    const summary = result.data.summary || {};
    const products = result.data.products || [];

    // Format top 3 products
    const topProductsText = products.slice(0, 3).map((p, idx) =>
      `${idx + 1}. **${p.productName}** (${p.productCode}): Bán ${p.totalQuantity} SP, Doanh thu: ${this.formatVND(p.totalRevenue)}`
    ).join('\n') || 'Không có sản phẩm nào bán ra.';

    const reply = `### 📊 BÁO CÁO DOANH THU CHI TIẾT
Khoảng thời gian: từ *${new Date(startDate).toLocaleDateString('vi-VN')}* đến *${new Date(endDate).toLocaleDateString('vi-VN')}*

* **Tổng doanh thu:** ${this.formatVND(summary.totalRevenue || 0)}
* **Tổng số lượng bán:** ${summary.totalQuantity || 0} sản phẩm
* **Số đơn hàng đã hoàn tất:** ${summary.totalOrders || 0} đơn
* **Giá trị đơn hàng trung bình:** ${this.formatVND(summary.averageOrderValue || 0)}

#### 🏆 Top sản phẩm bán chạy nhất:
${topProductsText}

Tôi đã chuẩn bị sẵn màn hình phân tích trực quan cho bạn dưới đây.`;

    return {
      intent: 'REPORT_SALES',
      reply,
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: `/reports/sales?period=${period}` }
      }
    };
  }

  async handleTopProducts(session, userMessage) {
    const userType = session.userType || session.user_type || 'customer';
    if (userType !== 'manager') {
      return {
        intent: 'REPORT_TOP_PRODUCTS',
        reply: 'Từ chối truy cập: Chỉ Quản lý hoặc Admin mới có quyền xem thông tin bán chạy.',
        products: null
      };
    }

    const { startDate, endDate, period } = this.parseDates(userMessage);
    const result = await this.apiClient.getSalesReport({ startDate, endDate });

    if (!result.success) {
      return {
        intent: 'REPORT_TOP_PRODUCTS',
        reply: `Không thể tải dữ liệu sản phẩm chạy nhất: ${result.error}`,
        products: null
      };
    }

    const products = result.data.products || [];
    const sortedByQty = [...products].sort((a, b) => b.totalQuantity - a.totalQuantity);

    const listText = sortedByQty.slice(0, 5).map((p, idx) =>
      `${idx + 1}. **${p.productName}** - Bán ${p.totalQuantity} SP (${this.formatVND(p.totalRevenue)})`
    ).join('\n') || 'Không có sản phẩm nào.';

    const reply = `### 🏆 SẢN PHẨM BÁN CHẠY NHẤT
Thời gian check: *${new Date(startDate).toLocaleDateString('vi-VN')}* - *${new Date(endDate).toLocaleDateString('vi-VN')}*

Tải thành công top 5 sản phẩm đạt sản lượng bán cao nhất:
${listText}

Bạn có thể tham khảo biểu đồ cơ cấu ngành hàng tại trang Phân tích Doanh thu.`;

    return {
      intent: 'REPORT_TOP_PRODUCTS',
      reply,
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: `/reports/sales?period=${period}` }
      }
    };
  }

  async handleLowStock(session, userMessage) {
    const userType = session.userType || session.user_type || 'customer';
    if (userType !== 'manager') {
      return {
        intent: 'REPORT_LOW_STOCK',
        reply: 'Từ chối truy cập: Chỉ Quản lý hoặc Admin mới có quyền xem thông tin tồn kho.',
        products: null
      };
    }

    const result = await this.apiClient.getInventoryReport({ view: 'needs-reorder' });

    if (!result.success) {
      return {
        intent: 'REPORT_LOW_STOCK',
        reply: `Không thể tải báo cáo tồn kho: ${result.error}`,
        products: null
      };
    }

    const products = result.data.products || [];
    const lowStockItems = products.filter(p => p.status === 'low-stock');
    const outOfStockItems = products.filter(p => p.status === 'out-of-stock');

    const lowStockText = lowStockItems.slice(0, 3).map(p =>
      `* **${p.productName}** (${p.productCode}): Còn ${p.quantityOnHand} SP (Định mức reorder: ${p.reorderPoint})`
    ).join('\n') || 'Không có.';

    const outOfStockText = outOfStockItems.slice(0, 3).map(p =>
      `* **${p.productName}** (${p.productCode}): **Hết hàng hoàn toàn!**`
    ).join('\n') || 'Không có.';

    const reply = `### ⚠️ CẢNH BÁO TỒN KHO & REORDER
Danh sách các sản phẩm đang cạn kiệt hoặc dưới mức định mức:

#### 🚫 Hết hàng (Out of Stock - Top 3):
${outOfStockText}

#### 📉 Tồn kho thấp (Low Stock - Top 3):
${lowStockText}

Tổng cộng có **${products.length}** sản phẩm cần nhập thêm hàng.`;

    return {
      intent: 'REPORT_LOW_STOCK',
      reply,
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: '/reports/inventory' }
      }
    };
  }

  async handleProfitReport(session, userMessage) {
    const userType = session.userType || session.user_type || 'customer';
    if (userType !== 'manager') {
      return {
        intent: 'REPORT_PROFIT',
        reply: 'Từ chối truy cập: Chỉ Quản lý hoặc Admin mới có quyền xem báo cáo lợi nhuận.',
        products: null
      };
    }

    const currentYear = new Date().getFullYear();
    const result = await this.apiClient.getProfitReport({ year: currentYear });

    if (!result.success) {
      return {
        intent: 'REPORT_PROFIT',
        reply: `Không thể tải báo cáo lợi nhuận: ${result.error}`,
        products: null
      };
    }

    const summary = result.data.summary || {};
    const reply = `### 📈 BÁO CÁO LỢI NHUẬN NĂM ${currentYear}
Số liệu tổng hợp sơ bộ hoạt động kinh doanh:

* **Doanh thu gộp:** ${this.formatVND(summary.combinedRevenue || summary.totalRevenue || 0)}
* **Giá vốn hàng bán (COGS):** ${this.formatVND(summary.combinedCost || summary.totalCost || 0)}
* **Lợi nhuận gộp:** ${this.formatVND(summary.grossProfit || 0)}
* **Tỷ suất lợi nhuận gộp:** ${(summary.profitMargin || 0).toFixed(2)}%

*Số liệu trên đã bao gồm điều chỉnh chênh lệch xuất bán và mất mát tồn kho thực tế.*`;

    return {
      intent: 'REPORT_PROFIT',
      reply,
      products: null,
      action: {
        type: 'NAVIGATE',
        payload: { path: '/reports/profit' }
      }
    };
  }
}

module.exports = ReportHandler;
