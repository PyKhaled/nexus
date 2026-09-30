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

describe("GET /api/health", () => {
  it("returns 200 and ok: true when x-tenant header is present", async () => {
    const res = await request(app)
      .get("/api/health")
      .set("x-tenant", "tenant-1")
    expect(res.status).toBe(200)
    expect(res.body).toEqual({ ok: true })
  })

  it("returns 400 when x-tenant header is missing", async () => {
    const res = await request(app).get("/api/health")
    expect(res.status).toBe(400)
    expect(res.body).toMatchObject({
      error: "BadRequest",
      message: "Missing x-tenant header"
    })
  })
})
