# Gateway Capability

The gateway is the public edge capability for the Nexus reference system. Its
current implementation uses NGINX for host-based routing, reverse proxying,
runtime Docker DNS resolution, and shared request policies.

The capability owns public HTTP entry points and routing policy. It does not
own application behavior, identity data, website content, or product-domain
authorization decisions.

## Configuration

| Path | Purpose |
| --- | --- |
| `nginx.conf` | Global workers, logging, Docker DNS, and includes |
| `conf.d/` | Static default and health endpoints |
| `templates/` | Default environment-rendered website, identity, and status routes |
| `templates-api/` | Optional unprotected API route |
| `snippets/` | Reusable proxy, timeout, and security policies |
| `ssl/` | Runtime TLS certificates; never included in the image |

The official NGINX image renders every `templates/*.template` file into
`conf.d/` at container startup. Routes resolve Docker service names at request
time, so the gateway can start before its upstream applications.

## Default routes

| URL | Default Docker upstream |
| --- | --- |
| `http://app.localhost` | `website:80` |
| `http://auth.localhost` | `keycloak:8080` |
| `http://status.localhost` | `status:3000` |
| `http://localhost/healthz` | Gateway liveness |
| `http://localhost/readyz` | Gateway configuration readiness |

The default composition does not declare an API route because no product API
is implemented. The optional API example mounts
`templates-api/30-api.conf.template` and applies a per-client rate limit. Apply
it only with a composition that declares the configured API upstream.

The documented API-auth Compose example mounts an OAuth2 Proxy `auth_request`
route while leaving the application and identity routes public.

## Run with Docker Compose

From the repository root:

```sh
make gateway
make gateway-test
make logs
```

Copy `system/system-gateway/.env.example` to the repository root as `.env` to
customize domains, upstreams, rate limits, or published ports. Compose defaults
make this optional for local development.

All routed applications must join the external Docker network named
`nexus-system`. The `make website`, `make auth`, and `make status` commands
start the gateway first and then attach their services to that network.

## Build and validate

Build directly from this directory:

```sh
docker build -t nexus/system-gateway:local .
```

Validate or inspect the environment-rendered configuration:

```sh
make gateway-test
make gateway-config
```

## Apply configuration changes

Configuration is baked into the image. Rebuild and recreate the gateway after
changing `nginx.conf`, a route template, or a shared snippet:

```sh
make gateway
```

`make gateway-reload` validates and reloads the currently running filesystem;
it is intended for deployments that mount generated configuration at runtime.

If a request returns `502`, check the configured upstream name, internal port,
container health, and `nexus-system` network membership.

## TLS certificates

TLS private keys are deployment secrets and are intentionally excluded from
the image. Default development uses HTTP. For local TLS testing, place
`fullchain.pem` and `privkey.pem` in `system/system-gateway/ssl/` and follow
the secure-development composition example in `docs/compose/README.md`.

The TLS example under `docs/compose/templates/` mounts the certificate
directory read-only, publishes port `443`, renders HTTPS routes, and redirects
the configured HTTP domains to HTTPS. Override `GATEWAY_TLS_DIR`,
`TLS_CERTIFICATE`, and `TLS_CERTIFICATE_KEY` when certificates use different
locations.

## API authentication placeholders

The API-auth example under `docs/compose/templates/` uses OAuth2 Proxy and
Keycloak OIDC. It exposes OAuth2 Proxy only inside `nexus-system`; NGINX serves
`/oauth2/*`, checks sessions through an internal auth subrequest, and forwards
authenticated user, email, group, and token headers to the API. See
`docs/compose/README.md` for example composition order. Values in `.env.example`
are functional local placeholders, not production secrets.

## Replacement contract

A replacement gateway implementation must preserve or deliberately migrate:

- configured public domains and routes;
- forwarding and client-address headers;
- health and readiness endpoints;
- security-header behavior;
- runtime handling for unavailable upstreams;
- optional TLS and authenticated API routes; and
- the rule that backend services remain internal by default.
