from __future__ import annotations

import argparse
import json
import sys

from . import VERSION
from .assembler import Assembler, Repository
from .data import canonical
from .errors import Error, ValidationError
from .repository_manager import RepositoryManager


def _print_json(value):
    print(json.dumps(canonical(value), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="nexus", description=f"Nexus Assembler {VERSION}")
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command")

    plan = sub.add_parser("plan", help="Resolve a blueprint without writing files")
    plan.add_argument("--blueprint", required=True)

    assemble = sub.add_parser("assemble", help="Assemble a deployment package from a blueprint")
    assemble.add_argument("--blueprint", required=True)
    assemble.add_argument("--output", required=True)
    assemble.add_argument("--force", action="store_true")

    validate = sub.add_parser("validate", help="Validate a Compose file or deployment package")
    validate.add_argument("path")

    secrets = sub.add_parser("secrets", help="Merge component .env files into one secrets file")
    secrets.add_argument("--blueprint", required=True)
    secrets.add_argument("--output", required=True)

    repository = sub.add_parser("repository", aliases=["repo"], help="Manage source repositories under system/")
    repo_sub = repository.add_subparsers(dest="repository_command")

    add = repo_sub.add_parser("add", help="Add and clone a repository as a Git submodule")
    add.add_argument("name"); add.add_argument("url"); add.add_argument("--blueprint", required=True)
    add.add_argument("--path"); add.add_argument("--branch"); add.add_argument("--optional", action="store_true")
    for name in ["list", "status", "sync", "validate"]:
        cmd = repo_sub.add_parser(name)
        cmd.add_argument("--blueprint", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    repository = Repository()
    assembler = Assembler(repository)
    manager = RepositoryManager(repository)
    try:
        if args.command == "plan":
            _print_json(assembler.plan(args.blueprint)); return 0
        if args.command == "assemble":
            manager.validate(args.blueprint)
            result = assembler.assemble(args.blueprint)
            destination = assembler.write_deployment_package(result, args.output, force=args.force)
            _print_json({"status": result.policy_report["status"], "deploymentPackage": str(destination), "output": str(destination), "services": sorted(result.compose["services"]), "policyReport": str(destination / "policy-report.json")})
            return 0 if result.policy_report["status"] == "passed" else 3
        if args.command == "validate":
            _print_json(assembler.validate_deployment_package(args.path)); return 0
        if args.command == "secrets":
            report = assembler.collect_secrets(args.blueprint, args.output)
            _print_json(report)
            if report["missingRequired"]:
                print(f"warning: missing required secrets: {', '.join(report['missingRequired'])}", file=sys.stderr)
            return 0
        if args.command in {"repository", "repo"}:
            if not args.repository_command:
                parser.parse_args([args.command, "--help"]); return 1
            if args.repository_command == "add":
                report = manager.add(args.blueprint, name=args.name, url=args.url, path=args.path, branch=args.branch, required=not args.optional)
                _print_json(report); return 0
            if args.repository_command == "list":
                _print_json({"repositories": manager.list(args.blueprint)}); return 0
            if args.repository_command == "status":
                report = manager.status(args.blueprint); _print_json(report)
                return 0 if report["status"].startswith("passed") else 3
            if args.repository_command == "sync":
                _print_json(manager.sync(args.blueprint)); return 0
            if args.repository_command == "validate":
                _print_json(manager.validate(args.blueprint)); return 0
        raise ValidationError(f"unknown command {args.command!r}")
    except Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
