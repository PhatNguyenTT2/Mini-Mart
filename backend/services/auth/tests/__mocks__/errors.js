/**
 * Mock: shared/common/errors — uses REAL error classes so tests can assert status codes.
 */

class AppError extends Error {
  constructor(message, statusCode = 500, code = 'INTERNAL_ERROR') {
    super(message);
    this.statusCode = statusCode;
    this.code = code;
    this.isOperational = true;
  }
}

class NotFoundError extends AppError {
  constructor(resource = 'Resource') { super(`${resource} not found`, 404, 'NOT_FOUND'); }
}

class ValidationError extends AppError {
  constructor(message = 'Validation failed', details = null) {
    super(message, 400, 'VALIDATION_ERROR');
    this.details = details;
  }
}

class UnauthorizedError extends AppError {
  constructor(message = 'Unauthorized') { super(message, 401, 'UNAUTHORIZED'); }
}

class ForbiddenError extends AppError {
  constructor(message = 'Forbidden') { super(message, 403, 'FORBIDDEN'); }
}

class ConflictError extends AppError {
  constructor(message = 'Conflict') { super(message, 409, 'CONFLICT'); }
}

class PinInvalidError extends AppError {
  constructor(attemptsRemaining) {
    super('Invalid employee ID or PIN', 401, 'INVALID_PIN');
    this.attemptsRemaining = attemptsRemaining;
  }
}

class PinLockedError extends AppError {
  constructor(minutesLeft) {
    super(`Account locked for ${minutesLeft} minutes`, 423, 'PIN_LOCKED');
    this.minutesLeft = minutesLeft;
  }
}

function errorHandler(err, req, res, _next) {
  if (err.isOperational) {
    return res.status(err.statusCode).json({
      success: false,
      error: { message: err.message, code: err.code }
    });
  }
  res.status(500).json({
    success: false,
    error: { message: 'Internal server error', code: 'INTERNAL_ERROR' }
  });
}

module.exports = { AppError, NotFoundError, ValidationError, UnauthorizedError, ForbiddenError, ConflictError, PinInvalidError, PinLockedError, errorHandler };
