# Minimum Runbook Review Evidence — 2026-08-30

## Evidence boundary

| Field | Value |
| --- | --- |
| Review date | 2026-08-30 |
| Source revision reviewed | `bb9ea7d8502145867f0d73dfed71b972b4d906f3` (`main`) |
| Change branch | `docs/issue-28-minimum-runbooks` |
| Review type | AI-assisted desk review against versioned repository configuration |
| Environment | Nexus local-development definition in root `compose.yml`; no deployed or shared environment inspected |
| Runtime exercise | Not run |
| Recovery exercise | Not run |
| Approval or production-readiness claim | None |
| Excluded | `system-service` scaffold, because root `compose.yml` does not run it as a current Nexus capability |

## Review method

The runbooks were checked against the root Compose service names, internal
ports, environment contracts, persistent resources, Make targets, gateway
routes, component documentation, and the runbook acceptance criteria in
[issue #28](https://github.com/PyKhaled/Nexus/issues/28).

The review required each procedure to state:

- the environment and exact resource boundary;
- prerequisites, access, impact, and destructive steps;
- observable success criteria;
- rollback or recovery limits;
- escalation conditions and evidence to retain; and
- whether it was desk-reviewed or actually exercised.

## Reviewed runbooks

| Service or stack | Runbook | Review result | Exercise result | Principal limitation |
| --- | --- | --- | --- | --- |
| Gateway | [Deploy or reload](../../system/system-gateway/docs/runbooks/gateway-deploy-and-reload.md) | Desk-reviewed | Not run | No gateway recreation/reload performed |
| Gateway | [Certificate rotation](../../system/system-gateway/docs/runbooks/gateway-certificate-rotation.md) | Desk-reviewed | Not run | No certificate material or TLS endpoint inspected |
| Gateway | [Upstream failure](../../system/system-gateway/docs/runbooks/gateway-upstream-failure.md) | Desk-reviewed | Not run | No upstream was interrupted |
| Authentication | [Administration and credential rotation](../../system/system-auth/docs/runbooks/auth-administration-and-credential-rotation.md) | Desk-reviewed | Not run | No realm/client/credential changed |
| Authentication | [Database backup and restore](../../system/system-auth/docs/runbooks/auth-database-backup-and-restore.md) | Desk-reviewed | Not run | No backup or restore executed |
| Authentication | [Upgrade and outage](../../system/system-auth/docs/runbooks/auth-upgrade-and-outage.md) | Desk-reviewed | Not run | No Keycloak outage or upgrade performed |
| Website | [Database and content recovery](../../system/system-website/docs/runbooks/website-database-and-content-recovery.md) | Desk-reviewed | Not run | No backup or restore executed |
| Website | [Maintenance and upgrade](../../system/system-website/docs/runbooks/website-maintenance-and-upgrade.md) | Desk-reviewed | Not run | No WordPress maintenance performed |
| Website | [Extension failure and outage](../../system/system-website/docs/runbooks/website-extension-failure-and-outage.md) | Desk-reviewed | Not run | No plugin/theme was disabled |
| Observability | [Docker-socket exposure incident](../../system/system-overseer/docs/runbooks/overseer-socket-exposure-incident.md) | Desk-reviewed | Not run | No incident simulation or host isolation performed |
| Observability | [Upgrade and rollback](../../system/system-overseer/docs/runbooks/overseer-upgrade-and-rollback.md) | Desk-reviewed | Not run | No image or service changed |
| Service status | [Outage triage](../../system/system-status/docs/runbooks/status-outage-triage.md) | Desk-reviewed | Not run | No Kener/Redis failure induced |

## Static verification

| Check | Result | Limitation |
| --- | --- | --- |
| Local links across 20 central/component runbook Markdown files | Pass | Does not validate external URLs or procedure behavior |
| Shell parsing of every fenced `sh` snippet in the 12 runbooks | Pass | Checks shell syntax only; commands were not executed |
| `git diff --check` | Pass | Checks patch whitespace only |
| `docker compose -f compose.yml config --quiet` | Pass | Validates Compose structure, not runtime behavior |
| Compose service and named-volume cross-check | Pass | Confirms documented local names, not resource health or contents |
| `make gateway-test` | Blocked: Docker daemon unavailable at the configured socket | NGINX configuration was not runtime-validated in this review |
| `make assembler-test` | Pass: 40 runs, 223 assertions, 0 failures/errors | Validates Assembler code, not runbook commands |

## Findings and follow-up

- Accountable owners remain unassigned and are tracked in
  [issue #16](https://github.com/PyKhaled/Nexus/issues/16).
- Status backup, restore, upgrades, subscriber delivery, and external probing
  remain in [issue #27](https://github.com/PyKhaled/Nexus/issues/27).
- Overseer authentication and socket isolation remain in
  [issue #26](https://github.com/PyKhaled/Nexus/issues/26).
- Each destructive database/content procedure requires a separately verified
  backup and names the exact local resource it replaces.
- These runbooks must remain marked “Not exercised” until an authorized,
  dated environment exercise records observed results.
