module.exports = (err, req, res, _next) => {
  const status = err.status || 500
  const body = {
    error: err.name || "Error",
    message: err.message || "Internal server error",
    request_id: req.requestId
  }
  res.status(status).json(body)
}
