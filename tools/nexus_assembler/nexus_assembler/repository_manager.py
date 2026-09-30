from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .assembler import Repository
from .data import dump_yaml, load_yaml
from .errors import Error, ValidationError
from .repository_declarations import validate as validate_declarations


@dataclass(slots=True)
class GitResult:
    stdout: str
    stderr: str
    success: bool


class RepositoryManager:
    def __init__(self, repository: Repository | None = None, runner: Callable[..., GitResult] | None = None) -> None:
        self.repository = repository or Repository()
        self.runner = runner or self._run_git

    def add(self, blueprint_path: str | Path, *, name: str, url: str, path: str | None = None, branch: str | None = None, required: bool = True):
        blueprint = self._load_blueprint(blueprint_path)
        declaration = {"name": name, "url": url, "path": path or f"system/{name}", "required": required}
        if branch:
            declaration["branch"] = branch
        declarations = validate_declarations(list(blueprint.get("repositories") or []) + [declaration])
        self._ensure_git_repository()
        self._ensure_path_available(declaration["path"])
        arguments = ["submodule", "add"]
        if branch:
            arguments += ["--branch", branch]
        arguments += ["--", url, declaration["path"]]
        self._git(*arguments)
        blueprint["repositories"] = declarations
        self._atomic_write(Path(blueprint_path).resolve(), dump_yaml(blueprint))
        return self._report_for(declaration)

    def list(self, blueprint_path: str | Path):
        return [self._report_for(declaration) for declaration in self._declarations(blueprint_path)]

    def status(self, blueprint_path: str | Path):
        reports = self.list(blueprint_path)
        required_failures = [r for r in reports if r["required"] and r["status"] != "initialized"]
        optional_failures = [r for r in reports if not r["required"] and r["status"] != "initialized"]
        if required_failures:
            overall = "failed"
        elif optional_failures:
            overall = "passed-with-warnings"
        else:
            overall = "passed"
        return {"status": overall, "repositories": reports}

    def validate(self, blueprint_path: str | Path):
        report = self.status(blueprint_path)
        failures = [r for r in report["repositories"] if r["required"] and r["status"] != "initialized"]
        if failures:
            details = "; ".join(f"{r['name']}: {r['reason']}" for r in failures)
            raise ValidationError(f"repository validation failed: {details}")
        return report

    def sync(self, blueprint_path: str | Path):
        self._ensure_git_repository()
        entries = self._gitmodules_by_path()
        for declaration in self._declarations(blueprint_path):
            entry = entries.get(declaration["path"])
            if entry:
                self._validate_gitmodules_entry(declaration, entry)
                continue
            self._ensure_path_available(declaration["path"])
            arguments = ["submodule", "add"]
            if declaration.get("branch"):
                arguments += ["--branch", declaration["branch"]]
            arguments += ["--", declaration["url"], declaration["path"]]
            self._git(*arguments)
        self._git("submodule", "sync", "--recursive")
        self._git("submodule", "update", "--init", "--recursive")
        return self.validate(blueprint_path)

    def _declarations(self, blueprint_path):
        return validate_declarations(self._load_blueprint(blueprint_path).get("repositories"))

    def _load_blueprint(self, blueprint_path):
        path = Path(blueprint_path).resolve()
        if not path.is_file():
            raise ValidationError(f"blueprint file not found: {path}")
        blueprint = load_yaml(path)
        if not isinstance(blueprint, dict):
            raise ValidationError("blueprint must be a mapping")
        return blueprint

    def _report_for(self, declaration):
        entry = self._gitmodules_by_path().get(declaration["path"])
        status, reason = self._repository_state(declaration, entry)
        return {**declaration, "status": status, "reason": reason}

    def _repository_state(self, declaration, entry):
        if not entry:
            return "missing", "no matching entry in .gitmodules"
        mismatch = self._gitmodules_mismatch(declaration, entry)
        if mismatch:
            return "mismatch", mismatch
        absolute_path = self.repository.root / declaration["path"]
        gitlink = self._gitlink_commit(declaration["path"])
        if not gitlink:
            return "not-a-submodule", "path is not recorded as a Gitlink in the parent repository"
        if not absolute_path.is_dir():
            return "uninitialized", "submodule working tree is absent"
        top_level = self._git_in_path(absolute_path, "rev-parse", "--show-toplevel")
        if not top_level or Path(top_level.strip()).resolve() != absolute_path.resolve():
            return "not-a-submodule", "path exists but is not an initialized Git submodule"
        checkout = self._git_in_path(absolute_path, "rev-parse", "HEAD")
        checkout = checkout.strip() if checkout else None
        if checkout != gitlink:
            return "checkout-mismatch", f"checked out commit {checkout!r} does not match Gitlink {gitlink}"
        return "initialized", "configured and checked out"

    def _validate_gitmodules_entry(self, declaration, entry):
        mismatch = self._gitmodules_mismatch(declaration, entry)
        if mismatch:
            raise ValidationError(f"{declaration['name']} conflicts with .gitmodules: {mismatch}")

    @staticmethod
    def _gitmodules_mismatch(declaration, entry):
        if entry.get("url") != declaration["url"]:
            return f"URL is {entry.get('url')!r}, expected {declaration['url']!r}"
        if declaration.get("branch") and entry.get("branch") != declaration["branch"]:
            return f"branch is {entry.get('branch')!r}, expected {declaration['branch']!r}"
        return None

    def _gitmodules_by_path(self):
        path = self.repository.root / ".gitmodules"
        if not path.is_file():
            return {}
        entries = {}
        current = None
        for line in path.read_text().splitlines():
            match = re.match(r'^\s*\[submodule\s+"([^"]+)"\]\s*$', line)
            if match:
                current = {"name": match.group(1)}
                continue
            if current:
                match = re.match(r"^\s*(path|url|branch)\s*=\s*(.*?)\s*$", line)
                if match:
                    current[match.group(1)] = match.group(2)
                    if current.get("path"):
                        entries[current["path"]] = current.copy()
        return entries

    def _ensure_git_repository(self):
        self._git("rev-parse", "--show-toplevel")

    def _ensure_path_available(self, relative_path):
        if (self.repository.root / relative_path).exists():
            raise ValidationError(f"repository path already exists: {relative_path}")

    def _git(self, *arguments):
        result = self.runner(*arguments)
        if result.success:
            return result
        detail = result.stderr.strip() or result.stdout.strip()
        suffix = f": {detail}" if detail else ""
        raise Error(f"git {' '.join(arguments)} failed{suffix}")

    @staticmethod
    def _git_in_path(path: Path, *arguments):
        result = subprocess.run(["git", "-C", str(path), *arguments], capture_output=True, text=True, check=False)
        return result.stdout if result.returncode == 0 else None

    def _gitlink_commit(self, relative_path):
        result = subprocess.run(["git", "-C", str(self.repository.root), "ls-files", "--stage", "--", relative_path], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return None
        match = re.match(r"^160000\s+([0-9a-f]{40,64})\s+\d+\t", result.stdout)
        return match.group(1) if match else None

    def _run_git(self, *arguments):
        result = subprocess.run(["git", "-C", str(self.repository.root), *arguments], capture_output=True, text=True, check=False)
        return GitResult(stdout=result.stdout, stderr=result.stderr, success=result.returncode == 0)

    @staticmethod
    def _atomic_write(path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(content)
                handle.flush(); os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name): os.unlink(temp_name)
