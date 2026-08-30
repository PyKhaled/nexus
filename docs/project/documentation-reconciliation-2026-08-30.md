# Documentation Reconciliation Evidence — 2026-08-30

## Evidence boundary

| Field | Value |
| --- | --- |
| Review date | 2026-08-30 |
| Source revision reviewed | `1b9633bc90553b7cdeb2091d2d4aef61dbba97dd` (`main`) |
| Change branch | `docs/issue-30-documentation-reconciliation` |
| Issue | [#30](https://github.com/PyKhaled/Nexus/issues/30) |
| Environment | Versioned repository configuration and GitHub issue state; no deployed environment inspected |
| Runtime verification | Not run |
| Production-readiness claim | None |

This record establishes what was reconciled and statically validated. It does
not replace the fresh commit-bound runtime baseline tracked in
[issue #17](https://github.com/PyKhaled/Nexus/issues/17).

## Reconciled sources

- Root README and onboarding boundaries for current implementation versus
  GitHub-tracked work.
- Documentation index boundaries for the dated takeover package and
  publication-time GitHub work index.
- Product-system profile capability names, states, implementations, and root
  Compose services.
- Composition catalog, active root Compose definition, checked-in blueprints,
  and documented Compose modes/examples.
- Current component known-gap references after issue #28 closed.
- Website capability documentation and environment example, replacing a stale
  nonexistent standalone layout, service names, and port.

## GitHub state observed

Issues #16–#27 and #29–#30 were open during the review. Issue #28 was closed
after the minimum runbook PR merged. Historical links to closed issues remain
only where the surrounding text identifies them as historical or completed
work. GitHub remains authoritative after this observation date.

## Capability reconciliation

The current-state sources agree on five partial capabilities and eight root
Compose services:

| Capability | Implementation | Compose services |
| --- | --- | --- |
| `gateway` | NGINX | `gateway` |
| `website` | WordPress | `website`, `website-db` |
| `authentication` | Keycloak | `keycloak`, `keycloak-db` |
| `service-status` | Kener | `status`, `status-redis` |
| `observability` | Overseer | `overseer` |

Missing manifest vocabulary remains outside current implementation and is
tracked for disposition in [issue #29](https://github.com/PyKhaled/Nexus/issues/29).

## Validation results

| Check | Result | Limitation |
| --- | --- | --- |
| Programmatic comparison of `product-system.yaml`, all catalog entries, and root Compose | Pass: 5 current capabilities and 8 services agree | Does not prove runtime health |
| Resolution of 43 local Markdown links in the reviewed documentation | Pass | Excludes the non-runnable `system-service` scaffold and external URLs |
| Root, TLS, API-auth, combined secure, standalone auth, and standalone website Compose configuration | Pass: all 6 configurations resolve | `docker compose config` does not start services |
| Every checked-in blueprint passed `bin/nexus plan` | Pass: 3 blueprints | Planning does not assemble or deploy packages |
| `make assembler-test` | Pass: 40 runs, 223 assertions, 0 failures/errors | Does not verify documentation prose or runtime services |
| `make help`, dry-run `make website collect-secrets`, and `bin/nexus help` | Pass | Website and secret collection were not executed |
| Website environment-example keys against root Compose interpolation | Pass: all 4 keys are consumed | Private values and resulting service behavior were not inspected |
| Stale-claim scan and `git diff --check` | Pass | Text scan cannot establish semantic completeness |

## Compose-example boundary retained

The documentation now states the observed limitation instead of implying full
secure-mode coverage: the local TLS example mounts website, authentication,
and reserved API HTTPS routes, but not the checked-in status or Overseer TLS
routes. With redirect enabled, those two hosts reach the default HTTPS `404`.
The API-auth example can exercise its OIDC boundary but has no runnable Nexus
API upstream. No implementation change is represented as merged behavior.

## Acceptance mapping

| Issue #30 acceptance criterion | Evidence |
| --- | --- |
| No closed issue described as current open backlog | Live-state scan plus historical/publication-time labels in indexes |
| Documentation links resolve and describe evidence boundaries | 43-link check; dated takeover and work-index descriptions updated |
| Current behavior and tracked work are visibly separated | Profile inventory, onboarding boundary, GitHub-authority wording |
| Capability names and states agree | Programmatic manifest/catalog/Compose comparison and profile table |
| Compose-mode TODO removed after review | Guide reviewed through deployment boundary; exact example limitations documented |
| Relevant links and commands validated | Validation table above |

## Limitations and follow-up

- Runtime startup, HTTP routes, persistence, and reset behavior remain for
  [issue #17](https://github.com/PyKhaled/Nexus/issues/17).
- The incomplete local TLS route surface is documented, not repaired by this
  documentation issue.
- Website recovery runbooks remain desk-reviewed rather than exercised.
- Accountable ownership remains unassigned and tracked in
  [issue #16](https://github.com/PyKhaled/Nexus/issues/16).
