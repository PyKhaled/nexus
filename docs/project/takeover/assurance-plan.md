# Nexus Takeover Assurance Plan

## Purpose

Refresh the Nexus baseline when authoritative sources change and keep stale or
unexecuted evidence from appearing as approval or readiness.

## Assurance boundary

This plan defines candidate checks and evidence handling. It does not claim
that the checks currently run in CI, pass on every environment, or cover
external production controls.

## Review triggers

Review affected baseline claims after changes to:

- `compose.yml`, `product-system.yaml`, `composition/`, or
  `tools/nexus_assembler/`;
- component images, routes, environment contracts, private services, or
  persistent volumes;
- architecture profiles or accepted decisions;
- environment, target, assurance, or capability definitions;
- tests, policy checks, build or release behavior;
- secrets boundaries, image provenance, host controls, backup, recovery, or
  observability;
- service-local runbooks or the central runbook index;
- product ownership, lifecycle, or deployment scope.

## Candidate verification sequence

Run only in an authorized environment and preserve the exact revision,
blueprint, command, result, and limitations.

| Check | Command or evidence | Claim it can support | It does not prove |
| --- | --- | --- | --- |
| Assembler and CLI behavior | `make assembler-test` | Test suites pass for the inspected revision | Runtime deployment or external controls |
| Source-repository declaration | `bin/nexus repository validate --blueprint FILE` | Declared required repositories match local submodule and Gitlink state | Remote availability or future repository revisions |
| Blueprint resolution | `make blueprint-plan` | A blueprint resolves and reports its policies | Deployment package deployability |
| Package assembly | `make assemble` | Expected artifacts are assembled locally | Production use or approval |
| Package validation | `make deployment-validate` | Assembled structure and configured validation checks pass | Host hardening, external secrets, backup, audit, or recovery |
| Gateway configuration | `make gateway-test` | Generated NGINX configuration validates in the selected local context | Upstream health or end-to-end behavior |
| Development smoke check | `make up`, then the documented health and endpoint checks | The selected local stack starts and responds during the observation window | Production readiness or durability |
| Runbook review | Written procedure plus recorded walkthrough or exercise | The reviewed scenario has bounded procedure evidence | Complete operational coverage |

Generated output under `generated/` is local scratch evidence unless a
separate, reviewed process intentionally retains it.

## Evidence record

For each assurance run, append or link a record with:

| Field | Required value |
| --- | --- |
| Observation date | ISO date and time when material |
| Git revision | Full commit hash |
| Blueprint | Exact blueprint file and resolved dimensions |
| Environment boundary | Local, CI, or other explicitly authorized target |
| Commands | Exact checks performed |
| Result | Pass, Fail, Blocked, or Not run |
| Evidence | Logs, generated package digest, report, issue, or pull request |
| Limitation | What the checks did not cover |
| Follow-up | Issue or decision link when action is needed |

## Initial assurance backlog

These are validation candidates, not commitments.

| Candidate | Current evidence state | Next evidence |
| --- | --- | --- |
| Re-run Assembler, CLI, and repository-manager tests at the baseline revision | Passed on 2026-08-27: 38 runs, 214 assertions, 0 failures, 0 errors | Repeat after relevant changes and retain CI evidence when available |
| Validate required source-repository declarations for an applicable blueprint | Not run | Repository-validation report and exact blueprint |
| Assemble and validate the documented development blueprint | Not run | Blueprint, assembled lock/report, and validation result |
| Validate representative self-hosted production and high-assurance blueprints | Not run | Deployment packages, policy reports, and explicit external-control gaps |
| Exercise gateway configuration and documented health behavior | Not run | Command output and observation window |
| Create prioritized service runbooks | Missing concrete procedures in inspected paths | Reviewed and exercised procedure links |
| Confirm accountable owner and product lifecycle | Unknown | Authoritative project or governance record |

## Refresh procedure

1. Determine which baseline claims the triggering change affects.
2. Record the full Git revision and authorized environment boundary.
3. Run the smallest check that can support each affected claim.
4. Preserve Fail, Blocked, and Not run; never collapse them into a passing
   summary.
5. Update the [evidence register](evidence-register.md) and create a new dated
   baseline when the overall current-state description materially changes.
6. Route implementation work to GitHub Issues and material choices to Nexus
   decisions.
7. Update Engineering OS discovery pointers only after their confirmation
   gates are satisfied.

## Related

- [Takeover index](README.md)
- [Engineering Baseline](engineering-baseline-2026-08-27.md)
- [Migration ledger](migration-ledger.md)
- [Composition documentation](../../../composition/README.md)
