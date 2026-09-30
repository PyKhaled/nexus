class AppError extends Error {
    constructor(message, status) {
      super(message)
      this.status = status
    }
  }

  class BadRequestError extends AppError {
    constructor(message) {
      super(message, 400)
    }
  }

  class UnauthorizedError extends AppError {
    constructor(message) {
      super(message, 401)
    }
  }

  class ForbiddenError extends AppError {
    constructor(message) {
      super(message, 403)
    }
  }

  class NotFoundError extends AppError {
    constructor(message) {
      super(message, 404)
    }
  }

  class ConflictError extends AppError {
    constructor(message) {
      super(message, 409)
    }
  }

  module.exports = {
    AppError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ConflictError
  }