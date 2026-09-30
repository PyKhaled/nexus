from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from nexus_assembler.cli import main


ROOT = Path(__file__).resolve().parents[3]
BLUEPRINT = ROOT / "composition/examples/nexus-development.yaml"


class CliTest(unittest.TestCase):
    def run_cli(self, arguments: list[str]) -> tuple[int, str, str]:
        output = io.StringIO()
        error = io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            status = main(arguments)
        return status, output.getvalue(), error.getvalue()

    def test_plan_returns_machine_readable_output(self) -> None:
        status, output, error = self.run_cli(["plan", "--blueprint", str(BLUEPRINT)])
        self.assertEqual(0, status, error)
        self.assertEqual("passed", json.loads(output)["policyStatus"])

    def test_assemble_writes_requested_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "deployment"
            status, output, error = self.run_cli(
                ["assemble", "--blueprint", str(BLUEPRINT), "--output", str(destination)]
            )
            self.assertEqual(0, status, error)
            self.assertEqual(str(destination.resolve()), json.loads(output)["deploymentPackage"])
            self.assertTrue((destination / "compose.yml").is_file())

    def test_invalid_blueprint_returns_error_status(self) -> None:
        status, _output, error = self.run_cli(["plan", "--blueprint", "missing.yaml"])
        self.assertEqual(2, status)
        self.assertIn("error:", error)


if __name__ == "__main__":
    unittest.main()
