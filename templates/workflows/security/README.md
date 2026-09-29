# Security Workflow Template

Copy `devsecops.yml` to `.github/workflows/devsecops.yml` when you need filesystem vulnerability and misconfiguration checks. It runs on PRs, pushes to `main`, and manual dispatch.

## Required files

Copy the complete repository `tools/secreport/` directory to the same path in your application, plus `templates/configuration/security/` contents to `security/`. The job installs the report requirements with Python 3.12. It needs `contents: read` and internet access for tools/databases; it does not require custom secrets.

## Customize

Review branches, scan target, scanner selection, policy context and thresholds, artifact retention, and dependency versions. Keep input validation and scanner operational failures blocking. This starter has no baseline dependency because its policy considers all findings.

## Verify

Confirm clean SARIF produces a passing gate and a synthetic HIGH/CRITICAL result blocks. Confirm absent or malformed evidence also fails. Inspect the uploaded `security-report` artifact and configure the `scan` check as required where appropriate.

## Limits

This is Trivy starter coverage, not the archived multi-tool suite. Evidence is uploaded to GitHub, and the report engine downloads public enrichment data. The report gate alone does not detect absent scanner coverage. See [Security Gates](../../../docs/pipeline/concepts/security-gates.md).
