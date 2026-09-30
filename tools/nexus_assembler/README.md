# Nexus Assembler — Python Toolkit

Python package and CLI port of the original Ruby Nexus Assembler, refactored so the same core capabilities can be reused by humans, CI pipelines, verification tools, and AI agents.

## Design rule

```text
nexus_assembler/       reusable Python APIs
        │
        ├──────────────► tools/    inspect / validate / audit / verify
        │                           preferably read-only
        │
        └──────────────► scripts/  operational actions that may change state

nexus CLI              human-facing product interface
```

**Tools are tools. Scripts are operations.**

- `tools/` should inspect, validate, audit, or verify state and return useful exit codes/results for CI and agents.
- `scripts/` may modify files, Git/submodule state, configuration, or runtime state.
- `nexus_assembler/` contains the reusable implementation so tools and scripts do not duplicate business logic.

See [ARCHITECTURE.md](ARCHITECTURE.md).

## Requirements

- Python 3.11+
- Git for repository commands
- Docker Compose is optional; package validation uses it when available

## Install

```bash
python -m pip install .
```

Development:

```bash
python -m pip install -e '.[dev]'
pytest
```

The installed command is:

```bash
nexus --help
```

## Repository root

The Python package uses:

1. `NEXUS_ROOT` when defined;
2. otherwise the current working directory.

Expected repository data remains compatible with the Ruby implementation:

```text
composition/
├── base.compose.yml
├── catalog/
├── editions/
├── environments/
├── targets/
└── assurance/

system/
```

## CLI

### Plan

```bash
nexus plan --blueprint product.yaml
```

### Assemble

```bash
nexus assemble --blueprint product.yaml --output dist/product
```

Replace a non-empty destination:

```bash
nexus assemble --blueprint product.yaml --output dist/product --force
```

Generated package:

```text
compose.yml
blueprint.yaml
compose.lock.yaml
build-plan.yaml
.env.example
secrets.required
policy-report.json
README.md
runtime/
```

### Validate generated package / Compose

```bash
nexus validate dist/product
nexus validate compose.yml
```

### Collect secrets

```bash
nexus secrets --blueprint product.yaml --output .env.secrets
```

### Repository operations

```bash
nexus repository list --blueprint product.yaml
nexus repository status --blueprint product.yaml
nexus repository validate --blueprint product.yaml
nexus repository sync --blueprint product.yaml
```

Add a repository:

```bash
nexus repository add backend git@github.com:org/backend.git \
  --blueprint product.yaml \
  --branch main
```

## Reusable Python API

The package exposes stable functions instead of requiring callers to use `Assembler._private_methods`.

### Assembly

```python
from nexus_assembler import assemble, plan_blueprint, resolve_components

plan = plan_blueprint("product.yaml")
components = resolve_components("product.yaml")
result = assemble("product.yaml")
```

Available APIs:

```text
assemble()
plan_blueprint()
resolve_components()
write_deployment_package()
```

### Validation

```python
from nexus_assembler import (
    validate_blueprint,
    validate_compose,
    validate_deployment_package,
    validate_repositories,
)
```

These are intended to be reusable in CI and agent workflows.

### Inspection

```python
from nexus_assembler import (
    inspect_catalog,
    inspect_dependencies,
    inspect_repository_status,
    collect_required_variables,
    collect_required_secrets,
)
```

### Policy

```python
from nexus_assembler import evaluate_policies

report = evaluate_policies("product.yaml")
```

## Tools — read-only validation / audit / inspection

```text
tools/
├── validate_playbook.py
├── validate_blueprint.py
├── validate_compose.py
├── audit_policy.py
├── inspect_catalog.py
└── inspect_repositories.py
```

Examples:

```bash
python tools/validate_blueprint.py product.yaml
python tools/validate_compose.py compose.yml
python tools/audit_policy.py product.yaml
python tools/inspect_catalog.py
python tools/inspect_repositories.py product.yaml
python tools/validate_playbook.py --json
```

`validate_playbook.py` is the refactored version of the uploaded validator. It checks available repository contracts such as:

- Markdown links
- YAML syntax
- GitHub Actions SHA pinning
- deny-by-default workflow permissions
- checkout credential persistence
- example drift
- preservation hashes / inherited-engine integrity when those repository assets exist

It no longer performs validation at import time, so its functions can be reused from tests, CI, or agents.

## Scripts — operations that may mutate state

```text
scripts/
├── sync_examples.sh
├── repository_add.sh
└── repository_sync.sh
```

Examples:

```bash
bash scripts/sync_examples.sh
bash scripts/sync_examples.sh --check
bash scripts/repository_sync.sh product.yaml
bash scripts/repository_add.sh product.yaml backend git@github.com:org/backend.git --branch main
```

`sync_examples.sh` remains under `scripts/` because its primary purpose is synchronization: it writes example copies. Its `--check` mode is useful in CI, but the operation itself is mutating.

## Package layout

```text
nexus_assembler/
├── __init__.py
├── __main__.py
├── assembler.py                 # compatibility/core implementation
├── cli.py
├── data.py                      # compatibility data primitives
├── errors.py
├── repository_declarations.py
├── repository_manager.py
│
├── assembly/
│   └── api.py
├── config/
│   └── __init__.py
├── validation/
│   ├── blueprint.py
│   ├── compose.py
│   ├── package.py
│   └── repository.py
├── inspection/
│   ├── catalog.py
│   ├── dependencies.py
│   ├── repositories.py
│   └── requirements.py
├── policy/
│   └── api.py
├── repository/
│   └── operations.py
└── tooling.py
```

The Python package replaces the previous Ruby implementation while preserving
the command model and deployment-package contracts.

## Exit codes

CLI and tools use the same broad convention:

- `0` — success / validation passed
- `1` — usage/no command where applicable
- `2` — input, validation, Git, or assembler error
- `3` — execution completed but a policy, audit, or repository-status check failed

## Blueprint flow

```text
Blueprint
   ↓
Validate product/deployment/repositories
   ↓
Load edition + environment + target + assurance dimensions
   ↓
Resolve capability implementations from catalog
   ↓
Resolve component dependencies
   ↓
Merge base Compose + component fragments
   ↓
Apply deployment / assurance policy
   ↓
Evaluate policy checks
   ↓
Generate lock file, build plan, env contracts, and deployment package
```
