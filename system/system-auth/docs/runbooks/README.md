# Authentication Stack Runbooks

Operational runbooks for the authentication stack belong in this directory.
Keep Keycloak and its private PostgreSQL dependency together because they share
an operational lifecycle and owner.

## Runbooks

| Priority | Runbook | Scope | Exercise state |
| --- | --- | --- | --- |
| P0 / P1 | [Keycloak administration and credential rotation](auth-administration-and-credential-rotation.md) | Realm/client changes plus admin, client-secret, and database-password rotation | Desk-reviewed; not exercised |
| P0 / P1 | [Keycloak database backup and restore](auth-database-backup-and-restore.md) | Logical backup, trial restore, and explicitly destructive database recovery | Desk-reviewed; not exercised |
| P0 / P1 | [Keycloak upgrade and outage](auth-upgrade-and-outage.md) | Bounded outage diagnosis, upgrade, and schema-aware rollback | Desk-reviewed; not exercised |

Review evidence: [2026-08-30 minimum-runbook review](../../../../docs/runbooks/review-evidence-2026-08-30.md).
