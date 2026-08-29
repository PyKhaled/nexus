# Observability Capability

Status: Partial

Owner: Unassigned

Implementation type: service

Technology: [Overseer](https://github.com/PyKhaled/Overseer), patch-floating image tag `3.0`

## Capability

Provide project-scoped service discovery, dependency visualization, resource
visibility, and start/stop/restart lifecycle control for the Nexus Compose
project. Overseer is the current replaceable reference implementation.

This capability observes and controls the other Nexus services; it does not
own their configuration, data, or release process.

## Scope

Owns:

- discovery and display of every service in the `nexus-development` Compose
  project (excluding itself);
- the dependency graph rendered from declared `depends_on` relationships; and
- start, stop, and restart actions for eligible services.

Does not own:

- the health, configuration, or data of the services it observes;
- authentication for the Nexus stack (it has none of its own); or
- host-level Docker daemon administration beyond what its dashboard exposes.

## Implementation

Overseer is a single stateless service with no private dependency. It reads
`com.docker.compose.project` from its own container to scope discovery to
this Compose project and excludes itself from the results.

## Interfaces

| Interface | Consumer | Contract |
| --- | --- | --- |
| `http://overseer.localhost` | Administrators | Gateway-routed dashboard (`/`, `/dependencies`, `/services`) |
| `/healthz` | Container runtime | Liveness; does not contact Docker |
| `GET /api/dashboard` | Administrators, automation | Project metadata plus aggregate and per-service CPU/memory |
| `GET /api/services` | Administrators, automation | Containers in this Compose project, with declared `dependencies` |
| `POST /api/service/<id>/{start,stop,restart}` | Administrators, automation | Lifecycle control; requires the `X-Overseer-CSRF: 1` header |

## Data ownership

Stateless. Overseer holds no data of its own beyond what it reads live from
the Docker daemon on each request.

## Configuration

| Setting | Purpose | Required | Secret | Owner | Safe development value |
| --- | --- | --- | --- | --- | --- |
| `OVERSEER_DOMAIN` | Public dashboard hostname | Yes | No | Service owner | `overseer.localhost` |
| `OVERSEER_UPSTREAM` | Gateway upstream address | Yes | No | Service owner | `overseer:8765` |
| `OVERSEER_COMPOSE_PROJECT` | Compose project Overseer discovers and controls | No | No | Service owner | `nexus-development` |

`OVERSEER_DOMAIN`/`OVERSEER_UPSTREAM` are set on the gateway in the root
`compose.yml`, the same way `STATUS_DOMAIN`/`STATUS_UPSTREAM` are. Overseer
detects the Compose project automatically from its own container label, so
`OVERSEER_COMPOSE_PROJECT` is set to the matching default only for
explicitness; it exists as an override in case automatic detection is ever
unavailable (for example, running the image outside Compose). None of these
values are secrets, and there is no service-level `.env.example` here for the
same reason `website` doesn't have one for its gateway-facing variables.

## Local composition

Compose service: `overseer`

Network: `nexus-system`

Public route: gateway only; the container publishes no host port.

```sh
make overseer
docker compose ps overseer
```

## Development

```sh
make overseer
curl http://overseer.localhost/healthz
make gateway-test
```

Open `http://overseer.localhost` to see the project overview, dependency
graph (`/dependencies`), and lifecycle controls (`/services`). Exercise a
lifecycle action against a non-critical service, for example:

```sh
curl --header "X-Overseer-CSRF: 1" \
  --request POST \
  http://overseer.localhost/api/service/nexus-development-website-1/restart
```

## Deployment and release

The development composition runs the patch-floating upstream
`ghcr.io/pykhaled/overseer:3.0` image directly; no image is built from this
repository. Patch releases stay within the 3.0 line; review minor or major
upgrades deliberately.

## Security and operations

Overseer has no built-in authentication, and mounting
`/var/run/docker.sock` gives it access equivalent to administrative control of
the Docker host: it can inspect every container, not only this project's, and
anyone who can reach the dashboard can start, stop, or restart this project's
services. Treat `http://overseer.localhost` as an administrative surface:

- The default gateway route (see `system/system-gateway/README.md`) is plain
  HTTP with no authentication, matching every other `.localhost` route in this
  repository. It is safe only on a trusted local network.
- Lifecycle POST requests require the `X-Overseer-CSRF: 1` header. The
  gateway's default proxy configuration forwards arbitrary request headers
  without modification, so this protection is preserved end to end; do not
  strip or rewrite headers on this route.
- Do not publish the gateway, or this route specifically, to an untrusted
  network without adding authentication and TLS in front of it first.

### Production access (draft, not implemented)

No authenticated overlay ships with this capability yet — see "Known gaps."
The intended approach, sketched here so a future implementation has a known
starting point rather than an open question:

- Reuse the existing OAuth2 Proxy `auth_request` pattern built for the API
  route: `system/system-gateway/templates-auth/{30-api,31-api-tls,oauth2-api.inc}.template`
  and `docs/compose/templates/compose.api-auth.example.yml`.
- Add `system/system-gateway/templates-auth/40-overseer.conf.template`,
  `41-overseer-tls.conf.template`, and `oauth2-overseer.inc.template`,
  proxying to `${OVERSEER_UPSTREAM}` with the same `auth_request` flow and no
  rate limiting (not warranted for a low-traffic admin dashboard).
- Add a documentation-only `compose.overseer-auth.example.yml` with its own
  `oauth2-proxy-overseer` service — a separate OIDC client ID, cookie secret,
  and redirect URL (`http://overseer.localhost/oauth2/callback`) from the
  API's oauth2-proxy, so the two protected routes don't share session state.
- Register a `development-overseer-auth` mode in `docs/compose/README.md`,
  matching the existing TLS and API-auth modes.

## Replacement contract

A replacement observability implementation must deliberately migrate:

- the stable dashboard route and its discovery scope (this Compose project
  only);
- the dependency-graph semantics (declared `depends_on`, not inferred
  topology);
- lifecycle-control semantics and their CSRF protection; and
- the Docker-socket privilege boundary and any authentication layered in
  front of it.

## Known gaps

| Gap | Risk | Owner | Target or review date |
| --- | --- | --- | --- |
| No authenticated production overlay exists yet (see "Production access" above) | The dashboard cannot be safely exposed beyond a trusted local network | [#26](https://github.com/PyKhaled/Nexus/issues/26) | Unscheduled |
| No production/hardened Nexus Assembler blueprint selects this capability | Prevents the Assembler from producing a policy-passed deployment package that silently exposes an unauthenticated Docker-socket-equivalent surface | [#26](https://github.com/PyKhaled/Nexus/issues/26) | Blocked by access and socket isolation |
| Docker-socket access is host-wide, not scoped to this Compose project | A vulnerability in Overseer would expose more than Nexus's own containers | [#26](https://github.com/PyKhaled/Nexus/issues/26) | Unscheduled |
| The socket-exposure incident runbook is desk-reviewed but has not been exercised | Actual containment and evidence behavior may differ during an incident | [Socket-exposure runbook](docs/runbooks/overseer-socket-exposure-incident.md), [#28](https://github.com/PyKhaled/Nexus/issues/28) | Exercise in an authorized disposable environment |
