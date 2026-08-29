# Runbook: Deploy or reload the gateway

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P1 — routine change with system-wide routing impact

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: Nexus local development using root `compose.yml`; adapt and re-review before use in another environment

Severity: routine, escalating to incident if health or routes regress

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Safely deploy baked gateway configuration or reload configuration that an
environment mounts at runtime, while preserving a known rollback point.

## Preconditions and safety

- Required access: repository checkout and permission to operate the selected
  Compose project.
- Required tools: Git, Docker Engine, Docker Compose, `make`, and `curl`.
- User or data impact: recreating or reloading the gateway can interrupt every
  public route briefly.
- Destructive or irreversible steps: none; do not prune images or volumes.
- Escalate before proceeding when the target is shared, the previous image or
  Git revision is unknown, or TLS/authentication behavior also changes.

Record the target revision, current gateway container, and current image before
changing anything:

```sh
git rev-parse HEAD
docker compose ps gateway
docker compose images gateway
```

## Detection

Use this runbook for an approved change under `system/system-gateway/`, a
gateway image update, or a runtime-mounted configuration change.

## Diagnosis and preflight

1. Review the exact pending gateway diff.
2. Validate the rendered NGINX configuration and Compose model:

   ```sh
   make gateway-test
   docker compose -f compose.yml config --quiet
   ```

3. Stop if either command fails. A warning is not approval to deploy.

## Procedure: default baked configuration

The default composition bakes configuration into the image; a reload alone
does not apply repository changes.

1. Build and recreate the gateway:

   ```sh
   make gateway
   ```

2. Verify container and gateway health:

   ```sh
   docker compose ps gateway
   curl --fail --show-error http://127.0.0.1/healthz
   curl --fail --show-error http://127.0.0.1/readyz
   ```

3. Verify representative routes selected by the deployed composition. A `502`
   for a deliberately absent upstream is not a gateway failure, but it must be
   recorded.

## Procedure: runtime-mounted configuration

Use this only when the deployment mounts changed NGINX files into the running
container. It is not the default root composition.

```sh
make gateway-reload
curl --fail --show-error http://127.0.0.1/healthz
curl --fail --show-error http://127.0.0.1/readyz
```

`make gateway-reload` runs `nginx -t` before sending the reload signal. Do not
send `nginx -s reload` directly after a failed validation.

## Success criteria

- The gateway container is running and healthy.
- `/healthz` and `/readyz` return success.
- Expected selected routes return their expected status.
- Gateway logs contain no new configuration or reload errors.

## Rollback or recovery

Rebuild and redeploy the previously approved Git revision or immutable image.
Do not guess a tag. Validate that revision with `make gateway-test` before
recreating the gateway, then repeat the success checks. If rollback cannot
restore routing, follow `gateway-upstream-failure.md` and escalate.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| Gateway health fails after rollback | Gateway operator and incident lead | Revisions, image IDs, `docker compose ps`, NGINX validation output, logs |
| Shared TLS or authentication behavior changes unexpectedly | Security owner | Affected hosts, certificate/client identifiers, timeline, observed responses |

## Follow-up

- Record the revision, environment, commands, results, and rollback use.
- Create an issue for any mismatch between rendered configuration and docs.
- Update this runbook when an exercised deployment differs from the procedure.
