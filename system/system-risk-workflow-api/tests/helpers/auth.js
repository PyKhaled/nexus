const bcrypt = require("bcrypt")
const { generateToken } = require("../../src/utils/jwt")

async function createUser(User, { email, password, role = "user" }) {
  const password_hash = await bcrypt.hash(password, 10)
  return User.create({ email, password_hash, role })
}

function getToken(user) {
  return generateToken({
    id: user._id,
    email: user.email,
    role: user.role
  })
}

module.exports = { createUser, getToken }
