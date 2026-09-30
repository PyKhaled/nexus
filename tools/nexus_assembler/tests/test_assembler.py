from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nexus_assembler import Assembler, Repository, validate_blueprint
from nexus_assembler.data import canonical, load_yaml
from nexus_assembler.errors import ValidationError


ROOT = Path(__file__).resolve().parents[3]


class AssemblerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assembler = Assembler(Repository(ROOT))

    def test_checked_in_blueprints_plan_successfully(self) -> None:
        expected = {
            "nexus-development.yaml": "development",
            "nexus-self-hosted-production.yaml": "production",
            "nexus-high-assurance.yaml": "production",
        }
        for name, environment in expected.items():
            with self.subTest(name=name):
                plan = self.assembler.plan(ROOT / "composition" / "examples" / name)
                self.assertEqual("passed", plan["policyStatus"])
                self.assertEqual(environment, plan["deployment"]["environment"])

    def test_development_blueprint_matches_root_compose(self) -> None:
        result = self.assembler.assemble(ROOT / "composition/examples/nexus-development.yaml")
        self.assertEqual(canonical(load_yaml(ROOT / "compose.yml")), canonical(result.compose))

    def test_writes_complete_deployment_package(self) -> None:
        result = self.assembler.assemble(ROOT / "composition/examples/nexus-development.yaml")
        with tempfile.TemporaryDirectory() as directory:
            destination = self.assembler.write_deployment_package(result, Path(directory) / "package")
            for name in (
                "compose.yml",
                "blueprint.yaml",
                "compose.lock.yaml",
                "build-plan.yaml",
                ".env.example",
                "secrets.required",
                "policy-report.json",
                "README.md",
            ):
                self.assertTrue((destination / name).is_file(), name)

    def test_validation_api_rejects_unknown_environment(self) -> None:
        blueprint = load_yaml(ROOT / "composition/examples/nexus-development.yaml")
        blueprint["deployment"]["environment"] = "unknown"
        with self.assertRaises(ValidationError):
            validate_blueprint(blueprint, root=ROOT)


if __name__ == "__main__":
    unittest.main()
