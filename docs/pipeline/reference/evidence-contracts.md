# Evidence Contracts

An evidence contract defines what a producer uploads and what the policy gate
may assume. Stable contracts let scanners change without coupling report and
policy logic to one implementation.

Only `raw-artifacts/trivy.sarif` and the resulting SecReport outputs are wired
into the current starter. The remaining names below describe target contracts
for future workflow templates.

## Required fields

Each producer should record:

- producer and scanner identity, including pinned version;
- source commit and workflow run identity;
- scope, configuration, and applicable repository profile;
- completion state distinct from finding count;
- machine-readable evidence or an explicit diagnostic failure;
- creation time and retention expectations;
- artifact or image digest where the evidence concerns a built artifact.

The gate should reject malformed evidence and fail when a required class is
missing. Optional or inapplicable classes must be declared by reviewed policy,
not inferred from absent artifacts.

## Proposed artifact names

| Producer | Representative evidence | Artifact name | State |
| --- | --- | --- | --- |
| CI hygiene | Workflow lint and automation security | `scan-ci-hygiene` | Target |
| Secrets | Redacted repository-history findings | `scan-secrets` | Target |
| SAST | Language-appropriate static analysis | `scan-sast` | Target |
| SCA and SBOM | Dependency findings plus CycloneDX or SPDX inventory | `scan-sca` | Target |
| Configuration | IaC, YAML, Compose, and Dockerfile findings | `scan-config` | Partial through Trivy |
| Container | Image findings, hardening results, SBOM, and digest | `scan-container` | Partial through Trivy |
| Container image | Exact exported image for downstream testing | `container-image` | Target |
| DAST | Runtime web-application observations | `scan-dast` | Target |
| Report and gate | Normalized findings, coverage inventory, and verdict | `security-report` | Current for starter scope |

Artifact names are contracts, not proof that a scanner ran correctly. The gate
must inspect content and producer status before accepting coverage.

## Gate contract

The gate should:

1. Download every applicable evidence artifact.
2. Inventory expected and received evidence classes.
3. Reject missing, malformed, or explicitly unsuccessful required evidence.
4. Normalize supported formats into one finding schema.
5. Apply baseline and time-bounded exceptions deliberately.
6. Evaluate the reviewed policy once and freeze the verdict.
7. Render human and machine reports from that same verdict.
8. Upload reports even when the verdict blocks the workflow.

The current workflow implements these principles for one Trivy SARIF input. It
does not yet implement a general coverage inventory across all proposed
artifacts.

## Baselines and exceptions

A baseline distinguishes previously accepted findings from new findings; it
does not make old findings safe. Define how the first scan is handled before
enabling new-only gating. Exceptions should identify an owner, rationale,
scope, approval, and expiry. Expired or unmatched exceptions must not suppress
findings.

## Sensitive data

Evidence may contain repository paths, vulnerable package versions, source
snippets, or secret metadata. Redact secret values, minimize workflow
permissions, choose retention deliberately, and restrict artifact access. A
reporting pipeline is not automatically suitable for public artifacts.
