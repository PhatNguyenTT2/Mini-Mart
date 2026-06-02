const express = require('express');
const { verifyToken } = require('../../../../shared/auth-middleware');

function createOrderRouter(orderService) {
  const router = express.Router();

  // Get orders list (Multi-Tenant by storeId from JWT)
  router.get('/', verifyToken, async (req, res, next) => {
    try {
      let storeId = req.user?.storeId;
      if (!storeId && req.headers['x-store-id']) {
        storeId = parseInt(req.headers['x-store-id'], 10);
      }
      storeId = storeId || 1;

      const filters = {
        status: req.query.status,
        paymentStatus: req.query.paymentStatus,
        deliveryType: req.query.deliveryType,
        customerId: req.query.customer,
        createdBy: req.query.createdBy,
        startDate: req.query.startDate,
        endDate: req.query.endDate
      };

      // Security: Enforce customer isolation (customerId = customer table PK from JWT)
      if (req.user?.roleName === 'Customer') {
        filters.customerId = req.user.customerId || req.user.id;
      }
      const orders = await orderService.getStoreOrders(storeId, filters);

      res.json({
        status: 'success',
        data: { orders }
      });
    } catch (error) {
      next(error);
    }
  });

  // Bulk delete drafts — MUST be before /:id route
  router.delete('/bulk/draft', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user?.storeId || 1;
      const result = await orderService.deleteDraftOrders(storeId);

      res.json({
        status: 'success',
        message: `Deleted ${result.deletedCount} draft order(s)`,
        data: result
      });
    } catch (error) {
      next(error);
    }
  });

  // GET /api/orders/stats/product-sales — Aggregated product sales (for statistics-service)
  router.get('/stats/product-sales', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user?.storeId || 1;
      const { startDate, endDate } = req.query;
      if (!startDate || !endDate) {
        return res.status(400).json({ status: 'error', message: 'startDate and endDate required' });
      }
      const data = await orderService.getProductSales(storeId, { startDate, endDate });
      res.json({
        status: 'success',
        data: {
          productSales: data.map(r => ({
            productId: r.product_id,
            productName: r.product_name,
            totalQuantity: parseInt(r.total_quantity) || 0,
            totalRevenue: parseFloat(r.total_revenue) || 0,
            orderCount: parseInt(r.order_count) || 0
          }))
        }
      });
    } catch (err) {
      next(err);
    }
  });

  // Get order detail
  router.get('/:id', verifyToken, async (req, res, next) => {
    try {
      let storeId = req.user?.storeId;
      if (!storeId && req.headers['x-store-id']) {
        storeId = parseInt(req.headers['x-store-id'], 10);
      }
      storeId = storeId || 1;
      const order = await orderService.getOrderById(storeId, req.params.id);

      // Security: Enforce customer isolation (customerId = customer table PK from JWT)
      const customerPk = req.user?.customerId || req.user?.id;
      if (req.user?.roleName === 'Customer' && String(order.customerId) !== String(customerPk)) {
        return res.status(403).json({
          status: 'error',
          message: 'You do not have permission to view this order'
        });
      }

      res.json({
        status: 'success',
        data: { order }
      });
    } catch (error) {
      next(error);
    }
  });

  // Create draft order (POS flow)
  router.post('/', verifyToken, async (req, res, next) => {
    try {
      let storeId = req.user?.storeId;
      if (!storeId && req.headers['x-store-id']) {
        storeId = parseInt(req.headers['x-store-id'], 10);
      }
      storeId = storeId || 1;

      // Fix: If the request is from a Customer, created_by should be -1 (since no employee created it)
      // We use -1 to avoid NOT NULL constraint errors in the database schema.
      const userId = req.user?.roleName === 'Customer' ? -1 : (req.user?.id || 1);

      const jwtToken = req.headers.authorization?.replace('Bearer ', '');

      const order = await orderService.createDraftOrder(storeId, req.body, userId, jwtToken);

      res.status(201).json({
        status: 'success',
        message: 'Draft order created',
        data: { order }
      });
    } catch (error) {
      next(error);
    }
  });

  // NOTE: POST /online REMOVED — simplified flow uses POST / for all orders
  // All orders start as 'draft' regardless of delivery type

  // Update draft order items (delete old → FEFO re-allocate → insert new)
  router.put('/:id/items', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user?.storeId || 1;
      const userId = req.user?.id || 1;
      const jwtToken = req.headers.authorization?.replace('Bearer ', '');
      const result = await orderService.updateDraftItems(
        storeId, req.params.id, req.body.items, userId, jwtToken
      );
      res.json({
        status: 'success',
        message: 'Draft order items updated',
        data: { order: result }
      });
    } catch (error) {
      next(error);
    }
  });

  // General update (address, shipping, discount, status, paymentStatus)
  router.put('/:id', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user?.storeId || 1;
      const updated = await orderService.updateOrder(storeId, req.params.id, req.body);

      res.json({
        status: 'success',
        data: { order: updated }
      });
    } catch (error) {
      next(error);
    }
  });

  // Status-only update (internal/webhook)
  router.patch('/:id/status', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user?.storeId || 1;
      const { status, payment_status } = req.body;

      const updated = await orderService.updateOrderStatus(storeId, req.params.id, status, payment_status);
      res.json({
        status: 'success',
        data: { order: updated }
      });
    } catch (error) {
      next(error);
    }
  });

  // Delete order
  router.delete('/:id', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user?.storeId || 1;
      const deleted = await orderService.deleteOrder(storeId, req.params.id);

      res.json({
        status: 'success',
        message: 'Order deleted',
        data: { order: deleted }
      });
    } catch (error) {
      next(error);
    }
  });

  // Refund order
  router.post('/:id/refund', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user?.storeId || 1;
      const result = await orderService.refundOrder(storeId, req.params.id, req.body);

      res.json(result);
    } catch (error) {
      next(error);
    }
  });

  return router;
}

module.exports = createOrderRouter;
