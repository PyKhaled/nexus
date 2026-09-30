from __future__ import annotations

from pathlib import Path
from typing import Any

from ..assembly.api import resolve_components


def inspect_dependencies(blueprint: str | Path | dict[str, Any], *, root: str | Path | None = None) -> dict[str, Any]:
    components = resolve_components(blueprint, root=root)
    return {
        "components": [
            {
                "capability": c["capability"],
                "implementation": c["implementation"],
                "dependencies": c.get("dependencies", []),
            }
            for c in components
        ]
    }
