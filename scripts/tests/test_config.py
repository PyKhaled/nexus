from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ConfigHelperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="nexus-config-")
        self.addCleanup(self.temporary.cleanup)
        self.scratch = Path(self.temporary.name)
        self.repository = self.scratch / "repo"
        (self.repository / "scripts").mkdir(parents=True)
        shutil.copy2(ROOT / "scripts/config.sh", self.repository / "scripts/config.sh")
        shutil.copytree(ROOT / "config/compose", self.repository / "config/compose")
        self.runtime = self.scratch / "runtime with spaces"
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "NEXUS_CONFIG_DIR": str(self.runtime),
                "NEXUS_ENV": "development",
            }
        )
        self.environment.pop("SECRETS_ENV", None)
        self.helper = self.repository / "scripts/config.sh"

    def run_helper(
        self,
        *arguments: str,
        environment: dict[str, str] | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        merged = self.environment.copy()
        if environment:
            merged.update(environment)
        return subprocess.run(
            ["bash", str(self.helper), *arguments],
            cwd=self.repository,
            env=merged,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_init_and_check_create_private_runtime_files(self) -> None:
        self.run_helper("init")
        self.run_helper("check")
        for name in ("config.env", "secret.env"):
            path = self.runtime / name
            self.assertTrue(path.is_file())
            self.assertEqual(0, stat.S_IMODE(path.stat().st_mode) & 0o027)

    def test_literal_values_and_process_precedence(self) -> None:
        self.run_helper("init")
        (self.runtime / "config.env").write_text(
            "SHARED=configuration\nLITERAL='$(touch should-not-run) $HOME `id` # literal'\nEMPTY=file\n"
        )
        (self.runtime / "secret.env").write_text(
            'SHARED=secret\nPASSWORD="test $dollar # spaces"\n'
        )
        self.run_helper(
            "run",
            "--",
            "bash",
            "-c",
            "[[ $SHARED == process && $EMPTY == '' && $PASSWORD == 'test $dollar # spaces' ]]",
            environment={"SHARED": "process", "EMPTY": ""},
        )
        self.assertFalse((self.repository / "should-not-run").exists())

    def test_rejects_duplicates_unsafe_permissions_and_symlinks(self) -> None:
        self.run_helper("init")
        secret = self.runtime / "secret.env"
        secret.write_text("KEY=one\nKEY=two\n")
        self.assertNotEqual(0, self.run_helper("check", check=False).returncode)

        secret.write_text("KEY=value\n")
        secret.chmod(0o644)
        self.assertNotEqual(0, self.run_helper("check", check=False).returncode)

        secret.unlink()
        secret.symlink_to(self.runtime / "config.env")
        self.assertNotEqual(0, self.run_helper("check", check=False).returncode)

    def test_production_defaults_to_etc_nexus(self) -> None:
        result = self.run_helper(
            "path",
            environment={"NEXUS_ENV": "production", "NEXUS_CONFIG_DIR": ""},
        )
        self.assertIn("/etc/nexus/secret.env", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
