# Service Status Runbooks

This directory owns operational procedures for Kener, its SQLite data, and its
private Redis dependency.

## Current local checks

Start the stack and inspect health from the repository root:

```sh
make status
docker compose ps status status-redis
docker compose logs status status-redis
curl http://status.localhost/healthcheck
```

## Required future runbooks

- Kener and database backup and restore
- Kener version upgrade and rollback
- Redis recovery and queue troubleshooting
- monitor and incident export and recovery
- subscriber-email delivery failure
- external-probe and whole-site outage handling

Any destructive recovery procedure must name the exact volumes involved and
include a verified backup before data is replaced.
