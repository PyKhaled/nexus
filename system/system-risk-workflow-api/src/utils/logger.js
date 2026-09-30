function log(message, meta = {}) {
    console.log(
      JSON.stringify({
        message,
        ...meta,
        timestamp: new Date().toISOString()
      })
    )
  }

  module.exports = {
    log
  }