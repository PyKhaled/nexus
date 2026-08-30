# Service Status Capability

Status: Partial

Owner: Unassigned

Implementation type: stack

Technology: Kener 4.1.2 with Redis 7.4 and SQLite

## Capability

Provide public service-health visibility, automated endpoint checks, incident
updates, scheduled maintenance, uptime history, and subscriber communication.
Kener is the current replaceable reference implementation.

The status capability reports on other capabilities but does not own their
telemetry, recovery procedures, or incident response decisions.

## Scope

Owns:

- the public status page and its uptime, incident, and maintenance history;
- monitor definitions and check scheduling for Nexus services; and
- its own SQLite data and private Redis dependency.

Does not own:

- the health or readiness of the services it monitors;
- incident response or recovery procedures for other components; or
- external, off-cluster probing of Nexus as a whole.

## Implementation

```text
service status capability
|-- status          Kener application and SQLite data
`-- status-redis    private Redis queue, cache, and scheduler dependency
```

Redis is private to this stack. SQLite is appropriate for the local reference
environment; PostgreSQL is the preferred replacement for a shared production
deployment.

## Interfaces

| Interface | Consumer | Contract |
| --- | --- | --- |
| `http://status.localhost` | Visitors and administrators | Gateway-routed Kener status and management UI |
| `/healthcheck` | Container runtime | Kener application health |
| Kener REST API | Approved automation | Monitor, incident, maintenance, page, and reporting automation |
| Redis protocol | Kener only | Private queue, cache, and scheduler dependency |

## Data ownership

Kener application data (SQLite database, uploaded assets) is stored in the
`status-data` volume. Redis append-only data is stored in `status-redis-data`.
Both volumes are private to this stack, persist across container recreation,
and currently have no backup or restore policy — see
[`docs/runbooks/README.md`](docs/runbooks/README.md).

## Configuration

| Setting | Purpose | Required | Secret | Owner | Safe development value |
| --- | --- | --- | --- | --- | --- |
| `KENER_SECRET_KEY` | Application signing and encryption key | Yes | Yes | Service owner | `change-me-kener-development-secret-at-least-32-chars` |
| `STATUS_DOMAIN` | Public status hostname; also used to build Kener's `ORIGIN` | Yes | No | Service owner | `status.localhost` |

The root `compose.yml` sets the required Kener `ORIGIN` and `REDIS_URL` values
directly; only `KENER_SECRET_KEY` and `STATUS_DOMAIN` need overriding locally.
`KENER_SECRET_KEY` defaults to an isolated-development placeholder so the local
stack starts without a secrets file. Replace it before creating real users or
using the deployment outside an isolated workstation.

Copy `.env.example` to `.env`, replace the secret, and collect the root secrets
file when a private local value is required:

```sh
cp system/system-status/.env.example system/system-status/.env
make collect-secrets
```

## Local composition

Compose services: `status`, `status-redis`

Network: `nexus-system`

Public route: gateway only; neither service publishes a host port.

```sh
make status
docker compose ps status status-redis
```

## Development

```sh
make status
curl http://status.localhost/healthcheck
make gateway-test
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

## Deployment and release

The development composition builds no image; `status` runs the pinned upstream
`ghcr.io/rajnandan1/kener:v4.1.2` image directly. Kener does not publish a
patch-floating `v4.1` image alias, so this is an explicit exact-patch exception.
A production deployment should resolve and pin an image digest and replace
SQLite with a managed PostgreSQL database, following the same pattern as the
authentication stack's database.

## Security and operations

- Both services join `nexus-system` only; the gateway is the only public entry
  point and neither service publishes a host port.
- Health is reported via `/healthcheck` (Kener) and `redis-cli ping`
  (Redis); Compose `depends_on: condition: service_healthy` gates startup.
- Logs are collected as `json-file` with the same rotation policy as the rest
  of the stack (10m / 3 files).
- See [`docs/runbooks/README.md`](docs/runbooks/README.md) for current checks
  and required future runbooks.

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

| Gap | Risk | Owner | Target or review date |
| --- | --- | --- | --- |
| First-run owner creation and initial monitor assignment are manual | New environments start with an empty status page | [#27](https://github.com/PyKhaled/Nexus/issues/27) | Unscheduled |
| Email delivery and public subscriber notifications are not configured | Incidents are not proactively communicated | [#27](https://github.com/PyKhaled/Nexus/issues/27) | Unscheduled |
| The local status service shares the host and network it monitors | A full network or host failure is invisible to itself | [#27](https://github.com/PyKhaled/Nexus/issues/27) | Unscheduled |
| No backup, restore, retention, external probing, or upgrade runbook exists | Data loss or a stale status page can go unnoticed | [#27](https://github.com/PyKhaled/Nexus/issues/27) | Unscheduled |
| SQLite is not the selected production database topology | Does not meet shared-deployment durability expectations | [#27](https://github.com/PyKhaled/Nexus/issues/27) | Unscheduled |
