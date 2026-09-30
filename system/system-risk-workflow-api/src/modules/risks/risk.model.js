const mongoose = require("mongoose")
const tenantPlugin = require("../../plugins/tenant.plugin")

const riskSchema = new mongoose.Schema(
  {
    title: {
      type: String,
      required: true
    },

    description: {
      type: String
    },

    status: {
      type: String,
      enum: [
        "draft",
        "submitted",
        "in_review",
        "changes_requested",
        "approved",
        "rejected",
        "archived"
      ],
      default: "draft"
    },

    assignee_id: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User"
    },

    created_by: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "User"
    }
  },
  { timestamps: true }
)

riskSchema.plugin(tenantPlugin)

module.exports = mongoose.model("Risk", riskSchema)