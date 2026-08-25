# Runbooks

Runbooks are owned by the service or stack whose operation they describe. For example, `system-website` is the WordPress stack, so its runbooks live at `system/system-website/docs/runbooks/`.
This directory is the central discovery index; service-specific procedures remain beside their deployable boundary under `system/`.

## Service runbook indexes

| Service or stack | Runbooks | Scope |
| --- | --- | --- |
| System Gateway | [`system/system-gateway/docs/runbooks/`](../../system/system-gateway/docs/runbooks/) | NGINX gateway operations |
| Authentication stack | [`system/system-auth/docs/runbooks/`](../../system/system-auth/docs/runbooks/) | Keycloak and PostgreSQL operations |
| Website stack | [`system/system-website/docs/runbooks/`](../../system/system-website/docs/runbooks/) | WordPress and MySQL operations |
| Service status stack | [`system/system-status/docs/runbooks/`](../../system/system-status/docs/runbooks/) | Kener and Redis operations |
| Observability service | [`system/system-overseer/docs/runbooks/`](../../system/system-overseer/docs/runbooks/) | Overseer operations |
| Service scaffold | [`system/system-service/docs/runbooks/`](../../system/system-service/docs/runbooks/) | Procedures for services created from the scaffold |

## Conventions

- Start new procedures from [`Runbook-Template.md`](Runbook-Template.md).
- Name each runbook after the system or event it handles, such as `postgres-restore.md` or `gateway-upstream-failure.md`.
- Keep stack dependencies in the owning stack's runbook directory.
- Include prerequisites, safety warnings, verification steps, rollback steps, and escalation details when applicable.
- Use commands that are safe to copy, and identify any environment-specific values explicitly.
- Link new runbooks from the owning directory's `README.md` and from this index when adding a new deployable boundary.
