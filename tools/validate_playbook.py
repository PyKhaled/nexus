"""Validate repository/playbook contracts without calling external services.

This is a read-only TOOL: suitable for developers, CI, and AI agents.
It intentionally does not modify repository state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[1]


def validate_markdown_links(root: Path, paths: list[Path]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(errors="replace")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if "://" in target or target.startswith(("#", "mailto:")):
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


def validate_workflows(root: Path) -> list[str]:
    errors: list[str] = []
    directory = root / "templates" / "workflows"
    if not directory.exists():
        return errors
    for path in directory.rglob("*.yml"):
        workflow = yaml.safe_load(path.read_text()) or {}
        if workflow.get("permissions") != {}:
            errors.append(f"{path.relative_to(root)}: expected deny-by-default permissions")
        for job in (workflow.get("jobs") or {}).values():
            for step in job.get("steps", []):
                action = step.get("uses", "")
                if action and not re.fullmatch(r"[^@]+@[0-9a-f]{40}", action):
                    errors.append(f"{path.relative_to(root)}: action is not SHA-pinned: {action}")
                if action.startswith("actions/checkout@") and step.get("with", {}).get("persist-credentials") is not False:
                    errors.append(f"{path.relative_to(root)}: checkout credentials persist")
    return errors


def validate_examples(root: Path) -> list[str]:
    manifest_path = root / "examples" / "manifest.json"
    if not manifest_path.is_file():
        return []

    errors: list[str] = []
    manifest = json.loads(manifest_path.read_text())
    for example, mappings in manifest.items():
        for source, destination in mappings.items():
            source_path = (root / source).resolve()
            destination_path = (root / "examples" / example / destination).resolve()
            if not source_path.is_relative_to(root):
                errors.append(f"Manifest source escapes repository: {source}")
                continue
            if not destination_path.is_relative_to(root / "examples"):
                errors.append(f"Manifest destination escapes examples: {example}/{destination}")
                continue
            if not source_path.is_file():
                errors.append(f"Manifest source missing: {source}")
            elif not destination_path.is_file() or source_path.read_bytes() != destination_path.read_bytes():
                errors.append(f"Example drift: examples/{example}/{destination}")
    return errors


def validate_preservation(root: Path) -> tuple[int, list[str]]:
    manifest_path = root / "archive" / "manifest.json"
    if not manifest_path.is_file():
        return 0, []
    manifest = json.loads(manifest_path.read_text())
    errors: list[str] = []
    for name, expected in manifest.items():
        path = root / name if name == "AGENTS.md" else root / "archive" / "original-scaffold" / name
        if not path.is_file():
            errors.append(f"Preservation file missing: {name}")
        elif sha256_file(path) != expected:
            errors.append(f"Preservation hash mismatch: {name}")

    inherited = root / "tools" / "secreport"
    original = root / "archive" / "original-scaffold" / "base" / "tools"
    for name in ("secreport.py", "requirements.txt"):
        left, right = inherited / name, original / name
        if left.exists() or right.exists():
            if not left.is_file() or not right.is_file() or left.read_bytes() != right.read_bytes():
                errors.append(f"Inherited engine changed: {name}")
    return len(manifest), errors


def validate_playbook(root: Path = ROOT) -> dict:
    root = root.resolve()
    errors: list[str] = []

    markdown: list[Path] = []
    for folder in ("docs", "templates", "examples", "tools"):
        directory = root / folder
        if directory.exists():
            markdown.extend(directory.rglob("*.md"))
    if (root / "README.md").is_file():
        markdown.append(root / "README.md")
    errors.extend(validate_markdown_links(root, markdown))

    yaml_paths: list[Path] = []
    for folder in ("templates", "examples"):
        directory = root / folder
        if directory.exists():
            yaml_paths.extend(p for p in directory.rglob("*") if p.suffix in {".yml", ".yaml"})
    yaml_count, yaml_errors = validate_yaml_files(yaml_paths)
    errors.extend(yaml_errors)
    errors.extend(validate_workflows(root))
    errors.extend(validate_examples(root))
    hash_count, preservation_errors = validate_preservation(root)
    errors.extend(preservation_errors)

    return {
        "status": "passed" if not errors else "failed",
        "yamlFiles": yaml_count,
        "preservationHashes": hash_count,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    report = validate_playbook(args.root)
    if args.as_json:
        print(json.dumps(report, indent=2))
    elif report["errors"]:
        print("\n".join(report["errors"]), file=sys.stderr)
    else:
        print(
            f"Validated {report['yamlFiles']} YAML files, documentation links, action conventions, "
            f"example copies, and {report['preservationHashes']} preservation hashes"
        )
    return 0 if report["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
