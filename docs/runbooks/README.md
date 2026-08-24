# Runbooks

Runbooks are owned by the service or stack whose operation they describe. This
directory is the central discovery index; service-specific procedures remain
beside their deployable boundary under `system/`.

## Service runbook indexes

| Service or stack | Runbooks | Scope |
| --- | --- | --- |
| System Gateway | [`system/system-gateway/docs/runbooks/`](../../system/system-gateway/docs/runbooks/) | NGINX gateway operations |
| Authentication stack | [`system/system-auth/docs/runbooks/`](../../system/system-auth/docs/runbooks/) | Keycloak and PostgreSQL operations |
| Website stack | [`system/system-website/docs/runbooks/`](../../system/system-website/docs/runbooks/) | WordPress and MySQL operations |
| Service status stack | [`system/system-status/docs/runbooks/`](../../system/system-status/docs/runbooks/) | Kener, SQLite, and Redis operations |

## Conventions

- Name each runbook after the system or event it handles, such as
  `postgres-restore.md` or `gateway-upstream-failure.md`.
- Keep stack dependencies in the owning stack's runbook directory.
- Include prerequisites, safety warnings, verification steps, rollback steps,
  and escalation details when applicable.
- Use commands that are safe to copy, and identify any environment-specific
  values explicitly.
- Link new runbooks from the owning directory's `README.md` and from this index
  when adding a new deployable boundary.

The copyable service runbook scaffold lives under
[`templates/service/docs/runbooks/`](../../templates/service/docs/runbooks/).
It is not an operational runbook for the current Nexus system.
