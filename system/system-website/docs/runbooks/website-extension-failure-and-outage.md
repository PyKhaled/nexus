# Runbook: Recover from a WordPress extension failure or outage

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P0 when the public site or administration is unavailable

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: local WordPress service `website`, database service `website-db`, and routed host `localhost`

Severity: degraded or incident

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Diagnose a WordPress outage and disable one suspected plugin or theme without
destroying the database or content volume.

## Preconditions and safety

- Required access: Docker Compose, gateway, and WordPress administration when
  available.
- Required tools: Docker and `curl`.
- User or data impact: disabling an extension changes site behavior; restarting
  WordPress interrupts active requests.
- Destructive or irreversible steps: none. Moving an extension directory is
  reversible. Do not remove volumes or reinstall WordPress.
- Escalate before proceeding when compromise, database corruption, multiple
  simultaneous extension failures, or unknown recent changes are suspected.

## Detection

- Public route returns `500`, blank page, or repeated redirect.
- `/wp-admin/` is unavailable after a plugin/theme change.
- WordPress logs show a PHP fatal in a specific plugin or theme.

## Diagnosis

1. Capture current state before restart:

   ```sh
   curl --include http://127.0.0.1/
   docker compose ps gateway website website-db
   docker compose logs --tail 200 website website-db gateway
   ```

2. Confirm MySQL health separately:

   ```sh
   docker compose exec website-db sh -c 'exec mysqladmin ping -h localhost -uroot -p"$MYSQL_ROOT_PASSWORD"'
   ```

3. Determine whether the failure is gateway-only, database connectivity,
   WordPress core, storage/permissions, plugin, or theme related. Follow the
   gateway upstream runbook when WordPress is healthy internally but routed
   access fails.

## Procedure: disable one suspected plugin

Replace `PLUGIN_SLUG` with the exact directory confirmed from the logs. List
the directory first; never use a wildcard.

```sh
docker compose exec website ls -la /var/www/html/wp-content/plugins
docker compose exec website mv /var/www/html/wp-content/plugins/PLUGIN_SLUG /var/www/html/wp-content/plugins/PLUGIN_SLUG.disabled
docker compose restart website
```

Verify the public route and `/wp-admin/`. Do not disable additional plugins
without recording the result of the first change.

## Procedure: disable one suspected theme

Confirm another installed theme can be selected. Prefer the WordPress admin
interface when available. If the site is inaccessible, move only the exact
suspected theme directory after recording its name:

```sh
docker compose exec website ls -la /var/www/html/wp-content/themes
docker compose exec website mv /var/www/html/wp-content/themes/THEME_SLUG /var/www/html/wp-content/themes/THEME_SLUG.disabled
docker compose restart website
```

If WordPress has no usable fallback theme, stop and escalate rather than
deleting files.

## Success criteria

- Public route and `/wp-admin/` respond as expected.
- Database remains healthy and persistent volumes remain present.
- The single responsible extension/change is identified or the incident is
  escalated with evidence.
- No extension or user content was deleted.

## Rollback or recovery

To reverse a diagnostic disable, move the exact `.disabled` directory back to
its original name and restart `website`, but only after the extension is fixed
or determined not to be the cause. If an upgrade corrupted database/content,
use `website-database-and-content-recovery.md` with a matched verified recovery
point; do not delete volumes or run a fresh installer.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| No safe fallback theme or multiple extensions implicated | Website owner | Recent changes, exact directories, logs, HTTP results, backup references |
| Database unhealthy/corrupt | Website/database operator and incident lead | Health output, logs, exact volume, last verified backup |
| Malicious extension or compromise suspected | Security incident lead | Extension source/version, indicators, access window, containment state |

## Follow-up

- Record the extension/version, trigger, impact, and recovery.
- Patch, replace, or remove the extension through a reviewed change.
- Add a regression check for the failed public/admin workflow.
