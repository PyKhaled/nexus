from __future__ import annotations

from pathlib import Path
from typing import Any

from ..assembly.api import assemble


def collect_required_variables(blueprint: str | Path | dict[str, Any], *, root: str | Path | None = None) -> list[str]:
    result = assemble(blueprint, root=root)
    names: set[str] = set()
    for component in result.components:
        for item in component.get("requiredVariables", []) or []:
            if isinstance(item, str):
                names.add(item)
            elif isinstance(item, dict) and item.get("name"):
                names.add(str(item["name"]))
    return sorted(names)


def collect_required_secrets(blueprint: str | Path | dict[str, Any], *, root: str | Path | None = None) -> list[str]:
    result = assemble(blueprint, root=root)
    names: set[str] = set()
    for component in result.components:
        for item in component.get("requiredSecrets", []) or []:
            if isinstance(item, str):
                names.add(item)
            elif isinstance(item, dict) and item.get("name"):
                names.add(str(item["name"]))
    # The rendered file is authoritative for ports where catalog schemas differ.
    for line in result.secrets_required.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.add(line.split("=", 1)[0].strip())
    return sorted(n for n in names if n)
