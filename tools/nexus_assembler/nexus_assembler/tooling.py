"""Small helpers intended for repository tools, CI, and agent integrations."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from urllib.parse import unquote

import yaml


def validate_markdown_links(root: Path, paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(errors="replace")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#") or target.startswith("mailto:"):
                continue
            clean = unquote(target.split("#", 1)[0])
            if clean and not (path.parent / clean).exists():
                errors.append(f"{path.relative_to(root)}: broken link {target}")
    return errors


def validate_yaml_files(paths: list[Path]) -> tuple[int, list[str]]:
    count = 0
    errors: list[str] = []
    for path in paths:
        try:
            list(yaml.safe_load_all(path.read_text()))
            count += 1
        except yaml.YAMLError as exc:
            errors.append(f"{path}: {exc}")
    return count, errors


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
