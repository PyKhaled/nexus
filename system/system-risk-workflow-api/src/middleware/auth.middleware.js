const jwt = require("jsonwebtoken")
const env = require("../config/env")

module.exports = (req, res, next) => {
  const token = req.headers.authorization?.split(" ")[1]

  if (!token) return res.status(401).json({ error: "Unauthorized" })

  try {
    const decoded = jwt.verify(token, env.JWT_SECRET)
    req.user = decoded
    next()
  } catch {
    res.status(401).json({ error: "Unauthorized" })
  }
}