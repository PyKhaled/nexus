# Contributing

## Sources of truth

Edit workflows and configuration in `templates/`, report tooling in `tools/secreport/`, and explanatory material in `docs/pipeline/`. Each template family documents prerequisites, destinations, customization, verification, and limits. Keep these contracts updated with behavior changes.

`examples/manifest.json` maps canonical sources to example destinations. Run `bash scripts/sync_examples.sh` after source changes, then add `--check` to detect drift. Do not hand-edit generated files. The script only writes mapped files within `examples/`; it is not an application installer.

Preserve the root `AGENTS.md` and the external source workspace. Use [Migration](migration.md) to understand the imported layout.

## Checks

Run the local playbook checks with the repository's configured Python environment:

```bash
bash scripts/sync_examples.sh --check
python3 tools/validate_playbook.py
```

The validator checks document links, YAML parsing, and action pin/permission conventions. The sync check separately verifies generated examples. Run `actionlint` on changed workflow templates when available; use `zizmor` for a separate workflow security review. Neither establishes hosted runtime success.

For adoption, run the copied workflows in an application repository and capture both success and intentional failure. This repository contains no application test suite or universal coverage threshold.

## Changes and pull requests

Use concise imperative messages such as `docs: clarify image publishing prerequisites`. Describe behavior changes, affected template families, required migration steps, and validation evidence. Link related issues. Do not claim deployment success from static checks, or update generated examples without their canonical sources.
