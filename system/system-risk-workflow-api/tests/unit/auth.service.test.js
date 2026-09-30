const { setupDb, teardownDb } = require("../helpers/db")
const { createUser } = require("../helpers/auth")
const authService = require("../../src/modules/auth/auth.service")
const User = require("../../src/modules/users/user.model")
const { UnauthorizedError } = require("../../src/utils/errors")
const jwt = require("jsonwebtoken")

describe("auth.service login", () => {
  let testUser

  beforeAll(async () => {
    await setupDb()
  })

  afterAll(async () => {
    await teardownDb()
  })

  beforeEach(async () => {
    testUser = await createUser(User, {
      email: "test@example.com",
      password: "password123",
      role: "user"
    })
  })

  afterEach(async () => {
    await User.deleteMany({})
  })

  it("returns token for valid email and password", async () => {
    const result = await authService.login("test@example.com", "password123")
    expect(result).toHaveProperty("token")
    expect(typeof result.token).toBe("string")
    const decoded = jwt.decode(result.token)
    expect(decoded).toMatchObject({
      id: testUser._id.toString(),
      email: "test@example.com",
      role: "user"
    })
  })

  it("throws UnauthorizedError for wrong password", async () => {
    await expect(
      authService.login("test@example.com", "wrongpassword")
    ).rejects.toThrow(UnauthorizedError)
    await expect(
      authService.login("test@example.com", "wrongpassword")
    ).rejects.toThrow("Invalid credentials")
  })

  it("throws UnauthorizedError for unknown email", async () => {
    await expect(
      authService.login("nonexistent@test.com", "any")
    ).rejects.toThrow(UnauthorizedError)
    await expect(
      authService.login("nonexistent@test.com", "any")
    ).rejects.toThrow("Invalid credentials")
  })
})
