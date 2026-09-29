# SecReport

**SecReport** is an open-source DevSecOps security aggregation, enrichment, risk-scoring, reporting, and policy-gating tool for CI/CD pipelines.

It collects output from multiple security scanners, converts their findings into one normalized model, removes duplicates, enriches vulnerabilities with real-world exploit intelligence, distinguishes new findings from existing security debt, applies approved risk exceptions, calculates contextual risk scores, and produces a single auditable security decision.

```text
Scanners
   │
   ▼
Raw SARIF / JSON / JSONL / SBOM
   │
   ▼
┌─────────────────────────────┐
│          SecReport          │
├─────────────────────────────┤
│ Collect                     │
│ Normalize                   │
│ Deduplicate                 │
│ Enrich                      │
│ Score                       │
│ Baseline                    │
│ Exceptions                  │
│ Optional AI triage          │
│ Policy evaluation           │
│ Reporting                   │
└──────────────┬──────────────┘
               │
     ┌─────────┴─────────┐
     ▼                   ▼
 Reports             PASS / FAIL
```

SecReport follows one important rule:

> **Scanners produce evidence. SecReport makes the security decision.**

Individual scanners therefore do not independently decide whether a build should pass or fail.

---

## Features

- Aggregate findings from multiple security scanners
- Parse SARIF 2.1.0 and scanner-specific JSON formats
- Normalize findings into one canonical data model
- Normalize scanner-specific severity levels
- Deduplicate findings reported by multiple tools
- Preserve multi-tool confirmation
- Generate stable finding fingerprints
- Track new versus pre-existing findings
- Enrich CVEs using:
  - CISA Known Exploited Vulnerabilities — KEV
  - FIRST Exploit Prediction Scoring System — EPSS
- Calculate contextual risk scores from `0–100`
- Prioritize actively exploited vulnerabilities
- Track whether fixes are available
- Support time-boxed risk acceptances
- Fail on expired exceptions
- Support remediation SLAs
- Optionally use a local LLM for false-positive triage
- Produce one centralized CI/CD gate decision
- Generate:
  - JSON
  - Markdown
  - SARIF
  - Excel
  - PDF
- Gracefully cache threat-intelligence data for offline runs
- Use open-source tooling and public intelligence sources
- Require no commercial security platform

---

# Why SecReport?

A typical DevSecOps pipeline may run several independent scanners:

```text
Semgrep
Trivy
Grype
OSV-Scanner
Gitleaks
TruffleHog
Checkov
Hadolint
Dockle
OWASP ZAP
Nuclei
zizmor
OpenSSF Scorecard
...
```

Each tool has its own:

- output format
- severity model
- rule identifiers
- duplicate findings
- exit codes
- policy behavior

If every scanner independently controls CI, the pipeline becomes difficult to reason about:

```text
Semgrep ──────► pass/fail
Trivy ────────► pass/fail
Checkov ──────► pass/fail
Gitleaks ─────► pass/fail
Grype ────────► pass/fail
```

SecReport instead centralizes the decision:

```text
Semgrep ──────┐
Trivy ────────┤
Checkov ──────┤
Gitleaks ─────┤
Grype ────────┤
ZAP ──────────┤
Nuclei ───────┘
              │
              ▼
         Security evidence
              │
              ▼
           SecReport
              │
         ┌────┴────┐
         ▼         ▼
       PASS       FAIL
```

This gives the organization one consistent and auditable security policy.

---

# Installation

## From source

Clone the repository and install the package in editable mode:

```bash
git clone https://github.com/<organization>/secreport.git
cd secreport

python -m venv .venv
source .venv/bin/activate

pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

If report generation dependencies are provided as optional extras, install them with:

```bash
pip install -e ".[reports]"
```

A complete package installation will typically require:

```text
PyYAML
openpyxl
reportlab
matplotlib
```

---

# Quick Start

Assume your scanners write their output to:

```text
raw-artifacts/
├── semgrep.sarif
├── trivy.sarif
├── grype.json
├── osv.json
├── checkov.sarif
├── gitleaks.sarif
├── trufflehog.jsonl
├── zap.json
└── sbom.cdx.json
```

Run SecReport:

```bash
secreport run \
  --input raw-artifacts \
  --out reports \
  --policy security/risk-policy.yaml \
  --exceptions security/exceptions.yaml \
  --baseline .baseline/baseline.json \
  --markdown \
  --sarif \
  --xlsx \
  --pdf
```

SecReport will:

```text
→ collecting scanner output
→ 47 raw findings
→ 31 after de-duplication
→ enriching with CISA KEV + FIRST EPSS
   KEV entries: ...
   EPSS entries: ...
→ wrote summary.md
→ wrote consolidated.sarif
→ wrote devsecops-report.xlsx
→ wrote devsecops-report.pdf

FAIL — 31 findings (4 new, 1 KEV, 0 verified secrets)
```

The `run` command always exits successfully after producing its reports.

Use the separate gate command to enforce CI policy:

```bash
secreport gate \
  --results reports/findings.json \
  --policy security/risk-policy.yaml
```

A passing gate returns:

```text
✅ Security gate PASSED
```

with exit code:

```text
0
```

A failing gate returns:

```text
❌ Security gate FAILED

  • 1 new finding(s) exceeds the configured risk threshold

Options:
  1. Fix the finding.
  2. Add a time-boxed approved exception.
  3. Tune the scanner rule when the finding is incorrect.
```

with exit code:

```text
1
```

---

# CLI

SecReport exposes two primary commands:

```text
secreport run
secreport gate
```

---

## `secreport run`

Collect, normalize, enrich, score, deduplicate, and report scanner evidence.

```bash
secreport run --input raw-artifacts
```

Full example:

```bash
secreport run \
  --input raw-artifacts \
  --out reports \
  --policy security/risk-policy.yaml \
  --exceptions security/exceptions.yaml \
  --baseline .baseline/baseline.json \
  --repo my-org/my-service \
  --ref main \
  --sha 1234567890abcdef \
  --run-url https://github.com/my-org/my-service/actions/runs/123456 \
  --markdown \
  --sarif \
  --xlsx \
  --pdf
```

### Options

| Option | Default | Description |
|---|---|---|
| `--input` | required | Directory containing scanner evidence |
| `--out` | `reports` | Output directory |
| `--policy` | `security/risk-policy.yaml` | Risk and gate policy |
| `--exceptions` | `security/exceptions.yaml` | Approved risk acceptances |
| `--baseline` | empty | Previous fingerprint baseline |
| `--repo` | `$GITHUB_REPOSITORY` or `local` | Repository name |
| `--ref` | `$GITHUB_REF_NAME` or `local` | Branch or reference |
| `--sha` | `$GITHUB_SHA` or zero SHA | Commit SHA |
| `--run-url` | empty | CI workflow URL |
| `--markdown` | disabled | Generate Markdown summary |
| `--sarif` | disabled | Generate consolidated SARIF |
| `--xlsx` | disabled | Generate Excel workbook |
| `--pdf` | disabled | Generate PDF report |

Regardless of optional report flags, `run` always generates:

```text
findings.json
baseline.json
```

---

## `secreport gate`

Evaluate the decision stored in the canonical results file and return the appropriate process exit code.

```bash
secreport gate
```

Defaults to:

```text
reports/findings.json
```

Explicit example:

```bash
secreport gate \
  --results reports/findings.json \
  --policy security/risk-policy.yaml
```

### Options

| Option | Default | Description |
|---|---|---|
| `--results` | `reports/findings.json` | Canonical SecReport result |
| `--policy` | `security/risk-policy.yaml` | Security policy |

The gate command returns:

```text
0 → PASS
1 → FAIL
```

This separation ensures that reports are still generated when a security policy fails.

---

# Architecture

SecReport processes scanner evidence through several stages.

```text
                         ┌──────────────────────┐
                         │ Security scanners    │
                         └──────────┬───────────┘
                                    │
                         SARIF / JSON / JSONL
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Collection           │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Normalization        │
                         │ → Finding            │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Deduplication        │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
               CISA KEV         FIRST EPSS      Scanner context
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Risk scoring         │
                         └──────────┬───────────┘
                                    │
                         ┌──────────┼──────────┐
                         ▼          ▼          ▼
                     Baseline   Exceptions   AI triage
                         │          │          │
                         └──────────┼──────────┘
                                    ▼
                         ┌──────────────────────┐
                         │ Policy evaluation    │
                         └──────────┬───────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                      Reports              PASS / FAIL
```

---

# Finding Model

Every scanner finding is normalized into the same internal model.

Conceptually:

```python
Finding(
    tool="trivy",
    category="SCA",
    rule_id="CVE-2026-12345",
    title="Vulnerability in urllib3",
    severity="CRITICAL",
    package="urllib3",
    installed_version="2.2.1",
    fixed_version="2.2.3",
    cve="CVE-2026-12345",
)
```

Additional fields are populated during processing:

```text
epss
kev
confirmed_by
risk_score
risk_factors
status
accepted
acceptance
sla_due
triage_note
fingerprint
```

This means downstream policy and reporting code does not need to understand every scanner's native schema.

---

# Supported Security Domains

Findings are normalized into these security categories:

```text
SECRETS
SAST
SCA
IAC
CONTAINER
DAST
CI_SUPPLY_CHAIN
LICENSE
```

Examples:

| Domain | Example tools |
|---|---|
| Secrets | Gitleaks, TruffleHog |
| SAST | Semgrep, CodeQL, Bandit, Opengrep |
| SCA | Trivy, Grype, OSV-Scanner |
| IaC | Checkov, KICS, Conftest, tfsec, Terrascan |
| Container | Hadolint, Dockle, Trivy |
| DAST | OWASP ZAP, Nuclei |
| CI supply chain | zizmor, actionlint, OpenSSF Scorecard |

Any SARIF-compatible scanner can also be consumed by the generic SARIF parser.

---

# SARIF Validation

SecReport's importer is intentionally tolerant.

Malformed scanner evidence should not prevent reporting of valid evidence from other tools.

For environments where scanner execution must be validated before aggregation, use the provided evidence validator:

```bash
python validate_evidence.py raw-artifacts/semgrep.sarif
```

It rejects:

- invalid JSON
- non-SARIF 2.1.0 documents
- SARIF without scanner runs
- runs without result lists
- missing scanner identity
- malformed result objects
- scanner invocations marked as unsuccessful

This separates:

```text
scanner execution validity
```

from:

```text
finding normalization
```

A recommended pipeline is:

```text
Scanner
   │
   ▼
SARIF
   │
   ▼
validate_evidence
   │
   ▼
SecReport
```

---

# Severity Normalization

Different scanners use different severity vocabularies.

SecReport normalizes them to:

```text
CRITICAL
HIGH
MEDIUM
LOW
INFO
```

Examples:

```text
FATAL       → CRITICAL
BLOCKER     → CRITICAL

ERROR       → HIGH
IMPORTANT   → HIGH
MAJOR       → HIGH

WARNING     → MEDIUM
MODERATE    → MEDIUM
WARN        → MEDIUM

MINOR       → LOW
NOTE        → LOW
NEGLIGIBLE  → LOW

INFORMATIONAL → INFO
```

For SARIF rules that provide numeric security severity values, SecReport interprets them similarly to CVSS:

```text
>= 9 → CRITICAL
>= 7 → HIGH
>= 4 → MEDIUM
< 4  → LOW
```

---

# Deduplication

Security scanners often report the same vulnerability independently.

For example:

```text
Trivy  ─┐
Grype  ─┼── CVE-2026-12345 in urllib3
OSV    ─┘
```

SecReport collapses these into one finding.

```text
CVE-2026-12345
Package: urllib3

Confirmed by:
  - Trivy
  - Grype
  - OSV
```

This prevents inflated vulnerability counts while preserving confidence from independent scanner agreement.

The scanner name is deliberately excluded from finding identity.

---

# Stable Fingerprints

Each normalized finding receives a SHA-256-based fingerprint derived from its identity.

The identity includes information such as:

```text
rule
CVE
package
file
```

and intentionally excludes line number.

For example:

```text
product/views.py:42
```

moving to:

```text
product/views.py:59
```

should not make the vulnerability appear new merely because surrounding code changed.

Fingerprints are used for:

- deduplication
- baseline comparison
- new/existing classification
- security debt tracking

---

# Baselines

SecReport supports baselining so existing security debt does not automatically block unrelated development.

Example:

```text
Previous repository state:

35 HIGH findings
```

A developer opens a PR that introduces no new HIGH finding.

Without a baseline:

```text
35 HIGH vulnerabilities → FAIL
```

With a baseline:

```text
35 existing
0 new

→ existing debt remains visible
→ developer introduced no new high-risk issue
```

After every run, SecReport writes:

```text
reports/baseline.json
```

Example:

```json
{
  "generated": "2026-09-28 03:20 UTC",
  "sha": "9f8a7d6c5b4a3210",
  "fingerprints": [
    "072a663b6f883bd4",
    "24163bf571ec3a11",
    "36f215eca01f7552"
  ]
}
```

Use the previous trusted baseline on later runs:

```bash
secreport run \
  --input raw-artifacts \
  --baseline .baseline/baseline.json
```

Findings are classified as:

```text
new
existing
```

---

# Threat Intelligence

SecReport enriches CVE findings with two external sources.

## CISA KEV

The CISA Known Exploited Vulnerabilities catalog identifies vulnerabilities known to be actively exploited.

```text
CVE
 │
 └── KEV = true
```

KEV findings can receive higher contextual risk.

---

## FIRST EPSS

The Exploit Prediction Scoring System estimates the probability that a vulnerability will be exploited in the wild.

Example:

```text
CVE-2026-12345
EPSS = 0.72
```

A HIGH vulnerability with high exploitation probability may therefore be more operationally important than an isolated CRITICAL issue with negligible exploit likelihood.

---

# Intelligence Cache

Threat-intelligence responses are cached under:

```text
.secreport-cache/
├── kev.json
└── epss.csv.gz
```

This provides graceful fallback when public intelligence services are temporarily unavailable.

A transient network failure should not make your reporting pipeline unusable.

---

# Risk Scoring

Raw scanner severity is only one input to SecReport's risk model.

Conceptually:

```text
Contextual Risk =
    Base severity
    × exploit intelligence
    × exposure
    × fix availability
    × scanner confidence
    × dependency context
    × environment context
```

Each finding receives:

```text
risk_score: 0–100
```

and a set of explanatory factors:

```json
{
  "risk_score": 93.5,
  "risk_factors": [
    "base:CRITICAL=90",
    "cisa-kev",
    "epss-high",
    "multi-tool-confirmation"
  ]
}
```

The important distinction is:

```text
Severity
    = how technically serious the vulnerability is

Risk
    = how important the vulnerability is in this specific context
```

---

# Risk Acceptance

Sometimes a vulnerability cannot immediately be fixed or is demonstrated not to be exploitable in the current environment.

SecReport supports explicit, time-boxed exceptions.

Example:

```yaml
exceptions:
  - id: CVE-2026-12345
    reason: Vulnerable code path is unreachable in this deployment.
    owner: platform-team
    approved_by: security-team
    expires: 2026-10-31
```

Risk acceptances should include at least:

```text
id
reason
owner
approved_by
expires
```

Expired exceptions are treated as errors.

This prevents:

```text
temporary suppression
        ↓
forgotten exception
        ↓
permanent untracked risk
```

---

# Optional AI Triage

SecReport can optionally use a local LLM to assist with false-positive analysis.

The LLM's role is advisory.

It may add triage information such as:

```json
{
  "likely_false_positive": true,
  "confidence": 0.91,
  "reason": "The detected value exists only in test fixture data."
}
```

AI triage is deliberately separated from deterministic security policy.

The LLM does not become the authoritative CI decision-maker.

A recommended model is:

```text
Scanners + deterministic policy
              │
              ├── authoritative
              │
Local LLM ────┘
     advisory triage
```

---

# Policy

Security behavior is configured through:

```text
security/risk-policy.yaml
```

A policy can control areas such as:

```text
risk score thresholds
new-finding behavior
severity limits
KEV handling
verified-secret handling
remediation SLAs
risk multipliers
AI triage
```

Conceptual example:

```yaml
gate:
  block_on_new_only: true
  block_above_risk_score: 70

  max_new:
    critical: 0
    high: 0

sla:
  critical: 1
  high: 7
  medium: 30
  low: 90
```

The exact policy fields should remain version-controlled alongside the application or organizational security configuration.

---

# Generated Reports

A full run can produce:

```text
reports/
├── findings.json
├── baseline.json
├── summary.md
├── consolidated.sarif
├── devsecops-report.xlsx
├── devsecops-report.pdf
└── charts/
    ├── chart_severity.png
    └── chart_category.png
```

---

## `findings.json`

The canonical SecReport dataset.

It contains:

```text
metadata
KPIs
gate result
gate reasons
exceptions
normalized findings
risk information
baseline state
enrichment data
```

Example:

```json
{
  "meta": {
    "repo": "my-org/my-service",
    "ref": "main",
    "sha": "9f8a7d6c",
    "generated": "2026-09-28 03:20 UTC"
  },
  "kpis": {
    "total": 18,
    "new": 4,
    "existing": 14,
    "kev": 1
  },
  "gate": {
    "passed": false,
    "reasons": [
      "A new finding exceeds the configured risk threshold."
    ]
  },
  "findings": []
}
```

Use this file as the main machine-readable integration contract.

---

## `baseline.json`

Stores finding fingerprints for future baseline comparison.

This is pipeline state rather than a human-facing security report.

---

## `summary.md`

Compact CI/PR-friendly report containing:

- security verdict
- severity counts
- new findings
- pre-existing findings
- KEV findings
- EPSS information
- fix availability
- gate failure reasons
- prioritized remediation queue

This file is well suited for:

```text
GitHub Actions summaries
PR comments
CI artifacts
developer review
```

---

## `consolidated.sarif`

One normalized SARIF document containing findings from all supported scanners.

Useful for integration with:

- GitHub Code Scanning
- SARIF viewers
- IDE tooling
- security dashboards
- downstream analysis tools

Conceptually:

```text
Semgrep SARIF ───┐
Trivy SARIF ─────┤
Checkov SARIF ───┤
JSON scanners ───┤
                 ▼
              SecReport
                 │
                 ▼
       consolidated.sarif
```

---

## `devsecops-report.xlsx`

Filterable security-analysis workbook.

It includes views such as:

```text
Executive Summary
Findings
Coverage by Tool
SLA Tracker
SBOM
Risk Acceptances
Methodology
```

The workbook is useful for:

- security engineers
- engineering managers
- remediation planning
- audit preparation
- filtering security debt
- reviewing remediation SLAs

---

## `devsecops-report.pdf`

Management and audit-oriented security assessment.

Typical sections include:

```text
Application Security Assessment
Executive Summary
Security Verdict
KPI Summary
Severity Distribution
Category Distribution
Gate Failure Reasons
Priority Remediation Queue
Control Coverage
Security Methodology
Framework Alignment
Risk Acceptance Register
Evidence Provenance
```

The PDF intentionally focuses on decision-making and remediation rather than raw scanner output.

---

# Output Responsibilities

Each report has a different purpose:

| Artifact | Primary purpose |
|---|---|
| `findings.json` | Canonical security data |
| `baseline.json` | Historical finding state |
| `summary.md` | Developer / PR feedback |
| `consolidated.sarif` | Security platform integration |
| `devsecops-report.xlsx` | Detailed analysis and remediation |
| `devsecops-report.pdf` | Management, governance and audit |

---

# SBOM Support

When a compatible SBOM is found in the evidence directory, SecReport can include software-component information in its reports.

The Excel workbook may include fields such as:

```text
Component
Version
Type
License
Package URL
Source
```

This enables vulnerability findings and software inventory to be reviewed together.

---

# CI/CD Usage

A recommended pipeline separates four concepts:

```text
Scan
  ↓
Validate evidence
  ↓
Aggregate and report
  ↓
Enforce gate
```

For example:

```bash
# 1. Security scanners write their evidence.
./run-security-scanners.sh

# 2. Validate scanner execution where required.
python validate_evidence.py raw-artifacts/semgrep.sarif
python validate_evidence.py raw-artifacts/trivy.sarif

# 3. Always generate reports.
secreport run \
  --input raw-artifacts \
  --out reports \
  --policy security/risk-policy.yaml \
  --exceptions security/exceptions.yaml \
  --baseline .baseline/baseline.json \
  --repo "$GITHUB_REPOSITORY" \
  --ref "$GITHUB_REF_NAME" \
  --sha "$GITHUB_SHA" \
  --markdown \
  --sarif \
  --xlsx \
  --pdf

# 4. Enforce centralized security policy.
secreport gate \
  --results reports/findings.json \
  --policy security/risk-policy.yaml
```

The separation is intentional.

`run` always produces evidence.

`gate` decides whether CI passes.

---

# GitHub Actions Example

```yaml
name: Security

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  security:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@<commit-sha>

      - name: Set up Python
        uses: actions/setup-python@<commit-sha>
        with:
          python-version: "3.12"

      - name: Install SecReport
        run: |
          pip install .

      - name: Run scanners
        run: |
          ./scripts/security-scan.sh

      - name: Build security reports
        run: |
          secreport run \
            --input raw-artifacts \
            --out reports \
            --policy security/risk-policy.yaml \
            --exceptions security/exceptions.yaml \
            --baseline .baseline/baseline.json \
            --repo "$GITHUB_REPOSITORY" \
            --ref "$GITHUB_REF_NAME" \
            --sha "$GITHUB_SHA" \
            --run-url "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID" \
            --markdown \
            --sarif \
            --xlsx \
            --pdf

      - name: Publish job summary
        if: always()
        run: |
          cat reports/summary.md >> "$GITHUB_STEP_SUMMARY"

      - name: Upload security reports
        if: always()
        uses: actions/upload-artifact@<commit-sha>
        with:
          name: security-report
          path: reports/

      - name: Enforce security gate
        run: |
          secreport gate \
            --results reports/findings.json \
            --policy security/risk-policy.yaml
```

Notice that reports are uploaded **before** the gate is enforced.

This ensures developers still receive diagnostic evidence when the build fails.

---

# Recommended Repository Layout

For projects consuming SecReport:

```text
project/
├── .github/
│   └── workflows/
│       └── security.yml
│
├── .baseline/
│   └── baseline.json
│
├── security/
│   ├── risk-policy.yaml
│   └── exceptions.yaml
│
├── raw-artifacts/
│   └── ...
│
└── reports/
    └── ...
```

For SecReport itself as a Python package:

```text
secreport/
├── pyproject.toml
├── README.md
├── LICENSE
│
├── src/
│   └── secreport/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── models.py
│       ├── collectors.py
│       ├── parsers/
│       │   ├── sarif.py
│       │   ├── grype.py
│       │   ├── osv.py
│       │   ├── zap.py
│       │   └── nuclei.py
│       ├── enrichment/
│       │   ├── kev.py
│       │   └── epss.py
│       ├── scoring.py
│       ├── baseline.py
│       ├── exceptions.py
│       ├── policy.py
│       ├── triage.py
│       ├── validation.py
│       └── reports/
│           ├── json.py
│           ├── markdown.py
│           ├── sarif.py
│           ├── excel.py
│           └── pdf.py
│
└── tests/
```

A console entry point can expose the CLI:

```toml
[project.scripts]
secreport = "secreport.cli:main"
```

Then users can run:

```bash
secreport run ...
```

instead of:

```bash
python tools/secreport.py run ...
```

---

# Design Principles

## Evidence before decisions

Scanner findings are evidence.

Scanner exit codes should not define organization-wide security policy.

---

## Centralized policy

One component owns the final security decision:

```text
SecReport policy engine
```

This makes the result easier to:

- explain
- test
- version
- review
- audit

---

## Security debt is not new risk

Baselines distinguish:

```text
existing debt
```

from:

```text
newly introduced risk
```

This prevents legacy findings from making security tooling unusable to developers.

---

## Context beats severity alone

A raw CVSS or scanner severity is not enough.

SecReport also considers signals such as:

```text
known exploitation
exploit probability
fix availability
environment
dependency context
multi-tool confirmation
```

---

## Exceptions must expire

Risk acceptance is allowed, but it must be:

```text
explicit
owned
approved
documented
time-boxed
```

---

## Reports must survive a failed gate

Security evidence is most important when the security gate fails.

Therefore:

```text
run → always generate reports

gate → control CI exit code
```

---

## AI is advisory

LLMs may help prioritize and explain findings.

They should not silently replace deterministic security policy.

---

# Security Domains and Methodology

SecReport is designed to aggregate evidence across a broad DevSecOps control surface.

| Control | Example tooling | Purpose |
|---|---|---|
| Secrets | Gitleaks, TruffleHog | Detect exposed credentials |
| SAST | Semgrep, CodeQL | Detect source-code vulnerabilities |
| SCA | Trivy, Grype, OSV-Scanner | Detect vulnerable dependencies |
| SBOM | Syft | Inventory shipped components |
| IaC | Checkov, Trivy config | Detect infrastructure misconfiguration |
| Policy as code | OPA, Conftest | Enforce organizational guardrails |
| Container | Hadolint, Dockle, Trivy | Analyze images and Dockerfiles |
| DAST | OWASP ZAP, Nuclei | Detect runtime vulnerabilities |
| CI supply chain | zizmor, actionlint, Scorecard | Analyze workflow security |
| Artifact integrity | Sigstore, SLSA | Verify build provenance |
| Exploit intelligence | CISA KEV, FIRST EPSS | Prioritize real-world exploitation risk |

SecReport does not need to execute all these tools itself.

Its role is to consume and interpret their evidence.

---

# Framework Alignment

The generated reports can help provide evidence for controls associated with frameworks such as:

```text
NIST SSDF
OWASP SAMM
OWASP ASVS
SLSA
ISO 27001
PCI DSS
software supply-chain requirements
SBOM requirements
```

SecReport should be considered supporting evidence and automation infrastructure rather than a guarantee of regulatory compliance.

---

# Development

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the project:

```bash
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run the CLI locally:

```bash
secreport --help
```

or:

```bash
python -m secreport --help
```

---

# Testing Strategy

Recommended test coverage includes:

```text
severity normalization
path normalization
SARIF parsing
scanner-specific parsers
fingerprint stability
deduplication
KEV enrichment
EPSS enrichment
offline cache behavior
risk scoring
baseline comparison
exception expiration
gate decisions
Markdown generation
SARIF generation
Excel generation
PDF generation
```

Particularly important invariants include:

```text
same finding from two scanners
→ one canonical finding

line-number change
→ same fingerprint

new severe finding
→ gate evaluates according to policy

expired exception
→ no longer suppresses the finding

report generation failure
→ clear diagnostic

network intelligence failure
→ cached/offline behavior remains usable
```

---

# Exit Codes

## `secreport run`

```text
0
```

Report generation and security policy enforcement are deliberately separated.

---

## `secreport gate`

```text
0 → policy passed
1 → policy failed
```

---

# Philosophy

SecReport treats security scanning as a distributed evidence-collection problem followed by a centralized decision problem.

```text
                 Evidence