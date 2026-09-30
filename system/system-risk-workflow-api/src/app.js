const express = require("express")
const helmet = require("helmet")
const cors = require("cors")

const requestId = require("./middleware/request-id.middleware")
const tenant = require("./middleware/tenant.middleware")
const errorHandler = require("./middleware/error.middleware")

const authRoutes = require("./modules/auth/auth.routes")
const riskRoutes = require("./modules/risks/risk.routes")

const app = express()

app.use(helmet())
app.use(cors())
app.use(express.json())

app.use(requestId)
app.use("/api", tenant)

app.get("/api/health", (req, res) => {
  res.json({ ok: true })
})

app.use("/api/auth", authRoutes)
app.use("/api/risks", riskRoutes)

app.use((req, res) => {
  res.status(404).json({
    error: "NotFound",
    message: "Route not found",
    request_id: req.requestId
  })
})

app.use(errorHandler)

module.exports = app
