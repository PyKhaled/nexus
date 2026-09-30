const express = require("express")
const controller = require("./risk.controller")
const auth = require("../../middleware/auth.middleware")
const role = require("../../middleware/role.middleware")

const router = express.Router()

router.post("/", auth, controller.create)
router.get("/", auth, controller.list)

router.post("/:id/submit", auth, controller.submit)
router.post("/:id/resubmit", auth, controller.resubmit)

router.post("/:id/assign", auth, role("compliance"), controller.assign)
router.post("/:id/request-changes", auth, role("compliance"), controller.requestChanges)

router.post("/:id/decision", auth, role("compliance"), controller.decision)
router.post("/:id/archive", auth, role("compliance"), controller.archive)

module.exports = router