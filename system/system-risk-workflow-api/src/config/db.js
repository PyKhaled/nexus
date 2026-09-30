const mongoose = require("mongoose")
const env = require("./env")

async function connectDB() {
  try {
    await mongoose.connect(env.MONGO_URI)
    console.log("MongoDB connected")
  } catch (err) {
    console.error("MongoDB connection failed", err)
    process.exit(1)
  }
}

module.exports = connectDB
