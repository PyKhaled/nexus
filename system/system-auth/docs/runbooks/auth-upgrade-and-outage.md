# Runbook: Upgrade Keycloak or respond to an authentication outage

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P0 for outage; P1 for planned upgrade

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: local Keycloak image built from `system/system-auth/dockerfile` and dedicated service `keycloak-db`

Severity: routine, degraded, or incident

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Diagnose authentication availability without damaging identity data and apply
a reviewed Keycloak upgrade with an evidence-backed rollback boundary.

## Preconditions and safety

- Required access: repository, Docker Compose, named Keycloak administrator,
  and approved backup storage for upgrades.
- Required tools: Docker, `curl`, and browser/client flow used for verification.
- User or data impact: authentication outage blocks every dependent login;
  upgrade can perform database schema migration.
- Destructive or irreversible steps: a schema migration may make image-only
  rollback unsafe. A verified database backup is mandatory before upgrade.
- Escalate before proceeding when PostgreSQL is unhealthy, backup verification
  failed, provider/theme compatibility is unknown, or compromise is suspected.

## Detection

- `keycloak` is unhealthy or `auth.localhost` fails.
- Dependent clients report issuer, redirect, token, or signing errors.
- An approved Keycloak version/provider/theme upgrade is scheduled.

## Procedure: outage diagnosis and bounded recovery

1. Capture state and logs before restarting:

   ```sh
   docker compose ps keycloak keycloak-db gateway
   docker compose logs --tail 200 keycloak keycloak-db
   curl --include http://auth.localhost/realms/nexus/.well-known/openid-configuration
   ```

2. Confirm PostgreSQL independently:

   ```sh
   docker compose exec keycloak-db pg_isready -U keycloak -d keycloak
   ```

3. Classify the failure: database unavailable, credential rejection, hostname/
   proxy mismatch, provider/theme startup failure, or gateway-only route issue.
4. If PostgreSQL is healthy and no corruption/security concern exists, recreate
   only Keycloak from the currently approved image:

   ```sh
   docker compose up -d --build keycloak
   ```

5. Verify readiness, a named administrator login, and one client flow. Use
   `gateway-upstream-failure.md` if Keycloak is healthy internally but the
   gateway route still fails.

## Procedure: planned upgrade

1. Review upstream release notes, migration notes, supported PostgreSQL, and
   every custom provider/theme compatibility requirement.
2. Create and trial-restore a fresh database backup using
   `auth-database-backup-and-restore.md`.
3. Change both `FROM quay.io/keycloak/keycloak:...` lines in
   `system/system-auth/dockerfile` to the same reviewed version through a pull
   request.
4. Build before touching the running service:

   ```sh
   docker compose build keycloak
   ```

5. Recreate Keycloak and monitor startup:

   ```sh
   docker compose up -d keycloak
   docker compose logs --tail 200 keycloak
   docker compose ps keycloak keycloak-db
   ```

6. Verify health, named admin login, realm/client configuration, and a
   representative token/login flow.

## Success criteria

- Keycloak and PostgreSQL are healthy.
- Admin and representative client authentication succeed.
- No unexpected realm/client/provider/theme change is observed.
- Upgrade evidence identifies old/new image references and backup checksum.

## Rollback or recovery

For a startup failure before schema change, restore the previous exact image
version and recreate Keycloak. If the new version may have migrated the
database, stop Keycloak, restore the verified pre-upgrade database using
`auth-database-backup-and-restore.md`, then deploy the previous image. Do not
run an older Keycloak against a possibly newer schema merely because the
container starts.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| Authentication unavailable and database unhealthy | Identity/database operators and incident lead | Health, logs, last change, backup reference, affected clients |
| Suspected account/client compromise | Security incident lead | Realm/client/account identifiers, exposure window, events, containment state |
| Upgrade migration or provider failure | Identity owner | Old/new versions, provider/theme inventory, backup evidence, startup logs |

## Follow-up

- Record outage duration, affected clients, root cause, and recovery.
- Add monitoring for the earliest reliable failure signal.
- Update compatibility and rollback notes after an authorized exercise.
