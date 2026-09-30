from __future__ import annotations

from pathlib import Path
from typing import Any

from ..assembler import Repository
from ..repository_declarations import validate as _validate_declarations
from ..repository_manager import RepositoryManager


def validate_repository_declarations(value: Any) -> list[dict[str, Any]]:
    return _validate_declarations(value)


def validate_repositories(blueprint: str | Path, *, root: str | Path | None = None) -> dict[str, Any]:
    """Verify declared repositories and Git submodule state without changing them."""
    return RepositoryManager(Repository(root)).validate(blueprint)
