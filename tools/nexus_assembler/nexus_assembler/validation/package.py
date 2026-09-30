from __future__ import annotations

from pathlib import Path
from typing import Any

from ..assembler import Assembler, Repository


def validate_deployment_package(path: str | Path, *, root: str | Path | None = None) -> dict[str, Any]:
    """Validate a deployment package or Compose file, including Docker Compose when available."""
    return Assembler(Repository(root)).validate_deployment_package(path)
