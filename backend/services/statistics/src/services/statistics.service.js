const cache = require('../cache/redis');
const { getPeriodDates, calculateChange, formatDateKey } = require('../utils/period');
const logger = require('../../../../shared/common/logger');

const CACHE_TTL = {
  DASHBOARD: 300,  // 5 minutes
  REPORT: 900      // 15 minutes
};

class StatisticsService {
  constructor({ orderClient, catalogClient, authClient, supplierClient, inventoryClient }) {
    this.orderClient = orderClient;
    this.catalogClient = catalogClient;
    this.authClient = authClient;
    this.supplierClient = supplierClient;
    this.inventoryClient = inventoryClient;
  }

  /**
   * Dashboard Statistics
   * Aggregates: orders + customers + categories
   */
  async getDashboard(token, period = 'year') {
    const cacheKey = cache.buildKey('dashboard', 'all', { period });
    const cached = await cache.get(cacheKey);
    if (cached) {
      logger.info({ cacheKey }, 'Dashboard served from cache');
      return cached;
    }

    const { startDate, endDate, prevStartDate, prevEndDate } = getPeriodDates(period);

    // Fetch data from services in parallel (Optimized with date filtering at DB level)
    const [currentOrders, previousOrders, customers, catalogProducts, catalogCategories, productSales] = await Promise.all([
      this.orderClient.getOrders(token, {
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        status: 'delivered',
        paymentStatus: 'paid'
      }),
      this.orderClient.getOrders(token, {
        startDate: prevStartDate.toISOString(),
        endDate: prevEndDate.toISOString(),
        status: 'delivered',
        paymentStatus: 'paid'
      }),
      this.authClient.getCustomers(token),
      this.catalogClient.getProducts(token),
      this.catalogClient.getCategories(token),
      this.orderClient.getProductSalesAggregated(token, {
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString()
      })
    ]);

    // Ensure inputs are arrays to prevent crashes on client errors
    const currentOrdersList = currentOrders || [];
    const previousOrdersList = previousOrders || [];
    const customersList = customers || [];
    const productsList = catalogProducts || [];
    const categoriesList = catalogCategories || [];
    const productSalesList = productSales || [];

    // Summary metrics
    const currentTotalOrders = currentOrdersList.length;
    const previousTotalOrders = previousOrdersList.length;

    const currentTotalRevenue = currentOrdersList.reduce((sum, o) => sum + (parseFloat(o?.total_amount || o?.total || 0) || 0), 0);
    const previousTotalRevenue = previousOrdersList.reduce((sum, o) => sum + (parseFloat(o?.total_amount || o?.total || 0) || 0), 0);

    // Sales quantity (use item_count or estimate from orders)
    const currentTotalSales = currentOrders.reduce((sum, o) => sum + (o.item_count || 1), 0);
    const previousTotalSales = previousOrders.reduce((sum, o) => sum + (o.item_count || 1), 0);

    // New customers in period
    const currentNewCustomers = customersList.filter(c =>
      c?.created_at && new Date(c.created_at) >= startDate && new Date(c.created_at) <= endDate
    ).length;
    const previousNewCustomers = customersList.filter(c =>
      c?.created_at && new Date(c.created_at) >= prevStartDate && new Date(c.created_at) <= prevEndDate
    ).length;

    // Changes
    const changes = {
      totalOrders: calculateChange(currentTotalOrders, previousTotalOrders),
      totalSales: calculateChange(currentTotalSales, previousTotalSales),
      newCustomers: calculateChange(currentNewCustomers, previousNewCustomers),
      totalRevenue: calculateChange(currentTotalRevenue, previousTotalRevenue)
    };

    // Order trend chart data
    const orderTrend = this._buildOrderTrend(currentOrdersList, previousOrdersList, period, startDate, endDate, prevStartDate, prevEndDate);

    // Top categories based on parent rollup
    const productInfo = {};
    productsList.forEach(p => { if (p && p.id) productInfo[p.id] = p; });

    const categoryMap = {};
    categoriesList.forEach(c => { if (c && c.id) categoryMap[c.id] = c; });

    const topCategories = this._buildTopCategoriesDerived(productSalesList, productInfo, categoryMap);

    // Recent transactions with correct customer mapping
    const customerMap = {};
    customersList.forEach(c => { if (c && c.id) customerMap[c.id] = c; });

    const transactions = [...currentOrdersList]
      .sort((a, b) => new Date(b?.orderDate || b?.order_date || b?.created_at || 0) - new Date(a?.orderDate || a?.order_date || a?.created_at || 0))
      .slice(0, 10)
      .map(order => {
        if (!order) return null;
        const custId = order.customerId || order.customer_id;
        const cust = customerMap[custId];
        const dateVal = order.orderDate || order.order_date || order.created_at || order.createdAt;
        return {
          id: order.orderNumber || order.order_number || `ORD-${order.id}`,
          customer: cust ? (cust.name || cust.fullName) : 'Walk-in',
          phone: cust ? (cust.phone || cust.phoneNumber) : 'N/A',
          amount: parseFloat(order.total || order.total_amount || 0) || 0,
          date: dateVal ? new Date(dateVal).toLocaleDateString('vi-VN') : 'N/A',
          status: order.status || 'unknown'
        };
      })
      .filter(Boolean);

    const result = {
      totalOrders: currentTotalOrders,
      totalSales: currentTotalSales,
      newCustomers: currentNewCustomers,
      totalRevenue: currentTotalRevenue,
      changes,
      orderTrend,
      topCategories,
      transactions
    };

    await cache.set(cacheKey, result, CACHE_TTL.DASHBOARD);
    return result;
  }

  /**
   * Sales Report
   */
  async getSalesReport(token, params) {
    const { startDate, endDate } = params;
    const cacheKey = cache.buildKey('sales', 'all', params);
    const cached = await cache.get(cacheKey);
    if (cached) return cached;

    // Fetch pre-aggregated product sales & catalog info in parallel
    const [revenueByProduct, products, categories] = await Promise.all([
      this.orderClient.getProductSalesAggregated(token, { startDate, endDate }),
      this.catalogClient.getProducts(token),
      this.catalogClient.getCategories(token)
    ]);

    const productsList = products || [];
    const categoriesList = categories || [];
    const revenueList = revenueByProduct || [];

    const productInfo = {};
    productsList.forEach(p => { if (p && p.id) productInfo[p.id] = p; });

    const categoryMap = {};
    categoriesList.forEach(c => { if (c && c.id) categoryMap[c.id] = c; });

    const enrichedProducts = revenueList.map(r => {
      const info = productInfo[r.productId] || {};
      const catId = info.category_id || info.categoryId || null;
      const rootCat = this._getRootCategory(catId, categoryMap);
      const parentCategoryId = rootCat.id || null;
      const parentCategoryName = rootCat.name || 'Uncategorized';
      const categoryName = info.categoryName || (catId && categoryMap[catId]?.name) || 'Uncategorized';
      return {
        productId: r.productId,
        productName: info.name || r.productName || `Product #${r.productId}`,
        productCode: info.barcode || info.productCode || info.product_code || 'N/A',
        barcode: info.barcode || null,
        categoryName,
        parentCategoryId,
        parentCategoryName,
        totalQuantity: r.totalQuantity || 0,
        totalRevenue: r.totalRevenue || 0,
        orderCount: r.orderCount || 0,
        averageSellingPrice: r.totalQuantity > 0 ? r.totalRevenue / r.totalQuantity : 0
      };
    });

    const totalRevenue = enrichedProducts.reduce((sum, p) => sum + p.totalRevenue, 0);
    const totalQuantity = enrichedProducts.reduce((sum, p) => sum + p.totalQuantity, 0);

    const orders = await this.orderClient.getOrders(token, {
      startDate,
      endDate,
      status: 'delivered',
      paymentStatus: 'paid'
    });
    const totalActualOrders = orders ? orders.length : 0;

    const result = {
      summary: {
        totalRevenue,
        totalOrders: totalActualOrders,
        totalQuantity,
        totalProducts: enrichedProducts.length,
        averageOrderValue: totalActualOrders > 0 ? totalRevenue / totalActualOrders : 0
      },
      products: enrichedProducts
    };

    await cache.set(cacheKey, result, CACHE_TTL.REPORT);
    return result;
  }

  /**
   * Purchase Report
   */
  async getPurchaseReport(token, params) {
    const { startDate, endDate } = params;
    const cacheKey = cache.buildKey('purchases', 'all', params);
    const cached = await cache.get(cacheKey);
    if (cached) return cached;

    // Fetch pre-aggregated product costs & catalog info in parallel
    const [costByProduct, products, categories] = await Promise.all([
      this.supplierClient.getProductCostsAggregated(token, { startDate: params.startDate, endDate: params.endDate }),
      this.catalogClient.getProducts(token),
      this.catalogClient.getCategories(token)
    ]);

    const productsList = products || [];
    const categoriesList = categories || [];
    const costList = costByProduct || [];

    const productInfo = {};
    productsList.forEach(p => { if (p && p.id) productInfo[p.id] = p; });

    const categoryMap = {};
    categoriesList.forEach(c => { if (c && c.id) categoryMap[c.id] = c; });

    const enrichedProducts = costList.map(c => {
      const info = productInfo[c.productId] || {};
      const catId = info.category_id || info.categoryId || null;
      const rootCat = this._getRootCategory(catId, categoryMap);
      const parentCategoryId = rootCat.id || null;
      const parentCategoryName = rootCat.name || 'Uncategorized';
      const categoryName = info.categoryName || (catId && categoryMap[catId]?.name) || 'Uncategorized';
      return {
        productId: c.productId,
        productName: info.name || c.productName || `Product #${c.productId}`,
        productCode: info.barcode || info.productCode || info.product_code || 'N/A',
        barcode: info.barcode || null,
        categoryName,
        parentCategoryId,
        parentCategoryName,
        totalQuantity: c.totalQuantity || 0,
        totalCost: c.totalCost || 0,
        poCount: c.poCount || 0,
        averageCostPrice: c.totalQuantity > 0 ? c.totalCost / c.totalQuantity : 0
      };
    });

    const totalCost = enrichedProducts.reduce((sum, p) => sum + p.totalCost, 0);
    const totalQuantity = enrichedProducts.reduce((sum, p) => sum + p.totalQuantity, 0);

    const pos = await this.supplierClient.getPurchaseOrders(token, {
      startDate: params.startDate,
      endDate: params.endDate,
      status: 'received'
    });
    const totalActualPOs = pos ? pos.length : 0;

    const result = {
      summary: {
        totalCost,
        totalOrders: totalActualPOs,
        totalQuantity,
        totalProducts: enrichedProducts.length,
        averageOrderValue: totalActualPOs > 0 ? totalCost / totalActualPOs : 0
      },
      products: enrichedProducts
    };

    await cache.set(cacheKey, result, CACHE_TTL.REPORT);
    return result;
  }

  /**
   * Profit Report
   */
  async getProfitReport(token, params) {
    const cacheKey = cache.buildKey('profit', 'all', params);
    const cached = await cache.get(cacheKey);
    if (cached) return cached;

    const year = params.year || new Date().getFullYear();
    const startDate = `${year}-01-01`;
    const endDate = `${year}-12-31`;

    // Fetch pre-aggregated data (SQL GROUP BY) to prevent OOM
    const [revenueByProduct, costByProduct, stockOutAggregates, products, categories] = await Promise.all([
      this.orderClient.getProductSalesAggregated(token, { startDate, endDate }),
      this.supplierClient.getProductCostsAggregated(token, { startDate, endDate }),
      this.inventoryClient.getProductStockOutAggregated(token, { startDate, endDate }),
      this.catalogClient.getProducts(token),
      this.catalogClient.getCategories(token)
    ]);

    const productsList = products || [];
    const categoriesList = categories || [];
    const revenueByProductList = revenueByProduct || [];
    const costByProductList = costByProduct || [];
    const stockOutList = stockOutAggregates || [];

    const productInfo = {};
    productsList.forEach(p => { if (p && p.id) productInfo[p.id] = p; });

    const categoryMap = {};
    categoriesList.forEach(c => { if (c && c.id) categoryMap[c.id] = c; });

    const revenueMap = {};
    revenueByProductList.forEach(r => { if (r && r.productId) revenueMap[r.productId] = r; });

    const costMap = {};
    costByProductList.forEach(c => { if (c && c.productId) costMap[c.productId] = c; });

    const stockOutSalesMap = {};
    const stockOutLossMap = {};
    let totalStockOutSalesRevenue = 0;
    let totalStockOutLossValue = 0;
    let totalStockOutSalesOrdersCount = 0;
    let totalStockOutLossOrdersCount = 0;

    stockOutList.forEach(s => {
      if (!s) return;
      const pid = s.product_id || s.productId;
      const reasonLower = (s.reason || '').toLowerCase();
      const isSales = ['sales', 'sale', 'xuất bán', 'ban', 'bán'].includes(reasonLower);
      const qty = parseInt(s.total_quantity || s.totalQuantity || 0) || 0;
      const val = parseFloat(s.total_price || s.totalPrice || 0) || 0;
      const orders = parseInt(s.order_count || s.orderCount || 0) || 0;

      if (isSales) {
        totalStockOutSalesRevenue += val;
        totalStockOutSalesOrdersCount += orders;
        if (!stockOutSalesMap[pid]) {
          stockOutSalesMap[pid] = { qty: 0, val: 0, orders: 0 };
        }
        stockOutSalesMap[pid].qty += qty;
        stockOutSalesMap[pid].val += val;
        stockOutSalesMap[pid].orders += orders;
      } else {
        totalStockOutLossValue += val;
        totalStockOutLossOrdersCount += orders;
        if (!stockOutLossMap[pid]) {
          stockOutLossMap[pid] = { qty: 0, val: 0, orders: 0 };
        }
        stockOutLossMap[pid].qty += qty;
        stockOutLossMap[pid].val += val;
        stockOutLossMap[pid].orders += orders;
      }
    });

    const allProductIds = new Set([
      ...Object.keys(revenueMap),
      ...Object.keys(costMap),
      ...Object.keys(stockOutSalesMap),
      ...Object.keys(stockOutLossMap)
    ]);

    const profitProducts = [...allProductIds].map(pid => {
      const rev = revenueMap[pid] || { totalRevenue: 0, totalQuantity: 0, orderCount: 0 };
      const cost = costMap[pid] || { totalCost: 0, totalQuantity: 0, poCount: 0 };
      const soSales = stockOutSalesMap[pid] || { qty: 0, val: 0, orders: 0 };
      const soLoss = stockOutLossMap[pid] || { qty: 0, val: 0, orders: 0 };
      const info = productInfo[pid] || {};

      const revenue = rev.totalRevenue || 0;
      const totalCost = cost.totalCost || 0;
      const quantitySold = rev.totalQuantity || 0;
      const quantityPurchased = cost.totalQuantity || 0;

      const rawName = info.name || rev.productName || cost.productName || `Product #${pid}`;
      const productName = !info.name ? `[Đã ngừng kinh doanh] ${rawName}` : rawName;

      const combinedProductRevenue = revenue + soSales.val;
      const combinedProductCost = totalCost + soLoss.val;
      const profit = combinedProductRevenue - combinedProductCost;
      const profitMargin = combinedProductRevenue > 0 ? (profit / combinedProductRevenue) * 100 : 0;

      const catId = info.category_id || info.categoryId || null;
      const rootCat = this._getRootCategory(catId, categoryMap);
      const parentCategoryId = rootCat.id || null;
      const parentCategoryName = rootCat.name || 'Uncategorized';
      return {
        productId: pid,
        productName,
        productCode: info.barcode || info.productCode || info.product_code || 'N/A',
        categoryName: info.categoryName || (catId && categoryMap[catId]?.name) || 'Uncategorized',
        parentCategoryId,
        parentCategoryName,
        image: info.image || null,
        totalRevenue: revenue,
        quantitySold,
        salesOrders: rev.orderCount || 0,
        averageSellingPrice: quantitySold > 0 ? revenue / quantitySold : 0,
        totalCost,
        quantityPurchased,
        purchaseOrders: cost.poCount || 0,
        averageCostPrice: quantityPurchased > 0 ? totalCost / quantityPurchased : 0,
        profit,
        profitPerUnit: quantitySold > 0 ? profit / quantitySold : 0,
        profitMargin,
        stockOutSalesQuantity: soSales.qty,
        stockOutSalesRevenue: soSales.val,
        stockOutSalesOrders: soSales.orders,
        stockOutLossQuantity: soLoss.qty,
        stockOutLossValue: soLoss.val,
        stockOutLossOrders: soLoss.orders
      };
    }).sort((a, b) => b.profit - a.profit);

    const totalRevenue = profitProducts.reduce((sum, p) => sum + p.totalRevenue, 0);
    const totalCost = profitProducts.reduce((sum, p) => sum + p.totalCost, 0);
    const grossProfit = (totalRevenue + totalStockOutSalesRevenue) - (totalCost + totalStockOutLossValue);

    const monthlyData = await this._buildMonthlyProfit(token, year);

    const result = {
      summary: {
        totalRevenue,
        totalSalesOrders: revenueByProductList.reduce((sum, r) => sum + (r.orderCount || 0), 0),
        stockOutSalesRevenue: totalStockOutSalesRevenue,
        totalStockOutSalesOrders: totalStockOutSalesOrdersCount,
        totalCost,
        totalPurchaseOrders: costByProductList.reduce((sum, c) => sum + (c.poCount || 0), 0),
        stockOutLossValue: totalStockOutLossValue,
        totalStockOutLossOrders: totalStockOutLossOrdersCount,
        combinedRevenue: totalRevenue + totalStockOutSalesRevenue,
        combinedCost: totalCost + totalStockOutLossValue,
        grossProfit,
        profitMargin: (totalRevenue + totalStockOutSalesRevenue) > 0
          ? (grossProfit / (totalRevenue + totalStockOutSalesRevenue)) * 100
          : 0
      },
      monthlyData,
      products: profitProducts
    };

    await cache.set(cacheKey, result, CACHE_TTL.REPORT);
    return result;
  }

  // Monthly trend helper
  async _buildMonthlyProfit(token, year) {
    const months = Array.from({ length: 12 }, (_, i) => ({
      month: i + 1,
      label: new Date(year, i).toLocaleString('en', { month: 'short' }),
      revenue: 0,
      cost: 0,
      profit: 0
    }));

    const [orders, pos] = await Promise.all([
      this.orderClient.getOrders(token, {
        startDate: `${year}-01-01`,
        endDate: `${year}-12-31`,
        status: 'delivered',
        paymentStatus: 'paid'
      }),
      this.supplierClient.getPurchaseOrders(token, {
        startDate: `${year}-01-01`,
        endDate: `${year}-12-31`,
        status: 'received'
      })
    ]);

    const ordersList = orders || [];
    const posList = pos || [];

    ordersList.forEach(o => {
      if (!o) return;
      const date = o.orderDate || o.order_date || o.createdAt || o.created_at;
      if (date) {
        const m = new Date(date).getMonth();
        if (m >= 0 && m < 12) {
          months[m].revenue += o.total || parseFloat(o.total_amount) || 0;
        }
      }
    });

    posList.forEach(po => {
      if (!po) return;
      const date = po.orderDate || po.order_date || po.createdAt || po.created_at;
      if (date) {
        const m = new Date(date).getMonth();
        if (m >= 0 && m < 12) {
          months[m].cost += po.totalPrice || parseFloat(po.total_price) || 0;
        }
      }
    });

    months.forEach(m => {
      m.profit = m.revenue - m.cost;
    });

    return months;
  }

  /**
   * Inventory Report
   */
  async getInventoryReport(token, params) {
    const cacheKey = cache.buildKey('inventory', 'all', params);
    const cached = await cache.get(cacheKey);
    if (cached) return cached;

    // 1. Get raw inventory summary from inventory service
    const rawItems = await this.inventoryClient.getSummary(token) || [];
    const rawItemsList = rawItems || [];

    // 2. Fetch products and categories from Catalog for enrichment
    const [catalogProducts, catalogCategories] = await Promise.all([
      this.catalogClient.getProducts(token),
      this.catalogClient.getCategories(token)
    ]);

    const catalogProductsList = catalogProducts || [];
    const catalogCategoriesList = catalogCategories || [];

    const productMap = {};
    catalogProductsList.forEach(p => {
      if (p && p.id) productMap[p.id] = p;
    });

    const categoryMap = {};
    catalogCategoriesList.forEach(c => {
      if (c && c.id) categoryMap[c.id] = c;
    });

    const getFullCategoryName = (catId) => {
      if (!catId || !categoryMap[catId]) return 'Uncategorized';
      const cat = categoryMap[catId];
      if (cat.parent_id && categoryMap[cat.parent_id]) {
        return `${categoryMap[cat.parent_id].name} > ${cat.name}`;
      }
      return cat.name;
    };

    // 3. Formulate the list of products for reporting, applying filters
    let products = rawItemsList.map(item => {
      const p = productMap[item.productId] || {};
      const status = item.quantityOnHand <= 0 ? 'out-of-stock' : (item.quantityOnHand <= item.reorderPoint ? 'low-stock' : 'in-stock');
      const catId = p.category_id || p.categoryId || null;
      const rootCat = this._getRootCategory(catId, categoryMap);
      const parentCategoryId = rootCat.id || null;
      const parentCategoryName = rootCat.name || 'Uncategorized';
      return {
        id: item.productId,
        productId: item.productId,
        productName: p.name || item.product?.name || `Product #${item.productId}`,
        productCode: p.barcode || p.productCode || p.product_code || 'N/A',
        barcode: p.barcode || null,
        image: p.image || item.product?.image || null,
        categoryId: catId,
        categoryName: getFullCategoryName(catId),
        parentCategoryId,
        parentCategoryName,
        quantityOnHand: item.quantityOnHand || 0,
        quantityOnShelf: item.quantityOnShelf || 0,
        quantityAvailable: item.quantityAvailable || 0,
        reorderPoint: item.reorderPoint || 10,
        status,
        value: (item.quantityOnHand || 0) * parseFloat(p.unit_price || p.unitPrice || item.product?.unitPrice || 0)
      };
    });

    // Filter by Category and View if requested
    if (params.categoryId) {
      products = products.filter(p => String(p.categoryId) === String(params.categoryId));
    }
    if (params.view === 'low-stock') {
      products = products.filter(p => p.status === 'low-stock');
    } else if (params.view === 'out-of-stock') {
      products = products.filter(p => p.status === 'out-of-stock');
    } else if (params.view === 'needs-reorder') {
      products = products.filter(p => p.quantityOnHand <= p.reorderPoint);
    }

    // 4. Summarize metrics
    const totalProducts = products.length;
    const totalValue = products.reduce((sum, p) => sum + p.value, 0);
    const lowStockCount = products.filter(p => p.status === 'low-stock').length;
    const outOfStockCount = products.filter(p => p.status === 'out-of-stock').length;
    const inStockCount = products.filter(p => p.status === 'in-stock').length;

    const totalQuantity = products.reduce((sum, p) => sum + p.quantityOnHand, 0);
    const totalShelfStock = products.reduce((sum, p) => sum + p.quantityOnShelf, 0);
    const totalWarehouseStock = totalQuantity - totalShelfStock;

    const warehouseUtilization = totalQuantity > 0 ? parseFloat(((totalWarehouseStock / totalQuantity) * 100).toFixed(1)) : 0;
    const shelfUtilization = totalQuantity > 0 ? parseFloat(((totalShelfStock / totalQuantity) * 100).toFixed(1)) : 0;
    const needsReorderItems = products.filter(p => p.quantityOnHand <= p.reorderPoint).length;

    // mock expiring soon (items that have active batches with expiry <= 30 days)
    const expiringSoonCount = 0;

    // 5. Stock Status structure
    const stockStatus = {
      inStock: inStockCount,
      lowStock: lowStockCount,
      outOfStock: outOfStockCount,
      needsReorder: needsReorderItems
    };

    // 6. Category Distribution: group by parent category name as requested, output exact keys required by frontend StockDistributionChart
    const parentCategoryQuantities = {};
    const parentCategoryProductCounts = {};
    products.forEach(p => {
      const catName = p.parentCategoryName || 'Uncategorized';
      parentCategoryQuantities[catName] = (parentCategoryQuantities[catName] || 0) + p.quantityOnHand;
      parentCategoryProductCounts[catName] = (parentCategoryProductCounts[catName] || 0) + 1;
    });

    const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6B7280'];
    const categoryDistribution = Object.keys(parentCategoryQuantities).map((name, i) => {
      const qty = parentCategoryQuantities[name];
      const percentage = totalQuantity > 0 ? parseFloat(((qty / totalQuantity) * 100).toFixed(1)) : 0;
      return {
        categoryName: name,
        percentage,
        totalQuantity: qty,
        productCount: parentCategoryProductCounts[name],
        color: colors[i % colors.length]
      };
    }).sort((a, b) => b.totalQuantity - a.totalQuantity);

    // 7. Stock Movement (past 7 days check)
    const now = new Date();
    const last7Days = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(now);
      d.setDate(now.getDate() - i);
      return formatDateKey(d);
    }).reverse();

    const startDate = new Date();
    startDate.setDate(now.getDate() - 7);

    const [recentOrders, recentPOs] = await Promise.all([
      this.orderClient.getOrdersWithDetails(token, {
        startDate: startDate.toISOString(),
        status: 'delivered',
        paymentStatus: 'paid'
      }),
      this.supplierClient.getPurchaseOrdersWithDetails(token, {
        startDate: startDate.toISOString(),
        status: 'received'
      })
    ]);

    const soldByDay = {};
    recentOrders.forEach(o => {
      const dateKey = formatDateKey(new Date(o.orderDate || o.order_date));
      const qty = (o.details || []).reduce((sum, d) => sum + (d.quantity || 0), 0);
      soldByDay[dateKey] = (soldByDay[dateKey] || 0) + qty;
    });

    const receivedByDay = {};
    recentPOs.forEach(po => {
      const dateKey = formatDateKey(new Date(po.orderDate || po.order_date));
      const qty = (po.details || []).reduce((sum, d) => sum + (d.quantity || 0), 0);
      receivedByDay[dateKey] = (receivedByDay[dateKey] || 0) + qty;
    });

    const stockMovement = last7Days.map(date => {
      const displayDate = new Date(date).toLocaleDateString('vi-VN', { month: 'numeric', day: 'numeric' });
      return {
        date: displayDate,
        received: receivedByDay[date] || 0,
        sold: soldByDay[date] || 0
      };
    });

    const result = {
      summary: { totalProducts, totalValue, lowStockCount, expiringSoonCount },
      stockStatus,
      categoryDistribution,
      stockMovement,
      products
    };

    await cache.set(cacheKey, result, CACHE_TTL.REPORT);
    return result;
  }

  /**
   * Employee Sales Report
   */
  async getEmployeeSalesReport(token, params) {
    const cacheKey = cache.buildKey('employee-sales', 'all', params);
    const cached = await cache.get(cacheKey);
    if (cached) return cached;

    const [orders, employees] = await Promise.all([
      this.orderClient.getOrders(token, {
        startDate: params.startDate,
        endDate: params.endDate,
        status: 'delivered',
        paymentStatus: 'paid'
      }),
      this.authClient.getEmployees(token)
    ]);

    const ordersList = orders || [];
    const employeesList = employees || [];

    const empMap = {};
    employeesList.forEach(e => {
      if (e && e.id) empMap[e.id] = e;
    });

    const empSalesMap = {};
    ordersList.forEach(order => {
      if (!order) return;
      const empId = order.createdBy || order.created_by || 'unknown';
      if (!empSalesMap[empId]) {
        const emp = empMap[empId] || {};
        empSalesMap[empId] = {
          employeeId: empId,
          employeeName: emp.name || emp.fullName || emp.full_name || `Employee #${empId}`,
          employeeCode: emp.employeeCode || emp.employee_code || `EMP-${empId}`,
          email: emp.email || 'N/A',
          phone: emp.phone || 'N/A',
          totalOrders: 0,
          totalRevenue: 0,
          totalQuantity: 0,
          orders: []
        };
      }
      empSalesMap[empId].totalOrders += 1;
      const orderTotal = parseFloat(order.total || order.total_amount || 0) || 0;
      empSalesMap[empId].totalRevenue += orderTotal;
      empSalesMap[empId].totalQuantity += parseInt(order.item_count || order.itemCount || 1) || 1;
      empSalesMap[empId].orders.push({
        orderId: order.id,
        orderNumber: order.order_number || order.orderNumber || `ORD-${order.id}`,
        customer: order.customer_name || order.customerName || 'Walk-in',
        phone: order.customer_phone || order.customerPhone || 'N/A',
        itemCount: parseInt(order.item_count || order.itemCount || 1) || 1,
        total: orderTotal,
        orderDate: order.order_date || order.orderDate || order.created_at
      });
    });

    const employeeList = Object.values(empSalesMap).sort((a, b) => b.totalRevenue - a.totalRevenue);
    const totalRevenue = employeeList.reduce((sum, e) => sum + e.totalRevenue, 0);
    const totalOrders = employeeList.reduce((sum, e) => sum + e.totalOrders, 0);

    // Add computed fields frontend expects
    employeeList.forEach((emp, idx) => {
      emp.rank = idx + 1;
      emp.averageOrderValue = emp.totalOrders > 0 ? emp.totalRevenue / emp.totalOrders : 0;
      emp.revenuePercentage = totalRevenue > 0 ? parseFloat(((emp.totalRevenue / totalRevenue) * 100).toFixed(1)) : 0;
    });

    const result = {
      summary: {
        totalEmployees: employeeList.length,
        totalRevenue,
        totalOrders
      },
      employees: employeeList
    };

    await cache.set(cacheKey, result, CACHE_TTL.REPORT);
    return result;
  }

  /**
   * Customer Sales Report
   * Data shape must match CustomerSalesList.jsx expectations
   */
  async getCustomerSalesReport(token, params) {
    const cacheKey = cache.buildKey('customer-sales', 'all', params);
    const cached = await cache.get(cacheKey);
    if (cached) return cached;

    const [orders, customers, employees] = await Promise.all([
      this.orderClient.getOrders(token, {
        startDate: params.startDate,
        endDate: params.endDate,
        status: 'delivered',
        paymentStatus: 'paid'
      }),
      this.authClient.getCustomers(token),
      this.authClient.getEmployees(token)
    ]);

    const ordersList = orders || [];
    const customersList = customers || [];
    const employeesList = employees || [];

    const custMap = {};
    customersList.forEach(c => {
      if (c && c.id) custMap[c.id] = c;
    });

    const empMap = {};
    employeesList.forEach(e => {
      if (e && e.id) empMap[e.id] = e;
    });

    const custSalesMap = {};
    ordersList.forEach(order => {
      if (!order) return;
      const custId = order.customerId || order.customer_id || 'GUEST';
      if (!custSalesMap[custId]) {
        const cust = custMap[custId] || {};
        custSalesMap[custId] = {
          customerId: custId,
          customerName: cust.name || cust.fullName || cust.full_name || (custId === 'GUEST' ? 'Guest Customers' : `Customer #${custId}`),
          customerCode: cust.customerCode || cust.customer_code || (custId === 'GUEST' ? 'GUEST' : `CUST-${custId}`),
          customerPhone: cust.phone || cust.phoneNumber || 'N/A',
          customerType: cust.type || cust.customerType || 'retail',
          email: cust.email || 'N/A',
          totalOrders: 0,
          totalRevenue: 0,
          totalQuantity: 0,
          orders: []
        };
      }
      custSalesMap[custId].totalOrders += 1;
      const orderTotal = parseFloat(order.total || order.total_amount || 0) || 0;
      custSalesMap[custId].totalRevenue += orderTotal;
      custSalesMap[custId].totalQuantity += parseInt(order.item_count || order.itemCount || 1) || 1;

      const empId = order.createdBy || order.created_by;
      const emp = empMap[empId] || {};
      custSalesMap[custId].orders.push({
        orderId: order.id,
        orderNumber: order.order_number || order.orderNumber || `ORD-${order.id}`,
        customerName: order.customer_name || order.customerName || 'Walk-in',
        customerPhone: order.customer_phone || order.customerPhone || 'N/A',
        employee: emp.name || emp.fullName || `Employee #${empId || 'N/A'}`,
        itemCount: parseInt(order.item_count || order.itemCount || 1) || 1,
        total: orderTotal,
        orderDate: order.order_date || order.orderDate || order.created_at
      });
    });

    const customerList = Object.values(custSalesMap).sort((a, b) => b.totalRevenue - a.totalRevenue);
    const totalRevenue = customerList.reduce((sum, c) => sum + c.totalRevenue, 0);
    const totalOrders = customerList.reduce((sum, c) => sum + c.totalOrders, 0);

    // Add computed fields frontend expects
    customerList.forEach((cust, idx) => {
      cust.rank = idx + 1;
      cust.averageOrderValue = cust.totalOrders > 0 ? cust.totalRevenue / cust.totalOrders : 0;
      cust.revenuePercentage = totalRevenue > 0 ? parseFloat(((cust.totalRevenue / totalRevenue) * 100).toFixed(1)) : 0;
    });

    const result = {
      summary: {
        totalCustomers: customerList.length,
        totalRevenue,
        totalOrders
      },
      customers: customerList
    };

    await cache.set(cacheKey, result, CACHE_TTL.REPORT);
    return result;
  }

  // ================== Private Helpers ==================

  _getRootCategory(catId, categoryMap) {
    if (!catId || !categoryMap[catId]) return { id: null, name: 'Uncategorized' };
    let current = categoryMap[catId];
    let depth = 0;
    while (current && (current.parentId || current.parent_id) && depth < 10) {
      const pid = current.parentId || current.parent_id;
      if (!categoryMap[pid]) break;
      current = categoryMap[pid];
      depth++;
    }
    return current;
  }

  _buildTopCategoriesDerived(productSales, productsMap, catMap) {
    const parentCategorySums = {};
    productSales.forEach(item => {
      const p = productsMap[item.productId] || {};
      const catId = p.category_id || p.categoryId;
      const rootCat = this._getRootCategory(catId, catMap);
      const parentName = rootCat.name || 'Uncategorized';
      const qty = parseInt(item.totalQuantity || item.total_quantity || 0) || 0;
      parentCategorySums[parentName] = (parentCategorySums[parentName] || 0) + qty;
    });

    const categoryColors = ['#e6816f', '#3b82f6', '#fbbf24', '#a855f7', '#10b981'];
    const sorted = Object.entries(parentCategorySums)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5);

    const total = sorted.reduce((sum, [, qty]) => sum + qty, 0);

    return sorted.map(([name, qty], index) => ({
      name,
      value: total > 0 ? Math.round((qty / total) * 100) : 0,
      color: categoryColors[index] || '#6b7280'
    }));
  }

  _buildOrderTrend(currentOrders, previousOrders, period, startDate, endDate, prevStartDate, prevEndDate) {
    const currentByDate = {};
    currentOrders.forEach(order => {
      const dateVal = order.orderDate || order.order_date || order.created_at || order.createdAt;
      const dateKey = formatDateKey(new Date(dateVal));
      currentByDate[dateKey] = (currentByDate[dateKey] || 0) + parseFloat(order.total || order.total_amount || 0);
    });

    const previousByDate = {};
    previousOrders.forEach(order => {
      const dateVal = order.orderDate || order.order_date || order.created_at || order.createdAt;
      const dateKey = formatDateKey(new Date(dateVal));
      previousByDate[dateKey] = (previousByDate[dateKey] || 0) + parseFloat(order.total || order.total_amount || 0);
    });

    const trend = { labels: [], current: [], previous: [] };

    if (period === 'week') {
      const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      let d = new Date(startDate);
      while (d <= endDate) {
        const dateKey = formatDateKey(d);
        trend.labels.push(dayNames[d.getDay()]);
        trend.current.push(currentByDate[dateKey] || 0);
        d.setDate(d.getDate() + 1);
      }
      let pd = new Date(prevStartDate);
      while (pd <= prevEndDate) {
        trend.previous.push(previousByDate[formatDateKey(pd)] || 0);
        pd.setDate(pd.getDate() + 1);
      }

    } else if (period === 'month') {
      const totalDays = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1;
      const interval = Math.max(Math.floor(totalDays / 8), 1);
      let d = new Date(startDate);
      let dayCount = 0;
      while (d <= endDate) {
        const dateKey = formatDateKey(d);
        if (dayCount % interval === 0) {
          const label = `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
          trend.labels.push(label);
          trend.current.push(currentByDate[dateKey] || 0);
        }
        d.setDate(d.getDate() + 1);
        dayCount++;
      }
      let pd = new Date(prevStartDate);
      let prevDayCount = 0;
      while (pd <= prevEndDate) {
        if (prevDayCount % interval === 0) {
          trend.previous.push(previousByDate[formatDateKey(pd)] || 0);
        }
        pd.setDate(pd.getDate() + 1);
        prevDayCount++;
      }

    } else if (period === 'year') {
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const currentByMonth = Array(12).fill(0);
      const previousByMonth = Array(12).fill(0);

      currentOrders.forEach(o => {
        const dateVal = o.orderDate || o.order_date || o.created_at || o.createdAt;
        const month = new Date(dateVal).getMonth();
        currentByMonth[month] += parseFloat(o.total || o.total_amount || 0);
      });
      previousOrders.forEach(o => {
        const dateVal = o.orderDate || o.order_date || o.created_at || o.createdAt;
        const month = new Date(dateVal).getMonth();
        previousByMonth[month] += parseFloat(o.total || o.total_amount || 0);
      });

      trend.labels = monthNames;
      trend.current = currentByMonth;
      trend.previous = previousByMonth;
    }

    return trend;
  }

  _buildTopCategories(orders) {
    // Legacy fallback, keep signature to prevent imports issues
    const categoryMap = {};
    orders.forEach(order => {
      const category = order.category_name || 'General';
      categoryMap[category] = (categoryMap[category] || 0) + 1;
    });

    const categoryColors = ['#e6816f', '#3b82f6', '#fbbf24', '#a855f7', '#10b981'];
    const sorted = Object.entries(categoryMap)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5);

    const total = sorted.reduce((sum, [, count]) => sum + count, 0);

    return sorted.map(([name, count], index) => ({
      name,
      value: total > 0 ? Math.round((count / total) * 100) : 0,
      color: categoryColors[index] || '#6b7280'
    }));
  }
}

module.exports = StatisticsService;
