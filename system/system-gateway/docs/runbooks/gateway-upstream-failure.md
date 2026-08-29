# Runbook: Diagnose a gateway upstream failure

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P0 when a required route is unavailable

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: Nexus local development using root `compose.yml`; route and service names must be confirmed for other packages

Severity: degraded or incident

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Separate a healthy gateway returning an upstream error from a gateway
configuration failure, then restore only the affected service boundary.

## Preconditions and safety

- Required access: Docker read access and permission to start the affected
  Compose service.
- Required tools: Docker Compose and `curl`.
- User or data impact: restarting a stateful stack can interrupt active users.
- Destructive or irreversible steps: none. Do not remove containers, volumes,
  databases, or networks during diagnosis.
- Escalate before proceeding when data corruption, repeated crash loops, or a
  security incident is suspected.

## Detection

- A routed request returns `502` or `504`.
- `/healthz` succeeds but a product route fails.
- Gateway logs report connection refusal, timeout, or unresolved upstream.

## Diagnosis

1. Confirm the gateway itself:

   ```sh
   curl --fail --show-error http://127.0.0.1/healthz
   curl --fail --show-error http://127.0.0.1/readyz
   docker compose ps gateway
   docker compose logs --tail 100 gateway
   ```

2. Reproduce the route without relying on workstation DNS. Replace the host
   with the affected configured domain:

   ```sh
   curl --include --header 'Host: auth.localhost' http://127.0.0.1/
   ```

3. Map the route to its current upstream:

   | Route | Compose service | Internal port |
   | --- | --- | --- |
   | `localhost` | `website` | `80` |
   | `auth.localhost` | `keycloak` | `8080` |
   | `status.localhost` | `status` | `3000` |
   | `overseer.localhost` | `overseer` | `8765` |
   | `api.localhost` | `api` | `8000`; reserved and absent by default |

4. Inspect only the affected service and dependency:

   ```sh
   docker compose ps
   docker compose logs --tail 200 SERVICE_NAME
   docker network inspect nexus-system
   ```

5. Confirm that the service is running, healthy when it defines a health
   check, attached to `nexus-system`, and listening on the configured internal
   port. A default `api.localhost` `502` is expected while `api` is absent.

## Procedure

1. If the selected service is stopped and no corruption/security concern is
   present, start its owning stack with the documented Make target (`make
   website`, `make auth`, `make status`, or `make overseer`).
2. If an approved configuration correction is required, apply it through the
   owning component and then follow `gateway-deploy-and-reload.md`.
3. Repeat the direct host-header request and inspect new gateway/upstream logs.

## Success criteria

- Gateway health remains successful.
- The selected upstream and required private dependencies are healthy.
- The route returns its expected application response instead of `502`/`504`.
- No unrelated service or persistent resource was recreated.

## Rollback or recovery

If a configuration change worsens the incident, restore the prior approved
configuration/image and redeploy the gateway. If the upstream still fails,
stop changing gateway configuration and escalate to the owning stack runbook.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| Gateway healthy, upstream crash-looping | Owning service operator | Route, service, health state, dependency state, logs, last change |
| Multiple unrelated upstreams fail | Platform/network incident lead | Gateway health, network inspection, affected routes, timeline |
| Failure follows credential or certificate change | Security owner and owning service operator | Changed identifier, timing, redacted error output, rollback result |

## Follow-up

- Record route, root cause, duration, and recovery action.
- Add a health check or alert when detection depended on manual observation.
- Correct stale route, service, or port documentation in the same follow-up.
