from __future__ import annotations

from pathlib import Path
from typing import Any

from ..assembler import Repository


def inspect_catalog(*, root: str | Path | None = None) -> dict[str, dict[str, dict[str, Any]]]:
    """Return the component catalog indexed by capability and implementation."""
    return Repository(root).catalog
