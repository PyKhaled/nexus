# Pipeline Playbook

A practical guide to designing CI/CD and DevSecOps pipelines, with reusable GitHub Actions templates and worked configuration examples.

Start with the capability you need, understand its requirements, then copy and adapt its template. There is no installer in the primary workflow.

## Start Here

- **Add application checks:** follow the [Node](guides/node.md), [Laravel](guides/laravel.md), or [Django](guides/django.md) guide.
- **Add security checks:** read [Security Gates](concepts/security-gates.md) and use the [security template](../../templates/workflows/security/README.md).
- **Publish a container:** choose [basic or scan-gated publishing](../../templates/workflows/containers/README.md).
- **Request a development deployment:** adapt the optional [Devtron template](../../templates/workflows/deployment/README.md).
- **See a complete file layout:** browse the [examples](../../examples/README.md).

New to the kit? Begin with [Getting Started](getting-started.md) and [Choosing a Pipeline](choosing-a-pipeline.md).

For the broader target model, use the [Implementation Guide](implementation-guide.md),
[Delivery Architecture](concepts/delivery-architecture.md), and
[Evidence Contracts](reference/evidence-contracts.md).

## Layout

```text
docs/pipeline/  Concepts, adoption guides, and configuration reference
templates/      Canonical workflows, configuration, and Kubernetes sample
tools/          Security report engine and contributor validation utilities
examples/       Pipeline configurations assembled from canonical sources
```

The examples supply pipeline configuration, not application source. Bring your application's dependency files, tests, settings, and Dockerfile. Runtime versions and scanner/action pins are starting points inherited from the kit; review compatibility and available updates before adopting them.

## Design Choices

- Keep application CI, security checks, publishing, and deployment understandable as separate capabilities.
- Use `secreport` to turn scanner evidence into an explicit policy decision.
- Reject missing or malformed scanner evidence before reporting.
- Make basic publishing and scan-gated publishing distinct templates. The latter pushes the same local image that was scanned.
- Require deliberate manual publishing from `main`; configure required CI checks on that branch. Publishing workflows do not themselves wait for CI.
- Use SHA-pinned actions and minimal job permissions. Scanner downloads and report enrichment still require network access; evidence is uploaded to GitHub artifacts.

The starter security workflow uses Trivy for vulnerability and misconfiguration checks. It does not recreate the archived multi-scanner suite or provide complete security coverage.

## Contributing and Validation

Edit canonical files in `templates/` or `tools/secreport/`, then refresh generated example files:

```bash
bash scripts/sync_examples.sh
bash scripts/sync_examples.sh --check
python3 tools/validate_playbook.py
```

The sync utility maintains examples within this repository; adoption is guided copying, not script installation. Checks cover YAML, local documentation links, workflow conventions, and example drift. They do not demonstrate a successful hosted workflow or deployment. See the [migration validation notes](validation.md).

See [Contributing](contributing.md) and the [migration map](migration.md) for current paths.

## Provenance

These playbook assets were imported from the preserved Pipeline workspace. Active templates use generic project names and documented assumptions; the source workspace remains unchanged.
