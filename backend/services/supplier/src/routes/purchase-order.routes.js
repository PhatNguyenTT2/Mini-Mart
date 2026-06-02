const express = require('express');
const { verifyToken } = require('../../../../shared/auth-middleware');

function createPurchaseOrderRouter(poService) {
  const router = express.Router();

  // List POs by storeId + filters
  router.get('/', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      const filters = {
        supplierId: req.query.supplierId,
        status: req.query.status,
        paymentStatus: req.query.paymentStatus,
        startDate: req.query.startDate,
        endDate: req.query.endDate
      };

      const purchaseOrders = await poService.getStorePurchaseOrders(storeId, filters);

      res.json({
        success: true,
        data: purchaseOrders
      });
    } catch (error) {
      next(error);
    }
  });

  // GET /api/purchase-orders/stats/product-costs — Aggregated product costs (for statistics-service)
  router.get('/stats/product-costs', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      const { startDate, endDate } = req.query;
      if (!startDate || !endDate) {
        return res.status(400).json({ status: 'error', message: 'startDate and endDate required' });
      }
      const data = await poService.getProductCosts(storeId, { startDate, endDate });
      res.json({
        success: true,
        data: {
          productCosts: data.map(r => ({
            productId: r.product_id,
            productName: r.product_name,
            totalQuantity: parseInt(r.total_quantity) || 0,
            totalCost: parseFloat(r.total_cost) || 0,
            poCount: parseInt(r.po_count) || 0
          }))
        }
      });
    } catch (err) {
      next(err);
    }
  });

  // Get PO by ID
  router.get('/:id', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      const po = await poService.getPurchaseOrderById(storeId, parseInt(req.params.id));

      res.json({
        success: true,
        data: po
      });
    } catch (error) {
      next(error);
    }
  });

  // Create draft PO
  router.post('/', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      const userId = req.user ? req.user.id : 1;

      const po = await poService.createDraftPO(storeId, req.body, userId);

      res.status(201).json({
        success: true,
        data: po
      });
    } catch (error) {
      next(error);
    }
  });

  // Update draft PO
  router.put('/:id', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      const po = await poService.updateDraftPO(storeId, parseInt(req.params.id), req.body);

      res.json({
        success: true,
        data: po
      });
    } catch (error) {
      next(error);
    }
  });

  // Delete PO (draft, cancelled, received)
  router.delete('/:id', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      await poService.deletePurchaseOrder(storeId, parseInt(req.params.id));

      res.json({
        success: true,
        data: { deleted: true }
      });
    } catch (error) {
      next(error);
    }
  });

  // Receive PO — create batches, stock in, update status (all in one)
  router.post('/:id/receive', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      const userId = req.user ? req.user.id : 1;
      const { items } = req.body;

      // Pass auth token for internal service-to-service calls
      const authToken = req.headers.authorization?.replace('Bearer ', '');

      const po = await poService.receivePO(
        storeId,
        parseInt(req.params.id),
        items,
        userId,
        authToken
      );

      res.json({
        success: true,
        data: po
      });
    } catch (error) {
      next(error);
    }
  });

  // Update status (approve, receive, cancel)
  router.patch('/:id/status', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      const { status, paymentStatus, payment_status } = req.body;

      const updated = await poService.updateStatus(
        storeId,
        parseInt(req.params.id),
        status,
        paymentStatus || payment_status
      );

      res.json({
        success: true,
        data: updated
      });
    } catch (error) {
      next(error);
    }
  });

  return router;
}

module.exports = createPurchaseOrderRouter;
