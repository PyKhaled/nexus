# Runbooks

Runbooks are owned by the service or stack whose operation they describe. For example, `system-website` is the WordPress stack, so its runbooks live at `system/system-website/docs/runbooks/`.
This directory is the central discovery index; service-specific procedures remain beside their deployable boundary under `system/`.

The missing minimum procedure set and exercise evidence are tracked in
[issue #28](https://github.com/PyKhaled/Nexus/issues/28).

## Service runbook indexes

| Service or stack | Runbooks | Scope |
| --- | --- | --- |
| System Gateway | [`system/system-gateway/docs/runbooks/`](../../system/system-gateway/docs/runbooks/) | NGINX gateway operations |
| Authentication stack | [`system/system-auth/docs/runbooks/`](../../system/system-auth/docs/runbooks/) | Keycloak and PostgreSQL operations |
| Website stack | [`system/system-website/docs/runbooks/`](../../system/system-website/docs/runbooks/) | WordPress and MySQL operations |
| Service status stack | [`system/system-status/docs/runbooks/`](../../system/system-status/docs/runbooks/) | Kener and Redis operations |
| Observability service | [`system/system-overseer/docs/runbooks/`](../../system/system-overseer/docs/runbooks/) | Overseer operations |
| Service scaffold | [`system/system-service/docs/runbooks/`](../../system/system-service/docs/runbooks/) | Procedures for services created from the scaffold |

## Prioritized runbooks

P0 covers high-impact active failure, security exposure, or destructive
recovery where delay materially increases harm. P1 covers likely routine
change and preventative recovery work whose failure can still cause an
incident. Mixed priority means the normal operation is P1 but its incident or
destructive path is P0.

| Priority | Service or stack | Runbook |
| --- | --- | --- |
| P0 | Gateway | [Upstream failure](../../system/system-gateway/docs/runbooks/gateway-upstream-failure.md) |
| P1 | Gateway | [Deploy and reload](../../system/system-gateway/docs/runbooks/gateway-deploy-and-reload.md) |
| P1 / P0 | Gateway | [Certificate rotation](../../system/system-gateway/docs/runbooks/gateway-certificate-rotation.md) |
| P0 / P1 | Authentication | [Administration and credential rotation](../../system/system-auth/docs/runbooks/auth-administration-and-credential-rotation.md) |
| P0 / P1 | Authentication | [Database backup and restore](../../system/system-auth/docs/runbooks/auth-database-backup-and-restore.md) |
| P0 / P1 | Authentication | [Upgrade and outage](../../system/system-auth/docs/runbooks/auth-upgrade-and-outage.md) |
| P0 / P1 | Website | [Database and content recovery](../../system/system-website/docs/runbooks/website-database-and-content-recovery.md) |
| P1 | Website | [Maintenance and upgrade](../../system/system-website/docs/runbooks/website-maintenance-and-upgrade.md) |
| P0 | Website | [Extension failure and outage](../../system/system-website/docs/runbooks/website-extension-failure-and-outage.md) |
| P0 | Observability | [Docker-socket exposure incident](../../system/system-overseer/docs/runbooks/overseer-socket-exposure-incident.md) |
| P1 | Observability | [Upgrade and rollback](../../system/system-overseer/docs/runbooks/overseer-upgrade-and-rollback.md) |
| P0 / P1 | Service status | [Outage triage](../../system/system-status/docs/runbooks/status-outage-triage.md) |

## Review evidence

- [2026-08-30 minimum-runbook desk review](review-evidence-2026-08-30.md) —
  source-bound documentation review; no recovery or incident procedure was
  executed.

## Conventions

- Start new procedures from [`Runbook-Template.md`](Runbook-Template.md).
- Name each runbook after the system or event it handles, such as `postgres-restore.md` or `gateway-upstream-failure.md`.
- Keep stack dependencies in the owning stack's runbook directory.
- Include prerequisites, safety warnings, verification steps, rollback steps, and escalation details when applicable.
- Use commands that are safe to copy, and identify any environment-specific values explicitly.
- Link new runbooks from the owning directory's `README.md` and from this index when adding a new deployable boundary.
