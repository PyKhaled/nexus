const authService = require("./auth.service")
const { BadRequestError } = require("../../utils/errors")

async function login(req, res, next) {
  try {
    const { email, password } = req.body

    if (!email || !password) {
      throw new BadRequestError("Email and password are required")
    }

    const result = await authService.login(email, password)

    res.json(result)
  } catch (err) {
    next(err)
  }
}

async function me(req, res) {
  res.json({
    id: req.user.id,
    email: req.user.email,
    role: req.user.role
  })
}

module.exports = {
  login,
  me
}