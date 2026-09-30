from __future__ import annotations

from pathlib import Path
from typing import Any

from ..assembler import Assembler, Repository
from ..data import canonical, load_yaml


def validate_blueprint(blueprint: str | Path | dict[str, Any], *, root: str | Path | None = None) -> dict[str, Any]:
    """Validate blueprint syntax and semantics, returning resolved dimension context."""
    assembler = Assembler(Repository(root))
    value = load_yaml(blueprint) if isinstance(blueprint, (str, Path)) else canonical(blueprint)
    context = assembler._validate_blueprint(value)
    return {
        "status": "passed",
        "product": value.get("product", {}).get("name"),
        "edition": context["edition"].get("id"),
        "environment": value.get("deployment", {}).get("environment"),
        "assurance": value.get("deployment", {}).get("assurance"),
    }
