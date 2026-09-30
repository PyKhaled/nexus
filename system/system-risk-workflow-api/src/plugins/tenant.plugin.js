module.exports = function tenantPlugin(schema) {
    schema.add({
      tenant_id: {
        type: String,
        required: true,
        index: true
      }
    })

    schema.pre(/^find/, function () {
      if (this.options.tenantId) {
        this.where({ tenant_id: this.options.tenantId })
      }
    })
  }