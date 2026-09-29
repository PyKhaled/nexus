# Pipeline Implementation Guide

Build the delivery system in stages. Each stage should produce a reviewable
contract or observable result before the next layer becomes blocking.

The current templates provide stack-specific CI, Trivy filesystem and image
scanning, SecReport policy evaluation, manual container publishing, and an
optional deployment request. Multi-scanner fan-out, DAST, provenance, and a
general release workflow remain target architecture.

## 1. Define the decision contract

Document protected branches and release inputs, required evidence, severity
thresholds, baseline behavior, exception expiry, and override ownership. Decide
which events observe findings and which events enforce them.

Definition of done: each required evidence class maps to a reviewed pass or
fail rule.

Avoid selecting scanners before the team agrees on the policy they serve.

## 2. Establish deterministic CI

Pin runtime versions, install from lock files, and run quality and test jobs
with minimal permissions. Add job timeouts and cancel superseded pull-request
runs where that does not discard protected-branch evidence.

The templates under `templates/workflows/ci/` provide the current starting
point for Node, Django, and Laravel.

Definition of done: a clean checkout produces repeatable checks, and an
intentional test failure makes the expected job fail.

Avoid one serial job that hides ownership and gives unrelated steps the same
privileges.

## 3. Centralize preflight routing

Before introducing change-aware scanners, define and validate workflow inputs,
comparison bases, and file classifications. Emit explicit flags for code,
dependencies, configuration, and container changes. If the comparison base is
unavailable or untrusted, scan all applicable files.

Status: target architecture. The starter workflows do not yet provide a shared
preflight job.

Definition of done: every conditional job has a documented input and a safe
fallback.

Avoid scattering unrelated path filters across scanner jobs.

## 4. Fan out evidence producers

Run independent scanners in parallel and give each producer a stable artifact
contract. Findings are evidence; a scanner should not make the final policy
decision. Preserve evidence on findings and diagnosable scanner failures while
still recording whether the scanner completed successfully.

The current starter produces Trivy SARIF. Additional secret, SAST, SCA, SBOM,
configuration, container-hardening, CI-supply-chain, and DAST producers are
future additions. See [Evidence Contracts](reference/evidence-contracts.md).

Definition of done: every enabled producer emits its named artifact or an
explicit failure record.

Avoid treating a missing artifact as a clean scan.

## 5. Apply policy once

Collect evidence in an always-running gate, validate required inputs, normalize
findings, apply exceptions and baseline rules, and store one verdict. Reports,
pull-request summaries, and required checks must consume the same stored
decision.

The current Trivy workflow follows this shape with evidence validation,
`secreport run`, and `secreport gate`. It does not yet enforce coverage across a
multi-scanner suite.

Definition of done: malformed or missing required evidence fails, findings
produce one reproducible verdict, and reports remain available after failure.

Avoid recalculating policy separately while rendering reports.

## 6. Preserve image identity through DAST

Build the image without registry credentials, scan it, generate its SBOM, and
export that exact image for runtime testing. A DAST job should load the exported
artifact rather than rebuild from source. Restrict targets to an approved local
or ephemeral environment, use throwaway settings, and always tear it down.

Status: target architecture. The scan-gated publishing template already pushes
the same local image it scanned, but it does not export the image to DAST.

Definition of done: the digest tested dynamically matches the container
evidence and teardown succeeds after passing or failing scans.

Avoid rebuilding in the DAST job.

## 7. Build an immutable release path

Accept only an approved release input, verify the selected commit passed its
required checks, and build every distribution artifact from that source.
Generate checksums and provenance, smoke-test optional images, and grant write
permissions only to publication jobs. Publication should verify and attach
existing artifacts rather than rebuild them.

Status: partial. The current container templates publish a full commit-SHA tag,
but they do not create general release records, attestations, or provenance.

Definition of done: one approved commit maps to checksummed artifacts, image
digests where applicable, and a release record.

Avoid floating references and publication-time rebuilds.

## 8. Roll out gradually

Pilot the pipeline in observe-only mode on a representative repository. Measure
runtime, false positives, missing evidence, and recurring exceptions. Assign
owners and expiry dates, then enforce new findings before expanding to more
repositories. Review pins, baselines, permissions, and recovery procedures on a
schedule.

Definition of done: required gates are understandable, exceptions expire, and
teams can diagnose failures within an acceptable feedback time.

Avoid organization-wide enforcement before a pilot demonstrates signal quality
and operational ownership.

## Verification boundary

Static validation proves that files parse and repository contracts are
internally consistent. It does not prove successful hosted runs, scanner
coverage, registry publication, deployment, or runtime behavior. Capture those
results separately in the adopting repository.
