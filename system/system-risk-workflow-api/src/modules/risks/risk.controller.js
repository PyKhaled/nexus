const service = require("./risk.service")

async function create(req, res, next) {
  try {
    const risk = await service.createRisk(req.body, req.tenantId, req.user.id)

    res.status(201).json(risk)
  } catch (err) {
    next(err)
  }
}

async function list(req, res, next) {
  try {
    const risks = await service.listRisks(req.tenantId)
    res.json(risks)
  } catch (err) {
    next(err)
  }
}

async function submit(req, res, next) {
  try {
    const risk = await service.submitRisk(req.params.id, req.tenantId)
    res.json(risk)
  } catch (err) {
    next(err)
  }
}

async function resubmit(req, res, next) {
  try {
    const risk = await service.resubmitRisk(req.params.id, req.tenantId)
    res.json(risk)
  } catch (err) {
    next(err)
  }
}

async function assign(req, res, next) {
  try {
    const risk = await service.assignRisk(
      req.params.id,
      req.tenantId,
      req.user.id
    )
    res.json(risk)
  } catch (err) {
    next(err)
  }
}

async function requestChanges(req, res, next) {
  try {
    const risk = await service.requestChanges(req.params.id, req.tenantId)
    res.json(risk)
  } catch (err) {
    next(err)
  }
}

async function decision(req, res, next) {
  try {
    const { action } = req.body

    const risk = await service.decisionRisk(
      req.params.id,
      req.tenantId,
      action
    )

    res.json(risk)
  } catch (err) {
    next(err)
  }
}

async function archive(req, res, next) {
  try {
    const risk = await service.archiveRisk(req.params.id, req.tenantId)
    res.json(risk)
  } catch (err) {
    next(err)
  }
}

module.exports = {
  create,
  list,
  submit,
  resubmit,
  assign,
  requestChanges,
  decision,
  archive
}