const bcrypt = require("bcrypt")
const User = require("../users/user.model")
const { generateToken } = require("../../utils/jwt")
const { UnauthorizedError } = require("../../utils/errors")

async function login(email, password) {
  const user = await User.findOne({ email })

  if (!user) {
    throw new UnauthorizedError("Invalid credentials")
  }

  const match = await bcrypt.compare(password, user.password_hash)

  if (!match) {
    throw new UnauthorizedError("Invalid credentials")
  }

  const token = generateToken({
    id: user._id,
    role: user.role,
    email: user.email
  })

  return { token }
}

module.exports = {
  login
}