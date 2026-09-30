from __future__ import annotations

from pathlib import Path

from ..assembler import Repository
from ..repository_manager import RepositoryManager


def add_repository(blueprint: str | Path, *, name: str, url: str, path: str | None = None, branch: str | None = None, required: bool = True, root: str | Path | None = None):
    """Mutating operation: add a declared Git submodule repository."""
    return RepositoryManager(Repository(root)).add(blueprint, name=name, url=url, path=path, branch=branch, required=required)


def sync_repositories(blueprint: str | Path, *, root: str | Path | None = None):
    """Mutating operation: synchronize declared Git submodules."""
    return RepositoryManager(Repository(root)).sync(blueprint)
