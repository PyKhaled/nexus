# Observability Runbooks

This directory owns operational procedures for Overseer, which mounts
`/var/run/docker.sock` and has no built-in authentication of its own.

## Current local checks

Start the service and inspect health from the repository root:

```sh
make overseer
docker compose ps overseer
docker compose logs overseer
curl http://overseer.localhost/healthz
```

## Runbooks

| Priority | Runbook | Scope | Exercise state |
| --- | --- | --- | --- |
| P0 | [Docker-socket exposure incident](overseer-socket-exposure-incident.md) | Immediate containment, evidence preservation, host/credential recovery boundary | Desk-reviewed; not exercised |
| P1 | [Overseer upgrade and rollback](overseer-upgrade-and-rollback.md) | Digest-aware upgrade, project/CSRF verification, and rollback | Desk-reviewed; not exercised |

Review evidence: [2026-08-30 minimum-runbook review](../../../../docs/runbooks/review-evidence-2026-08-30.md).

Any procedure touching the Docker socket mount must document the exact
host-level blast radius before it is executed.
