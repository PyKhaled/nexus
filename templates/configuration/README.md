# Configuration Templates

## Dependabot

Copy one file from `dependabot/` to `.github/dependabot.yml`. It updates GitHub Actions and the selected application's package ecosystem weekly. Change paths for monorepos; add Docker updates if applicable. For security tooling, also add a pip entry for `/tools/secreport`. Verify update jobs in the receiving repository. No custom secrets are required for public dependencies.

## Pre-commit

Copy `pre-commit/.pre-commit-config.yaml` to the application root, install pre-commit in your development environment, then run `pre-commit install` and `pre-commit run --all-files`. Review hook versions and exclusions. Hooks check YAML, whitespace, merge conflicts, and private keys; they do not provide full secret or application security scanning.

## Security policies

Copy `security/` contents to `security/`. Review defaults and validate clean and blocking outcomes using the [policy reference](../../docs/pipeline/reference/risk-policies.md). Empty exceptions are intentional. No policy should be considered an assessment of the receiving application's risk without review.

## Scanner settings

`scanners/trivy.yaml` is an optional CLI example. Configure your invocation to consume it; active workflow inputs are set explicitly. Verify effective configuration and report output. See [Scanner Configuration](../../docs/pipeline/reference/scanner-configuration.md).
