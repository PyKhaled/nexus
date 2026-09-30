from __future__ import annotations

from pathlib import Path
from typing import Any

from ..assembler import Assembler, Repository, Result
from ..data import canonical, load_yaml

Blueprint = str | Path | dict[str, Any]


def _assembler(root: str | Path | None = None) -> Assembler:
    return Assembler(Repository(root))


def assemble(blueprint: Blueprint, *, root: str | Path | None = None) -> Result:
    """Assemble a blueprint into an in-memory deployment result without writing files."""
    return _assembler(root).assemble(blueprint)


def plan_blueprint(blueprint: Blueprint, *, root: str | Path | None = None) -> dict[str, Any]:
    """Resolve a blueprint and return a machine-readable plan."""
    return _assembler(root).plan(blueprint)


def resolve_components(blueprint: Blueprint, *, root: str | Path | None = None) -> list[dict[str, Any]]:
    """Resolve the concrete catalog components selected by a blueprint."""
    assembler = _assembler(root)
    if isinstance(blueprint, (str, Path)):
        value = load_yaml(blueprint)
    else:
        value = canonical(blueprint)
    context = assembler._validate_blueprint(value)
    return assembler._resolve_components(value, context["edition"])


def write_deployment_package(
    result: Result,
    output_directory: str | Path,
    *,
    root: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Materialize an assembled result as a deployment package."""
    return _assembler(root).write_deployment_package(result, output_directory, force=force)
