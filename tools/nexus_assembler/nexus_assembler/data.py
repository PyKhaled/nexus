from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import yaml

from .errors import ValidationError


def load_yaml(path: str | Path) -> Any:
    path = Path(path)
    try:
        value = yaml.safe_load(path.read_text())
        return {} if value is None else value
    except OSError as exc:
        raise ValidationError(f"cannot read YAML file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValidationError(f"invalid YAML in {path}: {exc}") from exc


def canonical(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): canonical(value[key]) for key in sorted(value, key=lambda item: str(item))}
    if isinstance(value, list):
        return [canonical(item) for item in value]
    return value


def dump_yaml(value: Any) -> str:
    return yaml.safe_dump(canonical(value), sort_keys=False, default_flow_style=False, width=10_000)


def deep_merge(left: Any, right: Any, path: list[str] | None = None) -> Any:
    path = path or []
    if not isinstance(left, dict) or not isinstance(right, dict):
        return canonical(right)

    result = canonical(left)
    for key, value in right.items():
        string_key = str(key)
        if string_key in result and path and path[-1] == "services":
            raise ValidationError(f'duplicate Compose service "{string_key}"')
        if string_key in result and isinstance(result[string_key], dict) and isinstance(value, dict):
            result[string_key] = deep_merge(result[string_key], value, path + [string_key])
        else:
            result[string_key] = canonical(value)
    return result


def transform(value: Any, callback: Callable[[Any], Any]) -> Any:
    if isinstance(value, dict):
        transformed = {str(key): transform(item, callback) for key, item in value.items()}
    elif isinstance(value, list):
        transformed = [transform(item, callback) for item in value]
    else:
        transformed = value
    return callback(transformed)
