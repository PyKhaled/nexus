const mongoose = require("mongoose")

const userSchema = new mongoose.Schema(
  {
    email: {
      type: String,
      required: true,
      unique: true
    },
    password_hash: {
      type: String,
      required: true
    },
    role: {
      type: String,
      enum: ["user", "compliance"],
      default: "user"
    }
  },
  { timestamps: true }
)

module.exports = mongoose.model("User", userSchema)
