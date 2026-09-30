const { validateTransition } = require("../../src/modules/risks/risk.workflow")

describe("risk.workflow validateTransition", () => {
  describe("valid transitions", () => {
    it("draft -> submitted", () => {
      expect(validateTransition("draft", "submitted")).toBe(true)
    })
    it("submitted -> in_review", () => {
      expect(validateTransition("submitted", "in_review")).toBe(true)
    })
    it("in_review -> approved", () => {
      expect(validateTransition("in_review", "approved")).toBe(true)
    })
    it("in_review -> rejected", () => {
      expect(validateTransition("in_review", "rejected")).toBe(true)
    })
    it("in_review -> changes_requested", () => {
      expect(validateTransition("in_review", "changes_requested")).toBe(true)
    })
    it("changes_requested -> submitted", () => {
      expect(validateTransition("changes_requested", "submitted")).toBe(true)
    })
    it("approved -> archived", () => {
      expect(validateTransition("approved", "archived")).toBe(true)
    })
    it("rejected -> archived", () => {
      expect(validateTransition("rejected", "archived")).toBe(true)
    })
  })

  describe("invalid transitions", () => {
    it("draft -> approved", () => {
      expect(validateTransition("draft", "approved")).toBe(false)
    })
    it("submitted -> draft", () => {
      expect(validateTransition("submitted", "draft")).toBe(false)
    })
    it("in_review -> submitted", () => {
      expect(validateTransition("in_review", "submitted")).toBe(false)
    })
    it("draft -> in_review", () => {
      expect(validateTransition("draft", "in_review")).toBe(false)
    })
  })

  describe("unknown source status", () => {
    it("unknown -> submitted returns false", () => {
      expect(validateTransition("unknown", "submitted")).toBe(false)
    })
  })
})
