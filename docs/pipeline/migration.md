# Pipeline Playbook Import

The playbook teaches selection and adaptation rather than installing a whole stack with Bash. Its reusable assets are integrated into Nexus as follows:

- `base/tools/` → `tools/secreport/`.
- Pipeline concepts and guides → `docs/pipeline/`.
- `variants/*/.github/workflows/` → smaller canonical templates under `templates/workflows/`, organized by capability.
- Variant policies and scanner files → reviewed starter configuration under `templates/configuration/`; original stack-specific values remain archived.
- `apply.sh` → retired from the recommended adoption workflow.
- Stack bundles → documented recipes and synchronized configurations under `examples/`.

The external Pipeline source workspace remains unchanged, and its stale `AGENTS.md` was not imported. Current editing and validation commands are in [Contributing](contributing.md).

Behavior changes: generic npm, Django, and Laravel tests replace product commands; filesystem security uses a deliberately smaller Trivy starter; all HIGH/CRITICAL findings block by default; publishers are manual on `main`; scan-gated publishing pushes the local scanned image; deployment is a separate manual request. There is no commit-message gate bypass.
