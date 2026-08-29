# Runbook: Back up and restore WordPress database and content

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P0 before destructive recovery; P1 for scheduled backup verification

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; no restore has been run; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: local services `website` and `website-db`, database `wordpress`, volume `nexus-development_wordpress-data`, and volume `nexus-development_website-db-data`

Severity: routine or critical

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Create a consistent logical MySQL backup plus a WordPress content archive,
verify both, and restore the exact local resources only with explicit approval.

## Preconditions and safety

- Required access: Docker Compose and an approved backup directory outside Git.
- Required tools: MySQL client utilities in `website-db` and `tar` in `website`.
- User or data impact: final restore stops WordPress and replaces database
  `wordpress` and/or all files in `nexus-development_wordpress-data`.
- Destructive or irreversible steps: dropping database `wordpress` or clearing
  the WordPress data volume. Both require separately verified backups.
- Escalate before proceeding when configured database/volume names differ,
  backups are unverified, storage corruption is suspected, or the target is
  shared/production.

Replace the example `/absolute/approved/backup/` paths with reviewed paths
outside the repository. Confirm the Compose project and actual volume names
with `docker compose config` and `docker volume inspect` before restoration.

## Detection

- Scheduled backup/restore exercise.
- Backup required before WordPress, plugin, theme, or database upgrade.
- Recovery approved after content/database corruption or operator error.

## Procedure: create and verify backups

1. Confirm both services are healthy/running:

   ```sh
   docker compose ps website website-db
   ```

2. Quiesce editorial/admin writes and keep them stopped until both artifacts
   are complete. Create the database dump using credentials already present
   inside the database container:

   ```sh
   docker compose exec -T website-db sh -c 'exec mysqldump --single-transaction --quick --no-tablespaces --triggers -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' > /absolute/approved/backup/wordpress.sql
   test -s /absolute/approved/backup/wordpress.sql
   ```

3. Trial-restore into exact temporary database `nexus_wordpress_restore_check`:

   ```sh
   docker compose exec website-db sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "DROP DATABASE IF EXISTS nexus_wordpress_restore_check; CREATE DATABASE nexus_wordpress_restore_check;"'
   docker compose exec -T website-db sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" nexus_wordpress_restore_check' < /absolute/approved/backup/wordpress.sql
   docker compose exec website-db sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" nexus_wordpress_restore_check -e "SELECT COUNT(*) FROM wp_options;"'
   docker compose exec website-db sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "DROP DATABASE nexus_wordpress_restore_check;"'
   ```

4. Archive the complete WordPress data volume through the running application
   container and verify the archive:

   ```sh
   docker compose exec -T website tar -C /var/www/html -czf - . > /absolute/approved/backup/wordpress-data.tgz
   test -s /absolute/approved/backup/wordpress-data.tgz
   tar -tzf /absolute/approved/backup/wordpress-data.tgz >/dev/null
   ```

5. Retain timestamp, sizes, checksums, source revision/environment, and trial
   restore result in the approved evidence store. Do not commit either backup.

## Procedure: destructive database restore

Proceed only with the verified SQL dump and confirmed database name.

```sh
docker compose stop website
docker compose exec website-db sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "DROP DATABASE wordpress; CREATE DATABASE wordpress;"'
```

Before restoring, use the approved database administration path to confirm the
configured `wordpress` user still has its grant on `wordpress.*`. Grants are
stored independently from the database and should survive recreation; stop and
escalate if the grant is absent.

```sh
docker compose exec -T website-db sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" wordpress' < /absolute/approved/backup/wordpress.sql
docker compose up -d website
```

If `MYSQL_DATABASE` or `MYSQL_USER` differs from `wordpress`, do not use the
literal command. Produce and review an environment-specific command first.

## Procedure: destructive content-volume restore

Proceed only with the verified archive and confirmed exact volume
`nexus-development_wordpress-data`.

```sh
docker compose stop website
docker compose run --rm --no-deps -T website sh -c 'find /var/www/html -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +; tar -xzf - -C /var/www/html' < /absolute/approved/backup/wordpress-data.tgz
docker compose up -d website
```

This clears and replaces only the mounted WordPress content root. It does not
replace `nexus-development_website-db-data`.

## Success criteria

- SQL dump is non-empty and trial-restores successfully.
- Content archive is non-empty and `tar` can list it.
- Restored site and `/wp-admin/` respond through the gateway.
- Representative content, media, active theme, plugin state, and admin login
  are verified.

## Rollback or recovery

If verification fails, keep WordPress stopped and repeat the applicable restore
using the immediately preceding separately verified database dump and content
archive. Preserve `nexus-development_website-db-data`,
`nexus-development_wordpress-data`, logs, and failed backups for investigation;
do not remove volumes to obtain a clean start.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| Trial restore or archive verification fails | Website/database owners | Image versions, redacted error, backup checksums/sizes, source environment |
| Database and content recovery points disagree | Incident/change authority | Both timestamps, expected content window, impact, available alternatives |
| Shared/production restore requested | Environment owner | Exact resources, outage approval, recovery objectives, verified backup evidence |

## Follow-up

- Record recovery point, data-loss window, duration, and verifier.
- Create corrective work for the initiating failure.
- Exercise both restores in a disposable authorized environment before calling
  this runbook validated.
