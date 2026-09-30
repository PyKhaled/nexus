const jwt = require("jsonwebtoken")
const env = require("../config/env")

function generateToken(payload) {
  return jwt.sign(payload, env.JWT_SECRET, {
    expiresIn: "1h"
  })
}

module.exports = {
  generateToken
}