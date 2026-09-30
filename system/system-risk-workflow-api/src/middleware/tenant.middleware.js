module.exports = (req, res, next) => {
    const tenant = req.headers["x-tenant"]

    if (!tenant) {
      return res.status(400).json({
        error: "BadRequest",
        message: "Missing x-tenant header",
        request_id: req.requestId
      })
    }

    req.tenantId = tenant
    next()
  }