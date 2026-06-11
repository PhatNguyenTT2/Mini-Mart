const express = require('express');
const { verifyToken } = require('../../../../shared/auth-middleware');

function createBatchRouter(batchRepo) {
  const router = express.Router();

  function sanitizePromotion(body) {
    if (!body) return;

    // Map frontend 'discount' or 'buy1get1' to 'manual'
    if (body.promotion_applied === 'discount' || body.promotion_applied === 'buy1get1') {
      body.promotion_applied = 'manual';
    }
    if (body.promotionApplied === 'discount' || body.promotionApplied === 'buy1get1') {
      body.promotionApplied = 'manual';
    }

    // Map legacy 'auto_fresh' to 'perishable'
    if (body.promotion_applied === 'auto_fresh') {
      body.promotion_applied = 'perishable';
    }
    if (body.promotionApplied === 'auto_fresh') {
      body.promotionApplied = 'perishable';
    }

    // Force 'none' if discount rate is 0 or null
    const pct = body.discount_percentage !== undefined ? body.discount_percentage : body.discountPercentage;
    if (pct === 0 || pct === '0' || pct === null) {
      body.promotion_applied = 'none';
      body.promotionApplied = 'none';
    }
  }

  // Create a new product batch
  router.post('/', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      sanitizePromotion(req.body);
      const { product_id, cost_price, unit_price, quantity, mfg_date, expiry_date, notes, promotion_applied, discount_percentage } = req.body;

      if (!product_id || !quantity) {
        return res.status(400).json({
          success: false,
          error: 'product_id and quantity are required'
        });
      }

      const batch = await batchRepo.create(storeId, {
        product_id,
        cost_price: cost_price || 0,
        unit_price: unit_price || cost_price || 0,
        quantity,
        mfg_date: mfg_date || null,
        expiry_date: expiry_date || null,
        notes: notes || null,
        promotion_applied: promotion_applied || 'none',
        discount_percentage: discount_percentage || 0
      });

      res.status(201).json({
        success: true,
        data: batch
      });
    } catch (error) {
      next(error);
    }
  });

  // Get batches by storeId + optional filters
  router.get('/', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      const productId = req.query.productId || req.query.product;
      const filters = {
        productId: productId ? parseInt(productId) : undefined,
        status: req.query.status
      };

      const batches = await batchRepo.findAll(storeId, filters);
      res.json({
        success: true,
        data: batches
      });
    } catch (error) {
      next(error);
    }
  });

  // Bulk update all batches of a product
  router.put('/bulk-update', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      sanitizePromotion(req.body);
      const { productId, discount_percentage, promotion_applied } = req.body;
      if (!productId) {
        return res.status(400).json({ success: false, error: 'productId is required' });
      }
      const result = await batchRepo.bulkUpdateByProduct(storeId, productId, {
        discount_percentage,
        promotion_applied
      });
      res.json({ success: true, data: result });
    } catch (error) {
      next(error);
    }
  });

  // Update a product batch
  router.put('/:id', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      const batchId = parseInt(req.params.id);
      sanitizePromotion(req.body);
      const updated = await batchRepo.update(storeId, batchId, req.body);
      if (!updated) {
        return res.status(404).json({ success: false, error: 'Batch not found' });
      }
      res.json({ success: true, data: updated });
    } catch (error) {
      next(error);
    }
  });

  // Get single batch by ID (includes serverTime for expiry validation)
  router.get('/:id', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      const batchId = parseInt(req.params.id);

      const batch = await batchRepo.findById(storeId, batchId);
      if (!batch) {
        return res.status(404).json({ success: false, error: 'Batch not found' });
      }

      res.json({
        success: true,
        data: { ...batch, serverTime: new Date().toISOString() }
      });
    } catch (error) {
      next(error);
    }
  });

  // Saga compensation: delete orphaned batch (CASCADE cleans inventory_item + movement)
  router.delete('/:id', verifyToken, async (req, res, next) => {
    try {
      const storeId = req.user ? req.user.storeId : 1;
      const batchId = parseInt(req.params.id);

      const deleted = await batchRepo.deleteById(storeId, batchId);
      if (!deleted) {
        return res.status(404).json({ success: false, error: 'Batch not found' });
      }

      res.json({ success: true, data: deleted });
    } catch (error) {
      next(error);
    }
  });

  return router;
}

module.exports = createBatchRouter;
