class Error(Exception):
    """Base Nexus Assembler error."""


class ValidationError(Error):
    """Raised when blueprint, repository, or Compose validation fails."""


class PolicyError(Error):
    """Raised when an assembled deployment package fails policy validation."""
