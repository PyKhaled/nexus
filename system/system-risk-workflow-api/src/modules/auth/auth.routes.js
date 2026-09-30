const express = require("express")
const controller = require("./auth.controller")
const authMiddleware = require("../../middleware/auth.middleware")
const rateLimit = require("express-rate-limit")

const router = express.Router()

const loginLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 5,
  standardHeaders: true
})

router.post("/login", loginLimiter, controller.login)

router.get("/me", authMiddleware, controller.me)

module.exports = router