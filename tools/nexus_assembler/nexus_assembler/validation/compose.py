from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..assembler import Assembler, Repository
from ..data import load_yaml


def validate_compose(path_or_value: str | Path | dict[str, Any], *, root: str | Path | None = None) -> dict[str, Any]:
    """Validate the Nexus-required Compose structure without mutating anything."""
    assembler = Assembler(Repository(root))
    if isinstance(path_or_value, (str, Path)):
        path = Path(path_or_value)
        compose = load_yaml(path)
        text = path.read_text()
    else:
        compose = path_or_value
        text = ""
    assembler._validate_compose_structure(compose)
    required = sorted(set(re.findall(r"\$\{([A-Z][A-Z0-9_]*):\?", text)))
    return {"status": "passed", "services": sorted(compose["services"]), "requiredVariables": required}
