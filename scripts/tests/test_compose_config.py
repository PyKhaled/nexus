from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ComposeConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        if shutil.which("docker") is None:
            self.skipTest("Docker CLI is not installed")
        probe = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode:
            self.skipTest("Docker Compose is not available")

        self.temporary = tempfile.TemporaryDirectory(prefix="nexus-compose-config-")
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name)
        files = (
            "compose.yml",
            "compose.config.yml",
            "compose.secrets.yml",
            "Makefile",
            "scripts/config.sh",
            "config/compose/config.env.example",
            "config/compose/secret.env.example",
            "system/system-auth/.env.example",
            "system/system-auth-db/.env.example",
        )
        for relative in files:
            destination = self.repository / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)

        self.runtime = self.repository / "private config"
        self.runtime.mkdir()
        config = "MYSQL_DATABASE=example\nKC_DB_USERNAME=example\nPOSTGRES_USER=example\n"
        secrets = (
            "MYSQL_PASSWORD=literal $dollar # password\n"
            "MYSQL_ROOT_PASSWORD=admin-only\n"
            "KC_DB_PASSWORD=auth-password\n"
            "POSTGRES_PASSWORD=auth-password\n"
            "KENER_SECRET_KEY=status-only\n"
        )
        (self.runtime / "config.env").write_text(config)
        (self.runtime / "secret.env").write_text(secrets)
        for path in self.runtime.glob("*.env"):
            path.chmod(0o600)

        self.environment = os.environ.copy()
        self.environment.update(
            {
                "NEXUS_CONFIG_DIR": str(self.runtime),
                "NEXUS_ENV": "development",
                "SECRETS_ENV": str(self.repository / "absent"),
            }
        )
        for line in (config + secrets).splitlines():
            self.environment.pop(line.split("=", 1)[0], None)

    def run_command(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            arguments,
            cwd=self.repository,
            env=self.environment,
            capture_output=True,
            text=True,
            check=check,
        )

    def model(self, *extra_files: str) -> dict:
        files = ("compose.yml", "compose.config.yml", *extra_files)
        arguments = ["bash", "scripts/config.sh", "run", "--", "docker", "compose", "--env-file", "/dev/null"]
        for filename in files:
            arguments.extend(("-f", filename))
        arguments.extend(("config", "--format", "json"))
        return json.loads(self.run_command(*arguments).stdout)

    def test_environment_mapping_and_secret_isolation(self) -> None:
        self.run_command("make", "-s", "config-check", "compose-check")
        services = self.model()["services"]
        password = services["website"]["environment"]["WORDPRESS_DB_PASSWORD"]
        self.assertEqual("literal $$dollar # password", password)
        self.assertEqual(password, services["website-db"]["environment"]["MYSQL_PASSWORD"])
        self.assertEqual("auth-password", services["keycloak"]["environment"]["KC_DB_PASSWORD"])
        self.assertNotIn("MYSQL_ROOT_PASSWORD", services["website"]["environment"])
        self.assertNotIn("KENER_SECRET_KEY", services["gateway"]["environment"])

    def test_secret_file_overlay_removes_password_environment(self) -> None:
        for name in ("mysql_password", "mysql_root_password"):
            (self.runtime / name).write_text("synthetic")
        with (self.runtime / "config.env").open("a") as handle:
            handle.write(f"MYSQL_PASSWORD_FILE={self.runtime / 'mysql_password'}\n")
            handle.write(f"MYSQL_ROOT_PASSWORD_FILE={self.runtime / 'mysql_root_password'}\n")

        self.run_command("make", "-s", "compose-check", "COMPOSE_SECRETS=compose.secrets.yml")
        services = self.model("compose.secrets.yml")["services"]
        self.assertNotIn("WORDPRESS_DB_PASSWORD", services["website"]["environment"])
        self.assertNotIn("MYSQL_PASSWORD", services["website-db"]["environment"])
        grants = [item["source"] for item in services["website"]["secrets"]]
        self.assertEqual(["mysql_password"], grants)

    def test_root_compose_is_rejected_for_production(self) -> None:
        result = self.run_command("make", "-s", "compose-check", "ENV=production", check=False)
        self.assertNotEqual(0, result.returncode)


if __name__ == "__main__":
    unittest.main(verbosity=2)
