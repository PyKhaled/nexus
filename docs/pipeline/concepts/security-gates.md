# Security Gates

The starter follows: scanner evidence → evidence validation → normalized report → policy gate.

Trivy is configured to return zero for findings so the report policy makes the risk decision. Tool execution failures still fail the workflow; missing, malformed, or explicitly unsuccessful SARIF is rejected before reporting. A clean scan must contain a valid scanner run with an empty results list.

`secreport run` computes and stores the decision in `reports/findings.json`; it normally returns zero even for blocking findings. `secreport gate` reads that stored decision and returns nonzero when it failed. Its accepted `--policy` argument does not recompute a decision: regenerate the report after changing policy.

The starter policies consider all findings, including the first scan. The inherited engine labels first-scan findings as `baseline`; enabling new-only gating without deliberately managing a baseline can exclude them. See [Risk Policies](../reference/risk-policies.md).

Reports contain sensitive repository metadata and finding details. These templates upload evidence to GitHub Actions artifacts with a 14-day retention period. The engine fetches public KEV/EPSS data; GitHub, package registries, and scanner databases are also contacted. This is not an offline pipeline.

The starter covers vulnerabilities and misconfigurations through Trivy, not all secrets, SAST, DAST, licensing, or supply-chain threats. Passing the gate means the configured policy accepted the collected evidence, not that the application is secure.

## Rollout model

Introduce a new gate in observe-only mode on a representative repository. Track
runtime, false positives, missing evidence, and recurring exceptions before
enforcement. Assign exception owners and expiry dates, then enable blocking for
new findings before expanding repository by repository.

Review scanner pins, baseline behavior, permissions, artifact retention, and
recovery procedures on a schedule. A gate should become required only after its
evidence and failure modes are understandable to the teams that must respond.

See the [Implementation Guide](../implementation-guide.md) for the staged
adoption sequence and [Evidence Contracts](../reference/evidence-contracts.md)
for the proposed multi-scanner boundary.
