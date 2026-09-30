const { randomUUID } = require("crypto")

module.exports = (req, res, next) => {
  req.requestId = randomUUID()
  next()
}