# Runbook: Back up and restore the Keycloak database

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P0 before destructive recovery; P1 for scheduled backup verification

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; no restore has been run; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: local PostgreSQL service `keycloak-db`, database/role `keycloak`, and bind-mounted data directory `system/system-auth-db/data`

Severity: routine or critical

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Create a logical Keycloak backup, verify it with an isolated trial restore, and
restore the exact local database only when recovery is approved.

## Preconditions and safety

- Required access: Docker Compose operation and an approved backup directory
  outside the repository.
- Required tools: the PostgreSQL utilities already present in `keycloak-db`.
- User or data impact: the final restore stops Keycloak and replaces the
  `keycloak` database.
- Destructive or irreversible steps: dropping/recreating database `keycloak`.
  Never remove `system/system-auth-db/data` as part of this procedure.
- Escalate before proceeding when the backup is empty/unverified, configured
  database or role names differ, storage corruption is suspected, or the
  target is not local development.

Replace `/absolute/approved/backup/keycloak.dump` with a reviewed path outside
the repository. Confirm `POSTGRES_DB=keycloak` and `POSTGRES_USER=keycloak` for
the selected environment before using the literal names below.

## Detection

- Scheduled backup/restore exercise.
- Backup required before realm, credential, image, or schema change.
- Keycloak data recovery approved after corruption or operator error.

## Procedure: create and verify a backup

1. Confirm database health:

   ```sh
   docker compose ps keycloak-db
   docker compose exec keycloak-db pg_isready -U keycloak -d keycloak
   ```

2. Create a custom-format logical dump:

   ```sh
   docker compose exec -T keycloak-db pg_dump -U keycloak -d keycloak --format=custom > /absolute/approved/backup/keycloak.dump
   test -s /absolute/approved/backup/keycloak.dump
   docker compose exec -T keycloak-db pg_restore --list < /absolute/approved/backup/keycloak.dump
   ```

3. Trial-restore into the exact temporary database `nexus_keycloak_restore_check`:

   ```sh
   docker compose exec keycloak-db dropdb -U keycloak --if-exists nexus_keycloak_restore_check
   docker compose exec keycloak-db createdb -U keycloak -O keycloak nexus_keycloak_restore_check
   docker compose exec -T keycloak-db pg_restore -U keycloak -d nexus_keycloak_restore_check --exit-on-error < /absolute/approved/backup/keycloak.dump
   docker compose exec keycloak-db psql -U keycloak -d nexus_keycloak_restore_check -c 'SELECT COUNT(*) FROM realm;'
   docker compose exec keycloak-db dropdb -U keycloak nexus_keycloak_restore_check
   ```

4. Record the file path in the approved evidence store, timestamp, size,
   checksum, source revision/environment, and successful trial query. Do not
   commit the dump.

## Procedure: destructive restore of database `keycloak`

Proceed only with the verified dump from the previous section and explicit
approval. These commands replace database `keycloak` but do not touch the
physical bind mount.

1. Stop Keycloak while leaving PostgreSQL running:

   ```sh
   docker compose stop keycloak
   ```

2. Terminate remaining sessions, replace the database, and restore:

   ```sh
   docker compose exec keycloak-db psql -U keycloak -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'keycloak' AND pid <> pg_backend_pid();"
   docker compose exec keycloak-db dropdb -U keycloak keycloak
   docker compose exec keycloak-db createdb -U keycloak -O keycloak keycloak
   docker compose exec -T keycloak-db pg_restore -U keycloak -d keycloak --exit-on-error < /absolute/approved/backup/keycloak.dump
   ```

3. Start and verify the stack:

   ```sh
   make auth
   docker compose ps keycloak keycloak-db
   curl --fail --show-error http://auth.localhost/realms/nexus/.well-known/openid-configuration
   ```

4. Verify a named administrator login and one representative client flow.

## Success criteria

- Backup is non-empty, listable, and trial-restores without error.
- Restored Keycloak and PostgreSQL report healthy.
- Named administrator and representative client authentication succeed.
- Backup metadata/checksum are retained outside Git.

## Rollback or recovery

If the restored database fails verification, keep Keycloak stopped and repeat
the destructive restore using the immediately preceding separately verified
backup. If no verified backup succeeds, preserve the data directory and logs,
stop destructive attempts, and escalate. Never initialize an empty database to
make health checks pass.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| Trial restore fails | Database and identity owners | PostgreSQL version, redacted error, dump checksum/size, source environment |
| All verified backups fail | Incident lead | Attempt timeline, untouched data path, backup inventory, logs |
| Shared/production restore requested | Environment owner and change authority | Target database, outage approval, recovery point/time objectives, backup evidence |

## Follow-up

- Record recovery point, duration, verifier, and any data loss window.
- Investigate why recovery was required and create corrective work.
- Exercise this runbook in an authorized disposable environment before calling
  it validated.
