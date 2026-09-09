# Nexus

Nexus is a self-hosted application stack fronted by a reusable NGINX edge
gateway. The gateway is the only component that publishes the HTTP port; backend
services communicate over the shared `nexus-system` Docker network.

## Product-system model

The repository is also being used to explore a broader, technology-neutral
model for structuring, developing, releasing, operating, and governing
composable software products. The proposal is deliberately separate from the
current runtime description and remains a draft for review.

Start with the [documentation index](docs/README.md) for current Nexus
architecture and operational material. Planned work and its acceptance
criteria live in [GitHub Issues](https://github.com/PyKhaled/Nexus/issues).
Reusable, technology-neutral product-system guidance is maintained separately
in Engineering OS; this repository records only the Nexus profile, decisions,
implementation, and evidence.


## Architecture

```text
browser / API client
        |
        v
Nexus System Gateway (NGINX :80)
        |
        +-- localhost/         --> website:80
        +-- auth.localhost     --> keycloak:8080
        +-- status.localhost   --> status:3000
        +-- overseer.localhost --> overseer:8765
        +-- api.localhost      --> api:8000
```

The gateway can run without its upstream applications. Docker service names
are resolved when requests arrive, so unavailable services return `502`
without preventing the gateway from starting.

## Components

| Component | Purpose |
| --- | --- |
| `system/system-gateway/` | NGINX edge gateway, routes, and shared policies |
| `system/system-auth/` | Optional Keycloak and PostgreSQL stack |
| `system/system-website/` | Optional WordPress and MySQL stack |
| `system/system-status/` | Optional Kener status page and Redis stack |
| `system/system-overseer/` | Optional Overseer observability and control dashboard |

## Start the development environment

The root `compose.yml` is the active definition for local development. Its
defaults work without an environment file:

```sh
make up
curl http://localhost/healthz
```

This starts the gateway, Keycloak with PostgreSQL, WordPress with MySQL,
Kener with Redis, and Overseer. The reference `system-service` scaffold is
not runnable and is therefore not started by Compose.

Expected response:

```text
ok
```

Use the Make-based runtime configuration workflow when overriding defaults:

```sh
make config-init       # Create private .env/development/{config,secret}.env
make config-path
# Edit the files privately.
make config-check     # Check syntax and permissions
make compose-check    # Validate Compose without printing values
make up
```

Make loads configuration and secrets through a small Bash helper. Existing
component authentication `.env` files and root `secrets.env` remain lower-priority
development inputs. `make collect-secrets` still invokes the Assembler collector
and rejects duplicate keys. Runtime files and values are never sourced as shell
code. See [runtime configuration](config/README.md) for precedence, production
paths, optional mounted WordPress/MySQL secrets, and Docker/Swarm boundaries.

Blueprints may also declare independently versioned source repositories below
`system/`. Repository synchronization is the explicit network step; planning,
validation, and composition never silently clone or fetch dependencies:

```sh
bin/nexus repository sync --blueprint nexus.yaml
bin/nexus repository validate --blueprint nexus.yaml
bin/nexus assemble --blueprint nexus.yaml --output generated/nexus
```

See the [source repository command reference](composition/README.md#source-repositories)
for the declaration schema and pipeline behavior.

Then rebuild and start the environment:

```sh
make up
```

## Start an individual service group

The root Compose file remains the source of truth even when starting only one
part of the environment:

```sh
make website
make auth
make status
make overseer
make gateway
```

The website and Keycloak stacks default to checked-in development placeholders.
Supply deployment-specific credentials through the runtime configuration
workflow before any shared deployment. Custom Keycloak provider and theme JARs are
optional; place them in `system/system-auth/providers/` or
`theme/` when available.

<!-- ## Local URLs -->

<!-- check openapi.json -->

<!-- | Endpoint | URL |
| --- | --- |
| Gateway health | `http://localhost/healthz` |
| Website | `http://localhost/` |
| Authentication | `http://auth.localhost` |
| API | `http://api.localhost` | -->

## Gateway operations

```sh
make gateway-test      # validate generated NGINX configuration
make gateway-config    # print the complete generated configuration
make gateway-reload    # reload runtime-mounted config after validation
make logs              # follow gateway logs
```

See `system/system-gateway/README.md` for configuration layout, troubleshooting, and instructions for adding routes.

## Compose modes and templates

`compose.yml` is the default model used by the development Make targets, with
`compose.config.yml` adding authentication variable mappings.
`compose.secrets.yml` is an opt-in WordPress/MySQL file-secret overlay. Optional
TLS, OIDC API authentication, combined secure-development, and standalone stack
definitions live under `docs/compose/templates/` as documentation examples.

Development container references use patch-floating release-line tags when the
upstream registry publishes them. Kener and OAuth2 Proxy are exact-patch
exceptions because their registries publish full release tags and `latest`, but
no major/minor aliases. Generated production packages replace upstream tags
with required image digests.

See `docs/compose/README.md` for the mode names, differences, example commands,
and the additional requirements for staging or production. The examples are
never loaded automatically.

## Runbooks

Operational runbooks are stored with the service or stack that owns them. See `docs/runbooks/README.md` for the central index and contribution conventions.

## Add another routed service

1. Attach the service to the Docker network named `nexus-system`.
2. Add its domain and upstream configuration to `compose.yml`.
3. Add a route template under `system/system-gateway/templates/`.
4. Rebuild the gateway and run `make gateway-test`.

Backends should expose only their internal application port. In normal
operation, host port `80` belongs exclusively to the gateway. Port `443` is
published only when intentionally applying the documented TLS example.
