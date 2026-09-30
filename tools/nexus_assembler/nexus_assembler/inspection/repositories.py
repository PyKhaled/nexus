from __future__ import annotations

from pathlib import Path
from typing import Any

from ..assembler import Repository
from ..repository_manager import RepositoryManager


def inspect_repository_status(blueprint: str | Path, *, root: str | Path | None = None) -> dict[str, Any]:
    """Inspect declared repository/submodule state without modifying it."""
    return RepositoryManager(Repository(root)).status(blueprint)
