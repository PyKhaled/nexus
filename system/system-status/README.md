# Service Status Capability

Status: Partial development implementation

Owner: Unassigned

Implementation: [Kener v4.1.2](https://kener.ing) with Redis 7.4 and SQLite

Upstream: [documentation](https://kener.ing/docs/v4/getting-started/introduction),
[quick start](https://kener.ing/docs/v4/getting-started/quick-start), and
[source](https://github.com/rajnandan1/kener)

## Capability

Provide public service-health visibility, automated endpoint checks, incident
updates, scheduled maintenance, uptime history, and subscriber communication.
Kener is the current replaceable reference implementation.

The status capability reports on other capabilities but does not own their
telemetry, recovery procedures, or incident response decisions.

## Stack

```text
service status capability
|-- status          Kener application and SQLite data
`-- status-redis    private Redis queue, cache, and scheduler dependency
```

Redis is private to this stack. SQLite is appropriate for the local reference
environment; PostgreSQL is the preferred replacement for a shared production
deployment.

## Interfaces

| Interface | Consumer | Current contract |
| --- | --- | --- |
| `http://status.localhost` | Visitors and administrators | Gateway-routed Kener status and management UI |
| `/healthcheck` | Container runtime | Kener application health |
| Kener REST API | Approved automation | Monitor, incident, maintenance, page, and reporting automation |
| Redis protocol | Kener only | Private queue, cache, and scheduler dependency |

## Configuration and data

The root `compose.yml` follows Kener's official v4 container contract. It sets
the required `ORIGIN`, `REDIS_URL`, and `KENER_SECRET_KEY` values, persists
`/app/database`, and waits for Redis health before starting Kener.
`KENER_SECRET_KEY` defaults to an isolated-development placeholder so the local
stack starts without a secrets file. Replace it before creating real users or
using the deployment outside an isolated workstation.

Copy `.env.example` to `.env`, replace the secret, and collect the root secrets
file when a private local value is required:

```sh
cp system/system-status/.env.example system/system-status/.env
make collect-secrets
```

Kener application data is stored in the `status-data` volume. Redis append-only
data is stored in `status-redis-data`. Both volumes require backup and restore
policies before shared use.

## Local composition

Compose services: `status`, `status-redis`

Network: `nexus-system`

Public route: gateway only

```sh
make status
docker compose ps status status-redis
```

Open `http://status.localhost`. On the first launch, complete Kener's setup
screen and create the owner account. Then add the following initial monitors
from **Manage -> Monitors** and assign them to the default page:

| Monitor | Type | Internal target |
| --- | --- | --- |
| Gateway liveness | API/Website | `http://gateway/healthz` |
| Gateway readiness | API/Website | `http://gateway/readyz` |
| Public website | API/Website | `http://website/` |
| Authentication | API/Website | `http://keycloak:8080/health/ready` |

The checks run through the private Docker network and Kener updates the public
page automatically. Monitor the externally visible domains from a separate
deployment when the goal is detecting a complete host, network, or gateway
failure.

## Replacement contract

A replacement status implementation must deliberately migrate:

- the stable public status route;
- monitor definitions, check semantics, and uptime history;
- incidents, maintenance windows, pages, and subscriber data;
- alerting and notification integrations;
- administrative roles, API clients, and auditability;
- backup, recovery, retention, and upgrade procedures; and
- an external monitoring strategy that remains available during Nexus outages.

## Known gaps

- First-run owner creation and initial monitor assignment are manual.
- Email delivery and public subscriber notifications are not configured.
- The local status service shares the host and network it monitors.
- No backup, restore, retention, external probing, or upgrade runbook exists.
- SQLite is not the selected production database topology.
