# Runbook: Perform WordPress maintenance or upgrade

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P1

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: local `wordpress:7.0-apache` service and its private MySQL stack; shared environments require change approval and tested maintenance routing

Severity: routine, escalating to incident when verification fails

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Apply an approved WordPress image, plugin, theme, or configuration change with
a consistent backup and explicit rollback boundary.

## Preconditions and safety

- Required access: repository, WordPress administrator, Docker Compose, and
  approved backup storage.
- Required tools: browser, Docker, and `curl`.
- User or data impact: maintenance can block writes/logins; image or extension
  updates may migrate database/content.
- Destructive or irreversible steps: database/content migrations may make
  image-only rollback unsafe.
- Escalate before proceeding when backups have not trial-restored, extension
  compatibility is unknown, or the requested target tag is mutable/unreviewed.

Use `website-database-and-content-recovery.md` to create and verify both backups
before every upgrade.

## Detection

- Approved WordPress core/image, plugin, theme, or configuration maintenance.
- Security release requires an expedited but still backed-up upgrade.

## Diagnosis and preflight

1. Record current image digest, active theme/plugins, site URL, and approved
   change.
2. Review upstream compatibility, migration, and rollback notes.
3. Verify database and content backups and identify the previous exact image or
   extension artifact.
4. Validate the Compose model before deployment:

   ```sh
   docker compose -f compose.yml config --quiet
   docker compose images website website-db
   ```

## Procedure

1. Announce the maintenance window and stop editorial/admin writes.
2. Apply the reviewed image reference in `compose.yml` through version control,
   or apply the approved extension update through the WordPress administrator.
3. For an image change, pull and recreate only the website service:

   ```sh
   docker compose pull website
   docker compose up -d website
   docker compose logs --tail 200 website
   ```

4. Complete any explicitly documented WordPress database upgrade through
   `/wp-admin/` only once.
5. Verify public and administrative paths:

   ```sh
   curl --fail --show-error http://127.0.0.1/
   curl --include http://127.0.0.1/wp-admin/
   docker compose ps website website-db
   ```

6. Verify representative content, media, login, active theme, critical plugins,
   and one safe read-only workflow.

## Success criteria

- Website and database remain running/healthy as applicable.
- Public pages, media, admin login, theme, and critical plugins behave as
  expected.
- Logs show no repeated PHP fatal, database, or migration errors.
- Old image reference and verified backup checksums remain available until the
  observation window ends.

## Rollback or recovery

For a failure with no database/content migration, restore the previous exact
image or extension artifact and recreate/re-enable it. If migration or writes
occurred, stop WordPress and restore the matched pre-change database dump and
content archive with `website-database-and-content-recovery.md` before
deploying the prior image. Do not combine a database from one recovery point
with content from another without explicit data-owner approval.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| Upgrade causes public outage | Website operator and incident lead | Old/new images, active extensions, logs, backup references, affected paths |
| Database migration cannot complete | Website/database owners | WordPress/MySQL versions, migration output, backup evidence, current state |
| Security update cannot be safely applied | Security and product owners | Vulnerability/advisory, exposed version, incompatibility, compensating controls |

## Follow-up

- Record old/new versions, change window, verifier, and observed anomalies.
- Remove superseded artifacts only after the rollback window closes.
- Update compatibility notes based on exercised behavior.
