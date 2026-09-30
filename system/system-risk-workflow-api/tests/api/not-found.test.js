const request = require("supertest")
const { setupDb, teardownDb } = require("../helpers/db")

let app

beforeAll(async () => {
  await setupDb()
  app = require("../../src/app")
})

afterAll(async () => {
  await teardownDb()
})

describe("404 for unknown route", () => {
  it("GET /api/unknown returns 404 with error, message, request_id", async () => {
    const res = await request(app)
      .get("/api/unknown")
      .set("x-tenant", "tenant-1")
    expect(res.status).toBe(404)
    expect(res.body).toMatchObject({
      error: "NotFound",
      message: "Route not found"
    })
    expect(res.body).toHaveProperty("request_id")
  })
})
