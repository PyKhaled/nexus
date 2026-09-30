const transitions = {
    draft: ["submitted"],
    submitted: ["in_review"],
    in_review: ["approved", "rejected", "changes_requested"],
    changes_requested: ["submitted"],
    approved: ["archived"],
    rejected: ["archived"]
  }

  function validateTransition(from, to) {
    const allowed = transitions[from] || []
    return allowed.includes(to)
  }

module.exports = { validateTransition }
