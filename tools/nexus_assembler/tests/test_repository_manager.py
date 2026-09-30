from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from nexus_assembler import Repository
from nexus_assembler.data import dump_yaml, load_yaml
from nexus_assembler.errors import ValidationError
from nexus_assembler.repository_manager import GitResult, RepositoryManager


class RepositoryManagerTest(unittest.TestCase):
    def git(self, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            self.fail(result.stderr or result.stdout)
        return result

    def initialize(self, root: Path) -> None:
        self.git(root, "init", "--initial-branch=main")
        self.git(root, "config", "user.name", "Nexus Test")
        self.git(root, "config", "user.email", "nexus@example.test")

    def write_blueprint(self, root: Path, repositories: list[dict]) -> Path:
        path = root / "nexus.yaml"
        path.write_text(
            dump_yaml(
                {
                    "apiVersion": "nexus.io/composition/v1alpha1",
                    "product": {"name": "test", "edition": "custom"},
                    "deployment": {
                        "target": "local",
                        "environment": "development",
                        "assurance": "standard",
                    },
                    "capabilities": {},
                    "repositories": repositories,
                }
            )
        )
        return path

    def test_add_declares_and_initializes_local_submodule(self) -> None:
        with tempfile.TemporaryDirectory() as parent_dir, tempfile.TemporaryDirectory() as child_dir:
            parent = Path(parent_dir)
            child = Path(child_dir)
            self.initialize(parent)
            self.initialize(child)
            (child / "README.md").write_text("# Child\n")
            self.git(child, "add", "README.md")
            self.git(child, "commit", "-m", "Initial child")
            blueprint = self.write_blueprint(parent, [])
            self.git(parent, "add", "nexus.yaml")
            self.git(parent, "commit", "-m", "Initial parent")

            def runner(*arguments: str) -> GitResult:
                result = subprocess.run(
                    ["git", "-C", str(parent), "-c", "protocol.file.allow=always", *arguments],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                return GitResult(result.stdout, result.stderr, result.returncode == 0)

            manager = RepositoryManager(Repository(parent), runner=runner)
            report = manager.add(blueprint, name="system-service", url=str(child), branch="main")
            self.assertEqual("initialized", report["status"])
            self.assertEqual("system/system-service", load_yaml(blueprint)["repositories"][0]["path"])

    def test_required_missing_repository_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.initialize(root)
            blueprint = self.write_blueprint(
                root,
                [
                    {
                        "name": "missing",
                        "url": "https://example.test/missing.git",
                        "path": "system/missing",
                        "required": True,
                    }
                ],
            )
            manager = RepositoryManager(Repository(root))
            with self.assertRaises(ValidationError):
                manager.validate(blueprint)


if __name__ == "__main__":
    unittest.main()
