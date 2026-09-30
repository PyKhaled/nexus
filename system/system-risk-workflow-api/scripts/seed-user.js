/**
 * One-time script to create a user. Run after MongoDB is up and .env is set.
 *
 * Usage:
 *   node scripts/seed-user.js <email> <password> [role]
 *   role: user | compliance (default: user)
 *
 * Example:
 *   node scripts/seed-user.js admin@example.com secret123 compliance
 */
require("dotenv").config()
const mongoose = require("mongoose")
const bcrypt = require("bcrypt")
const User = require("../src/modules/users/user.model")
const env = require("../src/config/env")

async function main() {
  const [email, password, role = "user"] = process.argv.slice(2)

  if (!email || !password) {
    console.error("Usage: node scripts/seed-user.js <email> <password> [role]")
    process.exit(1)
  }

  if (!env.MONGO_URI) {
    console.error("MONGO_URI is not set in .env")
    process.exit(1)
  }

  await mongoose.connect(env.MONGO_URI)
  const hash = await bcrypt.hash(password, 10)
  await User.create({ email, password_hash: hash, role })
  console.log("User created:", email, "role:", role)
  await mongoose.disconnect()
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
