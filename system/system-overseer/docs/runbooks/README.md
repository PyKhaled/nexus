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

## Required future runbooks

- credential and network isolation review before any non-trusted-network exposure
- incident response if the Docker socket mount is ever exposed or misused
- upgrade and rollback procedure for pinned image versions

Any procedure touching the Docker socket mount must document the exact
host-level blast radius before it is executed.
