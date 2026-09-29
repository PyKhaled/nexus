# Delivery Architecture

The delivery system separates fast repository feedback, security evidence,
policy decisions, release distribution, and environment deployment. This keeps
permissions and failure ownership narrow while allowing each layer to evolve.

## Workflow surfaces

| Surface | Responsibility | Typical trigger | Primary output | Current state |
| --- | --- | --- | --- | --- |
| Repository CI | Quality checks and project tests | Push or pull request | Required status checks | Node, Django, and Laravel starters |
| Security workflow | Evidence production and policy evaluation | Push, pull request, or manual run | Verdict and reports | Trivy starter with SecReport |
| Release workflow | Build, provenance, and distribution | Approved release request | Immutable artifact references | Container publishing only |
| Policy configuration | Thresholds, exceptions, and context | Reviewed configuration change | Versioned decision contract | Risk and release policies |
| Deployment workflow | Environment rollout and verification | Approved artifact promotion | Deployment and runtime evidence | Devtron request example only |

## Dependency model

1. A code change starts repository CI and the applicable security workflow.
2. Independent CI jobs report quality and test results without publishing.
3. Security producers emit evidence without deciding the final outcome.
4. One gate validates coverage and applies the reviewed policy.
5. Only a reviewed commit with required checks should enter release processing.
6. Release jobs build and publish immutable artifacts from that same commit.
7. Deployment promotes an immutable artifact and records environment-specific
   approval, rollout, and runtime verification separately.

The current starter does not automatically verify required CI checks before a
manual publish. Repository rules and operator review must enforce that boundary.

## Core properties

### Evidence before policy

Scanners produce facts in documented formats. The gate validates those inputs
and makes the decision once. This prevents individual scanners from applying
inconsistent thresholds.

### Fail closed on required coverage

An enabled, required evidence class must produce valid output or an explicit
failure. Missing output cannot be interpreted as zero findings. The current
starter validates its Trivy SARIF; broader coverage validation is target
architecture.

### Build once

Scan, test, and publish the same artifact whenever practical. The current
scan-gated container template builds one local image, scans it, and pushes that
same image. Future DAST and release workflows should preserve the same identity
through digests and checksums.

### Least privilege

Keep top-level workflow permissions empty and grant access per job. Registry
write access belongs only to publishing jobs. Release-record and pull-request
write access should likewise be limited to the jobs that use them.

### Deployment remains separate

Release evidence establishes what was built and distributed. Deployment must
add environment approvals, secret boundaries, rollout checks, rollback, and
post-deployment verification. A published image is not deployment evidence.

## Repository profiles

Application repositories normally need code, dependency, configuration, and
possibly container and DAST evidence. Library repositories emphasize package
provenance and consumer compatibility. Infrastructure repositories emphasize
configuration, policy, secrets, and plan evidence. Each repository should
declare which evidence classes apply instead of silently omitting them.

See [Choosing a Pipeline](../choosing-a-pipeline.md) for adoption guidance and
[Evidence Contracts](../reference/evidence-contracts.md) for proposed artifact
boundaries.
