const { MongoMemoryServer } = require("mongodb-memory-server")
const mongoose = require("mongoose")

let mongoServer

async function setupDb() {
  if (mongoose.connection.readyState !== 0) {
    await mongoose.disconnect()
  }
  let uri

  // For test environment, always use an in-memory Mongo instance so tests
  // are isolated from any developer or CI MongoDB configuration.
  if (process.env.NODE_ENV === "test") {
    mongoServer = await MongoMemoryServer.create()
    uri = mongoServer.getUri()
    process.env.MONGO_URI = uri
  } else {
    uri = process.env.MONGO_URI
    if (!uri) {
      mongoServer = await MongoMemoryServer.create()
      uri = mongoServer.getUri()
      process.env.MONGO_URI = uri
    }
  }

  if (!process.env.JWT_SECRET) {
    process.env.JWT_SECRET = "test-jwt-secret"
  }
  await mongoose.connect(uri)
}

async function teardownDb() {
  if (mongoose.connection.readyState !== 0) {
    await mongoose.disconnect()
  }
  if (mongoServer) {
    await mongoServer.stop()
    mongoServer = null
  }
}

module.exports = { setupDb, teardownDb }
