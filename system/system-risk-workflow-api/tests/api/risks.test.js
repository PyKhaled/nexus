const request = require("supertest")
const mongoose = require("mongoose")
const { setupDb, teardownDb } = require("../helpers/db")
const { createUser, getToken } = require("../helpers/auth")
const User = require("../../src/modules/users/user.model")
const Risk = require("../../src/modules/risks/risk.model")

let app
let userToken
let complianceToken
let complianceUser

beforeAll(async () => {
  await setupDb()
  app = require("../../src/app")
  const user = await createUser(User, {
    email: "user@example.com",
    password: "pass",
    role: "user"
  })
  complianceUser = await createUser(User, {
    email: "compliance@example.com",
    password: "pass",
    role: "compliance"
  })
  userToken = getToken(user)
  complianceToken = getToken(complianceUser)
})

afterAll(async () => {
  await teardownDb()
})

afterEach(async () => {
  await Risk.deleteMany({})
})

const tenantHeader = { "x-tenant": "tenant-1" }
const authHeader = (token) => ({ Authorization: `Bearer ${token}` })

describe("Risks - tenant and auth required", () => {
  it("POST /api/risks without x-tenant returns 400", async () => {
    const res = await request(app)
      .post("/api/risks")
      .set(authHeader(userToken))
      .send({ title: "Risk" })
    expect(res.status).toBe(400)
    expect(res.body.message).toMatch(/x-tenant/)
  })

  it("GET /api/risks without x-tenant returns 400", async () => {
    const res = await request(app)
      .get("/api/risks")
      .set(authHeader(userToken))
    expect(res.status).toBe(400)
  })

  it("POST /api/risks without Authorization returns 401", async () => {
    const res = await request(app)
      .post("/api/risks")
      .set(tenantHeader)
      .send({ title: "Risk" })
    expect(res.status).toBe(401)
  })

  it("GET /api/risks without Authorization returns 401", async () => {
    const res = await request(app)
      .get("/api/risks")
      .set(tenantHeader)
    expect(res.status).toBe(401)
  })
})

describe("POST /api/risks create", () => {
  it("returns 201 with _id, title, status draft, tenant_id, created_by", async () => {
    const res = await request(app)
      .post("/api/risks")
      .set(tenantHeader)
      .set(authHeader(userToken))
      .send({ title: "New risk", description: "Optional" })
    expect(res.status).toBe(201)
    expect(res.body).toMatchObject({
      title: "New risk",
      description: "Optional",
      status: "draft",
      tenant_id: "tenant-1"
    })
    expect(res.body).toHaveProperty("_id")
    expect(res.body).toHaveProperty("created_by")
  })
})

describe("GET /api/risks list", () => {
  it("returns 200 and array of risks for tenant", async () => {
    await request(app)
      .post("/api/risks")
      .set(tenantHeader)
      .set(authHeader(userToken))
      .send({ title: "R1" })
    await request(app)
      .post("/api/risks")
      .set(tenantHeader)
      .set(authHeader(userToken))
      .send({ title: "R2" })
    const listRes = await request(app)
      .get("/api/risks")
      .set(tenantHeader)
      .set(authHeader(userToken))
    expect(listRes.status).toBe(200)
    expect(Array.isArray(listRes.body)).toBe(true)
    expect(listRes.body.length).toBe(2)
  })
})

describe("Risk workflow happy path", () => {
  it("create -> submit -> assign -> decision approve -> archive", async () => {
    const createRes = await request(app)
      .post("/api/risks")
      .set(tenantHeader)
      .set(authHeader(userToken))
      .send({ title: "Workflow risk" })
    expect(createRes.status).toBe(201)
    const riskId = createRes.body._id

    const submitRes = await request(app)
      .post(`/api/risks/${riskId}/submit`)
      .set(tenantHeader)
      .set(authHeader(userToken))
    expect(submitRes.status).toBe(200)
    expect(submitRes.body.status).toBe("submitted")

    const assignRes = await request(app)
      .post(`/api/risks/${riskId}/assign`)
      .set(tenantHeader)
      .set(authHeader(complianceToken))
    expect(assignRes.status).toBe(200)
    expect(assignRes.body.status).toBe("in_review")

    const decisionRes = await request(app)
      .post(`/api/risks/${riskId}/decision`)
      .set(tenantHeader)
      .set(authHeader(complianceToken))
      .send({ action: "approve" })
    expect(decisionRes.status).toBe(200)
    expect(decisionRes.body.status).toBe("approved")

    const archiveRes = await request(app)
      .post(`/api/risks/${riskId}/archive`)
      .set(tenantHeader)
      .set(authHeader(complianceToken))
    expect(archiveRes.status).toBe(200)
    expect(archiveRes.body.status).toBe("archived")
  })
})

describe("Invalid transition and not found", () => {
  it("POST .../archive when risk is draft returns 409", async () => {
    const createRes = await request(app)
      .post("/api/risks")
      .set(tenantHeader)
      .set(authHeader(userToken))
      .send({ title: "Draft risk" })
    const riskId = createRes.body._id
    const res = await request(app)
      .post(`/api/risks/${riskId}/archive`)
      .set(tenantHeader)
      .set(authHeader(complianceToken))
    expect(res.status).toBe(409)
    expect(res.body.message).toMatch(/Invalid transition/)
  })

  it("POST .../submit with non-existent id returns 404", async () => {
    const fakeId = new mongoose.Types.ObjectId()
    const res = await request(app)
      .post(`/api/risks/${fakeId}/submit`)
      .set(tenantHeader)
      .set(authHeader(userToken))
    expect(res.status).toBe(404)
    expect(res.body.message).toMatch(/not found/)
  })
})

describe("Compliance role", () => {
  it("assign returns 403 when token is user role", async () => {
    const createRes = await request(app)
      .post("/api/risks")
      .set(tenantHeader)
      .set(authHeader(userToken))
      .send({ title: "R" })
    await request(app)
      .post(`/api/risks/${createRes.body._id}/submit`)
      .set(tenantHeader)
      .set(authHeader(userToken))
    const res = await request(app)
      .post(`/api/risks/${createRes.body._id}/assign`)
      .set(tenantHeader)
      .set(authHeader(userToken))
    expect(res.status).toBe(403)
  })

  it("request-changes returns 403 when token is user role", async () => {
    const createRes = await request(app)
      .post("/api/risks")
      .set(tenantHeader)
      .set(authHeader(userToken))
      .send({ title: "R" })
    const res = await request(app)
      .post(`/api/risks/${createRes.body._id}/request-changes`)
      .set(tenantHeader)
      .set(authHeader(userToken))
    expect(res.status).toBe(403)
  })

  it("decision returns 403 when token is user role", async () => {
    const createRes = await request(app)
      .post("/api/risks")
      .set(tenantHeader)
      .set(authHeader(userToken))
      .send({ title: "R" })
    const res = await request(app)
      .post(`/api/risks/${createRes.body._id}/decision`)
      .set(tenantHeader)
      .set(authHeader(userToken))
      .send({ action: "approve" })
    expect(res.status).toBe(403)
  })

  it("archive returns 403 when token is user role", async () => {
    const createRes = await request(app)
      .post("/api/risks")
      .set(tenantHeader)
      .set(authHeader(userToken))
      .send({ title: "R" })
    const res = await request(app)
      .post(`/api/risks/${createRes.body._id}/archive`)
      .set(tenantHeader)
      .set(authHeader(userToken))
    expect(res.status).toBe(403)
  })
})
