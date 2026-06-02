const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const logger = require('../../../shared/common/logger');
const createStatisticsRouter = require('./routes/statistics.routes');
const createHealthRouter = require('./routes/health.routes');

function createApp({ statisticsService }) {
  const app = express();

  const allowedOrigins = (process.env.CORS_ORIGINS || 'http://localhost:5173').split(',').map(o => o.trim());
  app.use(cors({ origin: allowedOrigins, credentials: true }));
  app.use(helmet());
  app.use(express.json());

  // Health & Readiness
  const healthRouter = createHealthRouter();
  app.use('/', healthRouter);

  // Memory usage logging middleware
  app.use('/api/statistics', (req, res, next) => {
    const memoryBefore = process.memoryUsage();
    const startHrTime = process.hrtime();

    res.on('finish', () => {
      const elapsedHrTime = process.hrtime(startHrTime);
      const elapsedTimeInMs = elapsedHrTime[0] * 1000 + elapsedHrTime[1] / 1e6;
      const memoryAfter = process.memoryUsage();
      const heapDiff = memoryAfter.heapUsed - memoryBefore.heapUsed;

      logger.info({
        path: req.baseUrl + req.path,
        method: req.method,
        elapsedTimeInMs: elapsedTimeInMs.toFixed(2),
        heapUsedBeforeMB: (memoryBefore.heapUsed / 1024 / 1024).toFixed(2),
        heapUsedAfterMB: (memoryAfter.heapUsed / 1024 / 1024).toFixed(2),
        heapDiffMB: (heapDiff / 1024 / 1024).toFixed(2)
      }, 'Memory footprint profile');
    });

    next();
  });

  // Statistics API
  const statisticsRouter = createStatisticsRouter(statisticsService);
  app.use('/api/statistics', statisticsRouter);

  // Global error handler
  app.use((err, req, res, next) => {
    const status = err.statusCode || 500;
    logger.error({ err: err.message, stack: err.stack, path: req.path, method: req.method }, 'Request error');
    res.status(status).json({
      success: false,
      error: err.message || 'Internal server error'
    });
  });

  return app;
}

module.exports = createApp;
