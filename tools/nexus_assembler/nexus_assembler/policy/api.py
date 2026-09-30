from __future__ import annotations

from pathlib import Path
from typing import Any

from ..assembly.api import assemble


def evaluate_policies(blueprint: str | Path | dict[str, Any], *, root: str | Path | None = None) -> dict[str, Any]:
    """Assemble in memory and return the policy report only."""
    return assemble(blueprint, root=root).policy_report
