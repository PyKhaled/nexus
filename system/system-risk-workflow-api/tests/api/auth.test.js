const request = require("supertest")
const { setupDb, teardownDb } = require("../helpers/db")
const { createUser, getToken } = require("../helpers/auth")
const User = require("../../src/modules/users/user.model")

let app
let testUser

beforeAll(async () => {
  await setupDb()
  app = require("../../src/app")
  testUser = await createUser(User, {
    email: "auth@example.com",
    password: "secret123",
    role: "user"
  })
})

afterAll(async () => {
  await teardownDb()
})

const tenantHeader = { "x-tenant": "tenant-1" }

describe("POST /api/auth/login", () => {
  it("returns 200 and token for valid email and password", async () => {
    const res = await request(app)
      .post("/api/auth/login")
      .set(tenantHeader)
      .send({ email: "auth@example.com", password: "secret123" })
    expect(res.status).toBe(200)
    expect(res.body).toHaveProperty("token")
    expect(typeof res.body.token).toBe("string")
  })

  it("returns 400 when email is missing", async () => {
    const res = await request(app)
      .post("/api/auth/login")
      .set(tenantHeader)
      .send({ password: "secret123" })
    expect(res.status).toBe(400)
    expect(res.body).toMatchObject({
      message: "Email and password are required"
    })
  })

  it("returns 400 when password is missing", async () => {
    const res = await request(app)
      .post("/api/auth/login")
      .set(tenantHeader)
      .send({ email: "auth@example.com" })
    expect(res.status).toBe(400)
    expect(res.body).toMatchObject({
      message: "Email and password are required"
    })
  })

  it("returns 401 for wrong password", async () => {
    const res = await request(app)
      .post("/api/auth/login")
      .set(tenantHeader)
      .send({ email: "auth@example.com", password: "wrong" })
    expect(res.status).toBe(401)
  })

  it("returns 401 for unknown email", async () => {
    const res = await request(app)
      .post("/api/auth/login")
      .set(tenantHeader)
      .send({ email: "nobody@example.com", password: "any" })
    expect(res.status).toBe(401)
  })
})

describe("GET /api/auth/me", () => {
  it("returns 200 with id, email, role when token is valid", async () => {
    const token = getToken(testUser)
    const res = await request(app)
      .get("/api/auth/me")
      .set(tenantHeader)
      .set("Authorization", `Bearer ${token}`)
    expect(res.status).toBe(200)
    expect(res.body).toMatchObject({
      id: testUser._id.toString(),
      email: "auth@example.com",
      role: "user"
    })
  })

  it("returns 401 when Authorization header is missing", async () => {
    const res = await request(app)
      .get("/api/auth/me")
      .set(tenantHeader)
    expect(res.status).toBe(401)
  })

  it("returns 401 when token is invalid", async () => {
    const res = await request(app)
      .get("/api/auth/me")
      .set(tenantHeader)
      .set("Authorization", "Bearer invalid-token")
    expect(res.status).toBe(401)
  })
})
