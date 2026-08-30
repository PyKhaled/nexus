# Nexus GitHub Work Index

Status: Published as GitHub issues #16–#30 on 2026-08-30.

Prepared: 2026-08-30

## Purpose

This document records the scoped drafts used to publish Nexus issues #16–#30.
It is a publication-time source archive, not a live backlog, a commitment, or a
description of current implementation. Each linked GitHub issue is
authoritative for its current open/closed state.

The drafts were collected from:

- `product-system.yaml` missing capabilities and unassigned ownership;
- `composition/README.md` proposed modes, future policies, and known gaps;
- component README known-gap tables and runbook indexes;
- `docs/architecture/product-system-profile.md`, `docs/compose/README.md`, and
  `ONBOARDING.md`;
- the dated takeover evidence package;
- GitHub issues #2, #3, #4, and #6 and their merged pull requests.

Before publication, all existing Nexus GitHub issues were closed. The new
issues preserve still-relevant unchecked work without reopening or duplicating
completed implementation.

## Published issues

| ID | GitHub issue | Priority | Depends on |
| --- | --- | --- | --- |
| PW-01 | [#16 — Confirm accountable ownership and lifecycle](https://github.com/PyKhaled/Nexus/issues/16) | P0 | — |
| PW-02 | [#17 — Publish a fresh commit-bound engineering baseline](https://github.com/PyKhaled/Nexus/issues/17) | P0 | #16 for approval claims only |
| PW-03 | [#18 — Run Nexus validation continuously in CI](https://github.com/PyKhaled/Nexus/issues/18) | P0 | — |
| PW-04 | [#19 — Make Assembler package validation tamper-evident](https://github.com/PyKhaled/Nexus/issues/19) | P0 | — |
| PW-05 | [#20 — Add declarative compatibility and lifecycle metadata](https://github.com/PyKhaled/Nexus/issues/20) | P1 | #19 |
| PW-06 | [#21 — Define Assembler distribution and operator-facing CLI workflows](https://github.com/PyKhaled/Nexus/issues/21) | P1 | #19 |
| PW-07 | [#22 — Implement test and CI deployment modes](https://github.com/PyKhaled/Nexus/issues/22) | P1 | #20 |
| PW-08 | [#23 — Implement isolated preview/PR deployments](https://github.com/PyKhaled/Nexus/issues/23) | P1 | #20, #22 |
| PW-09 | [#24 — Implement staging and managed-container deployment targets](https://github.com/PyKhaled/Nexus/issues/24) | P1 | #20, #22 |
| PW-10 | [#25 — Add a full integration-development blueprint](https://github.com/PyKhaled/Nexus/issues/25) | P2 | #20 |
| PW-11 | [#26 — Harden Overseer access before non-local use](https://github.com/PyKhaled/Nexus/issues/26) | P0 | #20 |
| PW-12 | [#27 — Make the service-status capability durable and operable](https://github.com/PyKhaled/Nexus/issues/27) | P1 | #16 for owner assignment |
| PW-13 | [#28 — Establish the minimum operational runbook set](https://github.com/PyKhaled/Nexus/issues/28) | P1 | #16 |
| PW-14 | [#29 — Decide the product capability roadmap and reserved API boundary](https://github.com/PyKhaled/Nexus/issues/29) | P1 | #16 |
| PW-15 | [#30 — Reconcile documentation with merged behavior and issue state](https://github.com/PyKhaled/Nexus/issues/30) | P1 | #17 |

---

## PW-01 — Confirm accountable Nexus ownership and lifecycle

Suggested title: `Governance: confirm accountable Nexus ownership and lifecycle`

Suggested labels: `documentation`, `governance`

### Context

`product-system.yaml` records the product owner and every capability owner as
`unassigned`, while the takeover evidence records ownership and decision
authority as Unknown. Contributor identity and repository activity are not
sufficient evidence of accountability.

### Scope

- Identify the accountable product owner and technical decision authority.
- Confirm the intended lifecycle: experiment, maintained internal system,
  supported product, or another explicitly defined state.
- Define who accepts security and operational risk.
- Record escalation and review responsibilities for each current capability.
- Update the authoritative repository metadata and governance links.

### Acceptance criteria

- [ ] `product-system.yaml` names the confirmed product owner and lifecycle.
- [ ] Each current capability has an accountable owner or an explicit shared
      ownership rule.
- [ ] Security, release, and operational decision authority is documented.
- [ ] The confirmation is linked to an authoritative governance or project
      record.
- [ ] No ownership is inferred solely from Git history or repository access.

### Out of scope

- Assigning delivery dates or declaring production readiness.
- Treating the person who performs the repository update as the owner by
  default.

### Source

`product-system.yaml`; deleted takeover baseline findings FND-007 and GAP-003.

---

## PW-02 — Publish a fresh commit-bound engineering baseline

Suggested title: `Audit: publish a fresh commit-bound Nexus engineering baseline`

Suggested labels: `documentation`

### Context

The product profile still says the current implementation requires fresh
verification. The previous takeover baseline is dated 2026-08-27 and bound to
an older commit. Closed issue #6 defined a useful audit boundary, but its
acceptance checklist remains unchecked in the GitHub issue body.

### Scope

- Record the exact `main` commit and clean-worktree boundary being verified.
- Run the Assembler, CLI, and repository-manager test suites.
- Validate required source-repository declarations for applicable blueprints.
- Plan, assemble, and validate development, self-hosted production, and
  high-assurance examples.
- Validate the active root Compose definition and build owned images.
- Start the supported local system and verify health, routes, logs,
  persistence, and reset behavior.
- Record commands, expected results, observed results, failures, and evidence.
- Separate local evidence from production, security, recovery, and approval
  claims.

### Acceptance criteria

- [ ] The audit identifies the exact verified commit, date, and environment.
- [ ] Every check is recorded as Pass, Fail, Blocked, or Not run.
- [ ] Root Compose configuration and all documented example blueprints are
      covered.
- [ ] Gateway health and documented routes are verified or recorded as gaps.
- [ ] Persistence and reset behavior are verified for representative stateful
      stacks or explicitly deferred.
- [ ] External host, secrets, artifact, backup, and audit controls are not
      implied by Compose validation.
- [ ] The product-system profile and documentation index link to the result.
- [ ] Follow-up defects and risks are linked as separate issues.

### Out of scope

- Certifying production readiness from local Docker validation.
- Recreating historical evidence as if it applies to a newer commit.

### Source

Closed issue #6; `docs/architecture/product-system-profile.md`; dated takeover
assurance backlog and evidence register.

---

## PW-03 — Run Nexus validation continuously in CI

Suggested title: `CI: run Nexus composition and configuration validation on every change`

Suggested labels: `enhancement`

### Context

The repository documents local verification commands, but no root CI workflow
currently retains evidence for the Nexus Assembler, root Compose definition,
or gateway configuration. The service scaffold contains example pipeline
files, but they do not validate Nexus itself.

### Scope

- Add a repository CI workflow for relevant pushes and pull requests.
- Run the complete Assembler, CLI, and repository-manager tests.
- Validate `docker compose config` for the root definition.
- Run gateway configuration validation.
- Plan, assemble, and validate every checked-in example blueprint.
- Retain concise failure output and generated policy/evidence reports where
  useful.
- Document required local equivalents and path-based trigger behavior.

### Acceptance criteria

- [ ] A pull request changing Nexus code, composition data, or gateway config
      runs the applicable checks automatically.
- [ ] All three Ruby test suites run in CI.
- [ ] Root Compose and every checked-in example blueprint are validated.
- [ ] Failures identify the command and affected blueprint or component.
- [ ] The workflow does not require production secrets.
- [ ] Branch-protection requirements are documented separately from workflow
      presence.

### Out of scope

- Claiming runtime or production readiness from static CI validation.
- Publishing images or deploying environments.

### Source

Closed issue #4 acceptance criteria; `ONBOARDING.md`; deleted takeover
assurance plan.

---

## PW-04 — Make Assembler package validation tamper-evident

Suggested title: `Security: make Nexus Assembler validation tamper-evident`

Suggested labels: `enhancement`, `security`

### Context

`bin/nexus validate` checks blueprint digest and locked image references, but
does not reassemble the blueprint and rerun policy checks against all assembled
content. A security-relevant edit can therefore be evaluated against stale
evidence. This is the primary unresolved integrity item from closed issue #4.

### Scope

- Define a canonical composition intermediate representation used by assembly
  and validation.
- Digest all material inputs and outputs: normalized blueprint, catalog data,
  fragments, copied assets, generated Compose, build plan, policy report, and
  relevant tool/policy versions.
- Reassemble or equivalently recompile during validation.
- Rerun policies and compare generated content with the recorded evidence.
- Add negative tests for Compose, asset, lock, and policy-report tampering.
- Define backward-compatibility behavior for existing generated packages.

### Acceptance criteria

- [ ] A security-relevant change to assembled Compose causes validation to
      fail.
- [ ] Changes to copied runtime assets or policy inputs cause validation to
      fail.
- [ ] Validation reruns current policy evaluation through the same compiler
      path used by assembly.
- [ ] The lock identifies exact material inputs, outputs, and tool/policy
      versions.
- [ ] Deterministic development, production, and high-assurance examples still
      pass.
- [ ] Negative tampering tests run in the normal test suite and CI.

### Out of scope

- Host hardening, registry admission, external secret injection, backup, or
  independent audit enforcement.

### Source

`composition/README.md` known gaps; closed issue #4 and merged PR #5.

---

## PW-05 — Add declarative compatibility and lifecycle metadata

Suggested title: `Composition: add declarative compatibility, dependency, and state-lifecycle policies`

Suggested labels: `enhancement`

### Context

Catalog entries do not declare generic environment, target, or assurance
compatibility; capability dependencies and conflicts; or state lifecycle.
Future deployment modes and operational layers need these declarations without
hard-coded component-name branches.

### Scope

- Extend catalog schemas with generic compatibility rules.
- Model required and optional dependencies plus conflicts.
- Classify components and their ephemeral or persistent state.
- Make environment, target, and assurance declarations authoritative.
- Add policies that reject incompatible selections.
- Reject unsafe host-control mounts outside explicitly allowed scopes.
- Require disposable state and cleanup rules for test, CI, and preview.
- Update examples, documentation, and schema/negative tests.

### Acceptance criteria

- [ ] Compatibility and lifecycle decisions come from checked-in data rather
      than literal capability names.
- [ ] Incompatible environment, target, and assurance selections fail planning.
- [ ] Missing dependencies and declared conflicts fail with actionable output.
- [ ] Persistent versus disposable state is represented and policy-tested.
- [ ] Docker-socket-equivalent access is rejected outside an explicit allowed
      scope.
- [ ] Existing checked-in blueprints remain deterministic and valid.

### Out of scope

- Adding every proposed deployment mode in the same pull request.
- Encoding provider-specific product logic in the generic Assembler.

### Source

`composition/README.md` “Assembler evolution,” future policies, and known
gaps; `docs/architecture/product-system-profile.md`.

---

## PW-06 — Define Assembler distribution and operator-facing CLI workflows

Suggested title: `Tooling: define Nexus Assembler distribution and missing CLI workflows`

Suggested labels: `enhancement`

### Context

Nexus Assembler is a repository-local Ruby executable and cannot be installed
or version-pinned independently. Operators also lack catalog discovery,
blueprint configuration, explanation, and package comparison workflows.

### Scope

- Decide and document whether the supported delivery is repository-local,
  packaged as a Ruby gem, or built as a standalone artifact.
- Define versioning and compatibility for blueprints, locks, and policies.
- If external distribution is selected, implement an installable, reproducible
  artifact and release checks.
- Design the minimum useful `list`, `explain`, `configure`, and `diff`
  workflows; implement only commands whose user and output contract is clear.
- Document machine-readable output and exit-code stability.

### Acceptance criteria

- [ ] The supported delivery model and rationale are recorded in an ADR or
      equivalent decision.
- [ ] Installation, invocation, version reporting, and upgrade behavior are
      documented for the selected model.
- [ ] Each added command has help text, structured output where appropriate,
      tests, and failure semantics.
- [ ] Package/lock compatibility rules are explicit.
- [ ] No new command silently fetches repositories or overwrites operator data.

### Out of scope

- Building all four candidate commands before their workflows are validated.
- Making the Assembler a general-purpose orchestration platform.

### Source

`composition/README.md` known gaps; closed issue #4.

---

## PW-07 — Implement test and CI deployment modes

Suggested title: `Composition: implement disposable test and CI deployment modes`

Suggested labels: `enhancement`

### Context

Test and CI are documented deployment outcomes but are not implemented as
Assembler environment and target data. They need disposable state, predictable
exit behavior, and report handling.

### Scope

- Add a `test` environment and `ci` target.
- Define disposable database/cache lifecycle and explicit test-runner roles.
- Define exit-code propagation, logs, and report artifacts.
- Prevent production credentials and durable state from entering these modes.
- Add local-test and CI example blueprints.
- Add planning, assembly, validation, policy, and negative tests.

### Acceptance criteria

- [ ] Local-test and CI blueprints assemble deterministically.
- [ ] Test completion produces a reliable process exit status.
- [ ] State is disposable by default and cleanup behavior is documented.
- [ ] Production credentials and shared durable volumes are rejected.
- [ ] Reports can be retained by CI without retaining secrets.
- [ ] Both examples pass Compose and Assembler validation in CI.

### Out of scope

- Preview, staging, or production deployment behavior.
- Inventing integration dependencies that no selected test exercises.

### Source

`composition/README.md` deployment catalog and future policies;
`docs/architecture/product-system-profile.md`.

---

## PW-08 — Implement isolated preview/PR deployments

Suggested title: `Composition: implement isolated and expiring preview deployments`

Suggested labels: `enhancement`

### Context

Preview/PR is a documented design target but has no supported environment,
blueprint, isolation policy, or cleanup behavior.

### Scope

- Add a `preview` environment for a supported target.
- Require prebuilt candidate images and prohibit source mounts.
- Model unique namespace, hostname, secret, and data isolation.
- Define bounded credentials and least-privilege access.
- Define expiry, cleanup, and failure-recovery behavior.
- Add an example blueprint, policies, negative tests, and operator handoff.

### Acceptance criteria

- [ ] Two preview packages can coexist without names, routes, volumes, or
      credentials colliding.
- [ ] Preview packages use prebuilt candidate images.
- [ ] Secrets are isolated and bounded to one preview.
- [ ] State is disposable by default.
- [ ] Expiry and idempotent cleanup are documented and testable.
- [ ] Missing namespace, secret, or cleanup isolation fails policy evaluation.

### Out of scope

- Selecting a hosting provider without an explicit target decision.
- Treating preview as a production durability environment.

### Source

`composition/README.md` deployment catalog and future policies;
`docs/architecture/product-system-profile.md`.

---

## PW-09 — Implement staging and managed-container targets

Suggested title: `Composition: implement staging and managed-container deployment support`

Suggested labels: `enhancement`

### Context

Self-hosted staging and managed production are documented outcomes but remain
unsupported. Their external data, ingress, secrets, storage, and image
contracts differ from the current self-hosted target.

### Scope

- Add a `staging` environment with production-like immutable application
  images and real integrations but no source mounts.
- Add a `managed-container` target with explicit external-service contracts.
- Model external database, cache, storage, email, secrets, and ingress
  requirements without pretending to provision them.
- Add representative staging and managed-production blueprints.
- Extend policies, operator handoff, tests, and external-control warnings.

### Acceptance criteria

- [ ] Staging and managed-production packages assemble deterministically.
- [ ] Both modes use prebuilt immutable application images.
- [ ] External dependencies are explicit contracts, not silently created local
      containers.
- [ ] Source mounts and development secret defaults are rejected.
- [ ] Operator documentation separates package guarantees from platform-owned
      controls.
- [ ] Examples pass Assembler and configuration validation.

### Out of scope

- Provisioning a particular cloud platform.
- Claiming that generated packages implement host, backup, audit, or admission
  controls.

### Source

`composition/README.md` deployment catalog; product-system profile proposed
environments and targets.

---

## PW-10 — Add a full integration-development blueprint

Suggested title: `Composition: add an explicit full integration-development blueprint`

Suggested labels: `enhancement`

### Context

The documentation distinguishes lightweight development from full integration
development, but only the lightweight development blueprint is implemented.
Supporting databases, caches, mail sandboxes, observability, and engineering
tools should be selected only when a component or test declares a need.

### Scope

- Define the intended integration-development users and workflows.
- Add explicit optional operational-layer catalog entries where justified.
- Declare component dependencies rather than selecting services for visual
  topology parity.
- Keep databases, caches, and tools private to the Compose network.
- Add a checked-in blueprint, documentation, and deterministic tests.

### Acceptance criteria

- [ ] The blueprint names the integration workflows it enables.
- [ ] Every supporting service has a declared consumer.
- [ ] Database, Redis, mail, and admin surfaces publish no host ports unless a
      reviewed gateway route is explicitly required.
- [ ] Production credentials cannot be consumed by development-only tools.
- [ ] The blueprint assembles and validates deterministically.

### Out of scope

- Adding operational tools without a concrete workflow.
- Turning “full development” into a second independently maintained Compose
  source of truth.

### Source

`composition/README.md` deployment catalog and optional operational layers.

---

## PW-11 — Harden Overseer access before non-local use

Suggested title: `Security: authenticate and isolate Overseer before non-local use`

Suggested labels: `enhancement`, `security`

### Context

Overseer has no built-in authentication and mounts the host Docker socket with
administrative power. It is intentionally development-only. A production-auth
overlay is drafted in the component README but not implemented, and the socket
remains host-wide.

### Scope

- Threat-model the dashboard, lifecycle API, gateway route, OAuth flow, and
  Docker-socket boundary.
- Implement an authenticated TLS overlay using a separate OIDC client and
  session from the API route.
- Preserve CSRF protections end to end.
- Evaluate a socket proxy or other least-privilege isolation mechanism.
- Add policy metadata preventing unsafe selection outside trusted local use.
- Add route, authentication, authorization, and negative-access tests.
- Define the conditions—if any—for a production/hardened blueprint.

### Acceptance criteria

- [ ] Unauthenticated requests cannot reach the dashboard or lifecycle API in
      the protected mode.
- [ ] The Overseer OIDC client, redirect URL, and cookie secret are separate
      from other protected routes.
- [ ] TLS and CSRF behavior are tested.
- [ ] Docker access is reduced to the smallest practical boundary, or the
      residual host-wide risk is explicitly rejected for non-local use.
- [ ] Assembler policies reject Overseer in incompatible deployment shapes.
- [ ] A compromised-socket incident runbook exists and has been reviewed.

### Out of scope

- Describing authentication alone as sufficient socket isolation.
- Enabling Overseer in production before the acceptance criteria pass.

### Source

`system/system-overseer/README.md`; Overseer runbook index; merged PR #10
unchecked follow-up.

---

## PW-12 — Make the service-status capability durable and operable

Suggested title: `Operations: make Nexus service status durable and production-capable`

Suggested labels: `enhancement`

### Context

Kener works as a local reference stack, but first-run setup and monitor
assignment are manual; subscriber email is not configured; local-only probing
cannot detect a full host outage; SQLite is not the selected shared-deployment
topology; and backup, restore, retention, export, and upgrade procedures are
missing.

### Scope

- Decide whether supported initialization can be automated; otherwise define
  a reproducible first-run procedure.
- Create and verify the gateway, website, and authentication monitors.
- Demonstrate that a monitored outage appears correctly on the public page.
- Configure and test subscriber email for an approved environment.
- Define an external-probe topology for whole-site outages.
- Define the production database topology, including PostgreSQL migration if
  selected.
- Write and exercise backup, restore, retention, export/recovery, Redis
  troubleshooting, and upgrade/rollback procedures.

### Acceptance criteria

- [ ] A new supported environment obtains the required initial monitors
      reproducibly.
- [ ] A representative service outage is visible on the status page.
- [ ] Subscriber delivery succeeds in the intended environment or is explicitly
      deferred with a recorded decision.
- [ ] External probing detects gateway or host failure independently of Nexus.
- [ ] The supported production data topology and migration boundary are
      documented.
- [ ] Backup and restore are exercised against named, bounded data stores.
- [ ] Upgrade, rollback, retention, and recovery procedures are linked from the
      runbook index.

### Out of scope

- Claiming availability of the status page when it shares the failed host.
- Replacing Kener without a separate implementation decision.

### Source

`system/system-status/README.md`; status runbook index; merged PR #9 unchecked
manual checks.

---

## PW-13 — Establish the minimum operational runbook set

Suggested title: `Operations: establish and exercise the minimum Nexus runbook set`

Suggested labels: `documentation`

### Context

Nexus has a clear runbook ownership and discovery model, but most service
directories contain indexes rather than executable procedures. Index presence
does not establish operational coverage.

### Scope

- Prioritize failure and recovery scenarios by impact and likelihood.
- Add gateway deployment/reload, certificate rotation, and upstream-failure
  procedures.
- Add Keycloak realm/client administration, credential rotation, database
  backup/restore, upgrade, and authentication-incident procedures.
- Add WordPress maintenance, database backup/restore, plugin/theme failure,
  upgrade, and incident procedures.
- Add Overseer socket-exposure response and upgrade/rollback procedures.
- Coordinate status-specific procedures with PW-12 rather than duplicating
  them.
- Review or exercise each priority procedure and retain bounded evidence.

### Acceptance criteria

- [ ] Each current service or stack has at least one prioritized, concrete
      operational procedure.
- [ ] Every runbook names environment, prerequisites, safety boundary,
      verification, rollback, and escalation.
- [ ] Destructive recovery procedures identify exact resources and require a
      verified backup.
- [ ] Each runbook is linked from its owning index and central discovery index.
- [ ] Review or exercise evidence is dated and identifies the tested revision
      and environment.
- [ ] Unexecuted procedures are not described as validated.

### Out of scope

- Filling directories with unreviewed template copies.
- Treating local walkthroughs as proof of production readiness.

### Source

`docs/runbooks/README.md`; all service-local runbook indexes; deleted takeover
baseline gap R-002.

---

## PW-14 — Decide the product capability roadmap and reserved API boundary

Suggested title: `Product: decide the missing capability roadmap and reserved API boundary`

Suggested labels: `enhancement`

### Context

The product manifest lists help center, notifications, client experience,
administration, business domain, and integration manager as missing. The
gateway reserves `api.localhost`, while `system-service` is a scaffold rather
than a runnable Nexus API. These entries are vocabulary, not approved product
commitments.

### Scope

- Identify intended users and outcomes for each missing capability.
- Decide whether each capability belongs in Nexus, another product, or the
  reusable Engineering OS vocabulary only.
- Define ownership, interfaces, data boundaries, and acceptance measures for
  accepted candidates.
- Decide whether `api.localhost` should remain reserved, be backed by an
  approved service, or be removed until needed.
- Decide whether `system-service` is a maintained template, a future Nexus
  component, or an extraction candidate.
- Create separate implementation issues only for approved capabilities.

### Acceptance criteria

- [ ] Every missing manifest capability is marked accepted for discovery,
      deferred, moved, or removed with rationale.
- [ ] Accepted capabilities identify a user, outcome, owner, boundary, and
      measurable acceptance criteria.
- [ ] The reserved API route and service scaffold have an explicit documented
      disposition.
- [ ] `product-system.yaml`, architecture documentation, and gateway behavior
      agree.
- [ ] No placeholder implementation is created solely to satisfy the manifest.

### Out of scope

- Implementing all missing capabilities in one issue.
- Treating vocabulary imported from Engineering OS as a Nexus commitment.

### Source

`product-system.yaml`; product-system profile planned-capability boundary;
`ONBOARDING.md`; `docs/compose/README.md`.

---

## PW-15 — Reconcile documentation with merged behavior and issue state

Suggested title: `Docs: reconcile Nexus documentation with merged behavior and GitHub state`

Suggested labels: `documentation`

### Context

Several pages still point to closed issues as planned work, `ONBOARDING.md`
says issue #6 is open, and `docs/compose/README.md` contains an explicit review
TODO. These inconsistencies make it difficult to tell current behavior from
backlog.

### Scope

- Reconcile the root README, documentation index, product-system profile,
  composition guide, Compose-mode guide, and onboarding guide.
- Remove or replace stale open/closed issue claims.
- Confirm that the documentation-index link to the dated takeover package
  remains intentional and accurately bounded.
- Review the Compose-mode guide from its TODO marker through the end.
- Ensure current capability states match `product-system.yaml`, root Compose,
  catalog data, and merged behavior.
- Link the newly published GitHub issues once their final numbers exist.

### Acceptance criteria

- [ ] No page describes a closed issue as the current open backlog.
- [ ] Documentation-index links resolve and describe their evidence boundary.
- [ ] Current behavior and proposed work are visibly separated.
- [ ] Capability names and states agree across the manifest, catalog, Compose,
      architecture profile, and onboarding guide.
- [ ] The Compose-mode TODO is removed after review.
- [ ] Relevant Markdown links and documented commands are validated.

### Out of scope

- Rewriting the dated takeover package as if it were current evidence.
- Updating docs to describe an unmerged proposal as current behavior.

### Source

`docs/README.md`; `docs/architecture/product-system-profile.md`;
`docs/compose/README.md`; `ONBOARDING.md`; current GitHub issue state.

---

## Publication notes

- Each draft was published as a separate issue.
- Dependencies use the assigned GitHub issue numbers.
- Only existing repository labels were applied: `documentation` or
  `enhancement`.
- Source paragraphs remain in each issue body for traceability.
- Issues should be closed or narrowed when repository evidence shows the work
  is already complete; backlog is not preserved for its own sake.
