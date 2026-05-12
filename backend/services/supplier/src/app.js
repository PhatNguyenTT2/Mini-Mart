const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const { errorHandler } = require('../../../shared/common/errors');
const healthRoutes = require('./routes/health.routes');

/**
 * Create Express app with dependency injection.
 * @param {object} deps - { supplierService, poService }
 */
function createApp({ supplierService, poService }) {
  const app = express();

  app.use(helmet());
  const allowedOrigins = (process.env.CORS_ORIGINS || 'http://localhost:5173').split(',').map(o => o.trim());
  app.use(cors({ origin: allowedOrigins, credentials: true }));
  app.use(express.json());

  // Health
  app.use('/', healthRoutes);

  // API routes
  app.use('/api/suppliers', require('./routes/supplier.routes')(supplierService));
  app.use('/api/purchase-orders', require('./routes/purchase-order.routes')(poService));

  // Error handler (must be last)
  app.use(errorHandler);

  return app;
}

module.exports = createApp;
