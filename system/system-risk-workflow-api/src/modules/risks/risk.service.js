const Risk = require("./risk.model")
const { validateTransition } = require("./risk.workflow")
const {
  ConflictError,
  NotFoundError,
  BadRequestError
} = require("../../utils/errors")

/**
 * Create a new risk
 */
async function createRisk(data, tenantId, userId) {
  const risk = await Risk.create({
    title: data.title,
    description: data.description,
    tenant_id: tenantId,
    created_by: userId,
    status: "draft"
  })

  return risk
}

/**
 * List risks for tenant
 */
async function listRisks(tenantId) {
  return Risk.find({}, null, { tenantId })
}

/**
 * Get risk by id with tenant isolation
 */
async function getRiskById(id, tenantId) {
  const risk = await Risk.findOne({ _id: id, tenant_id: tenantId })

  if (!risk) {
    throw new NotFoundError("Risk not found")
  }

  return risk
}

/**
 * Generic workflow transition
 */
async function transitionRisk(id, toStatus, tenantId, options = {}) {
  const risk = await getRiskById(id, tenantId)

  if (!validateTransition(risk.status, toStatus)) {
    throw new ConflictError(
      `Invalid transition from ${risk.status} to ${toStatus}`
    )
  }

  risk.status = toStatus

  if (options.assignee_id) {
    risk.assignee_id = options.assignee_id
  }

  await risk.save()

  return risk
}

/**
 * Submit risk
 */
async function submitRisk(id, tenantId) {
  return transitionRisk(id, "submitted", tenantId)
}

/**
 * Resubmit risk after changes requested
 */
async function resubmitRisk(id, tenantId) {
  return transitionRisk(id, "submitted", tenantId)
}

/**
 * Assign risk to compliance reviewer
 */
async function assignRisk(id, tenantId, complianceUserId) {
  return transitionRisk(id, "in_review", tenantId, {
    assignee_id: complianceUserId
  })
}

/**
 * Request changes from submitter
 */
async function requestChanges(id, tenantId) {
  return transitionRisk(id, "changes_requested", tenantId)
}

/**
 * Approve or reject risk
 */
async function decisionRisk(id, tenantId, action) {
  if (!["approve", "reject"].includes(action)) {
    throw new BadRequestError("Invalid decision action")
  }

  const status = action === "approve" ? "approved" : "rejected"

  return transitionRisk(id, status, tenantId)
}

/**
 * Archive approved or rejected risk
 */
async function archiveRisk(id, tenantId) {
  return transitionRisk(id, "archived", tenantId)
}

module.exports = {
  createRisk,
  listRisks,
  getRiskById,
  submitRisk,
  resubmitRisk,
  assignRisk,
  requestChanges,
  decisionRisk,
  archiveRisk
}