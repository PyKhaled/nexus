from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Any

from .data import canonical
from .errors import ValidationError

ALLOWED_FIELDS = {"name", "url", "path", "branch", "required"}
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


def _duplicates(values: list[str]) -> list[str]:
    return sorted({value for value in values if values.count(value) > 1})


def validate(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationError("repositories must be a list")

    repositories: list[dict[str, Any]] = []
    for index, candidate in enumerate(value):
        label = f"repositories[{index}]"
        if not isinstance(candidate, dict):
            raise ValidationError(f"{label} must be a mapping")

        repository = canonical(candidate)
        unknown = sorted(set(repository) - ALLOWED_FIELDS)
        if unknown:
            raise ValidationError(f"unknown {label} fields: {', '.join(unknown)}")

        name = str(repository.get("name", ""))
        if not NAME_RE.fullmatch(name):
            raise ValidationError(f"{label}.name must be a lowercase DNS-style name")

        url = str(repository.get("url", "")).strip()
        if not url:
            raise ValidationError(f"{label}.url is required")

        path = str(repository.get("path", ""))
        pure = PurePosixPath(path)
        normalized = str(pure)
        if (
            not path
            or path != normalized
            or pure.is_absolute()
            or not path.startswith("system/")
            or path == "system/"
            or ".." in pure.parts
        ):
            raise ValidationError(f"{label}.path must be a normalized relative path below system/")

        if "branch" in repository and not str(repository["branch"]).strip():
            raise ValidationError(f"{label}.branch must not be empty")
        if "required" in repository and not isinstance(repository["required"], bool):
            raise ValidationError(f"{label}.required must be true or false")

        repository.update(name=name, url=url, path=path, required=repository.get("required", True))
        repositories.append(repository)

    duplicate_names = _duplicates([repo["name"] for repo in repositories])
    duplicate_paths = _duplicates([repo["path"] for repo in repositories])
    if duplicate_names:
        raise ValidationError(f"duplicate repository names: {', '.join(duplicate_names)}")
    if duplicate_paths:
        raise ValidationError(f"duplicate repository paths: {', '.join(duplicate_paths)}")

    return repositories
