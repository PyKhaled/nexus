# Runbook: Triage a service-status outage

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P1; P0 when the status page is required during an active incident

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: local Kener service `status`, Redis dependency `status-redis`, volumes `nexus-development_status-data` and `nexus-development_status-redis-data`

Severity: degraded or incident

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Restore local Kener/Redis health without deleting status history or duplicating
the backup, upgrade, external-probe, and subscriber work tracked in issue #27.

## Preconditions and safety

- Required access: Docker Compose and gateway operation.
- Required tools: Docker and `curl`.
- User or data impact: restarting Kener/Redis briefly interrupts status updates
  and checks.
- Destructive or irreversible steps: none. Never remove either status volume
  during triage.
- Escalate before proceeding when SQLite/Redis corruption, data loss, secret
  exposure, or whole-host failure is suspected.

## Detection

- `status.localhost` or `/healthcheck` fails.
- `status` or `status-redis` is unhealthy/restarting.
- Public page stops updating monitor state during an incident.

## Diagnosis

Capture state before restart:

```sh
docker compose ps status status-redis gateway
docker compose logs --tail 200 status status-redis
curl --include http://status.localhost/healthcheck
docker volume inspect nexus-development_status-data nexus-development_status-redis-data
```

Classify the failure as gateway route, Kener application/SQLite, Redis health,
secret/origin configuration, or host-wide outage. A local status service cannot
report the failure of the host/network it shares; external probing belongs to
issue #27.

## Procedure

1. If Redis is healthy and Kener alone failed without corruption/security
   indicators, recreate only Kener:

   ```sh
   docker compose up -d status
   ```

2. If Redis is unhealthy, preserve logs and volume metadata, then restart only
   Redis and wait for health before recreating Kener:

   ```sh
   docker compose restart status-redis
   docker compose ps status-redis
   docker compose up -d status
   ```

3. If services are healthy but routing fails, use the gateway upstream-failure
   runbook; do not recreate status volumes.
4. Verify application health and the visible status page:

   ```sh
   curl --fail --show-error http://status.localhost/healthcheck
   docker compose ps status status-redis
   ```

## Success criteria

- Kener and Redis report healthy.
- Status page and `/healthcheck` respond through the gateway.
- Existing monitors/incidents/history remain visible.
- Neither status volume was removed or replaced.

## Rollback or recovery

If a restart worsens the failure, keep both volumes intact, stop repeated
restarts, preserve logs, and escalate to the recovery work tracked in issue
#27. Do not initialize a blank Kener database or Redis volume to make health
checks pass.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| SQLite or Redis corruption/data loss suspected | Status/database owner and incident lead | Logs, exact volumes, last known good time, backup state |
| Whole host/network unavailable | Platform incident lead | External observation, affected Nexus routes, status-host topology |
| Status secret or admin access compromised | Security/status owner | Exposure window, affected account/secret identifiers, containment state |

## Follow-up

- Record duration, failed layer, recovery, and monitor gaps.
- Route backup/restore, upgrade, subscriber, and external-probe work to issue
  #27 rather than expanding this triage runbook.
- Update this procedure after an authorized exercise.
