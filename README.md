# Nexus

Nexus is a working reference implementation of a composable SaaS product
system. It assembles replaceable shared capabilities with product-specific
business capabilities through one root development composition.

The current implementation is an initial foundation slice: an NGINX gateway,
a WordPress public website stack, a Keycloak identity stack, and a Kener service
status stack. Client, administration, notification, help-center, integration,
and business-domain capabilities are not yet implemented.

## Product-system model

The repository is also being used to explore a broader, technology-neutral
model for structuring, developing, releasing, operating, and governing
composable software products. The proposal is deliberately separate from the
current runtime description and remains a draft for review.

Start with the
[Nexus Product System Wiki](https://github.com/PyKhaled/Nexus/wiki) for the
concept brief, reference architecture, draft standard, policies, templates,
machine-readable manifest example, and adoption checklist. The wiki is
maintained as a separate Git repository in the local `wiki/` workspace.

## Architecture

```text
browser / API client
        |
        v
Nexus System Gateway (NGINX :80)
        |
        +-- app.localhost  --> website:80
        +-- auth.localhost --> keycloak:8080
        +-- status.localhost --> status:3000
```

The gateway can run without its upstream applications. Docker service names
are resolved when requests arrive, so unavailable services return `502`
without preventing the gateway from starting.

## Components

| Component | Purpose |
| --- | --- |
| `system/system-gateway/` | Gateway capability; currently implemented with NGINX |
| `system/system-website/` | Public website capability; currently WordPress and MySQL |
| `system/system-auth/` | Authentication capability; currently Keycloak and PostgreSQL |
| `system/system-status/` | Service-status capability; currently Kener, Redis, and SQLite |
| `templates/service/` | Runnable starting template for a future owned service repository |
| `product-system.yaml` | Capability inventory, implementation selection, and maturity |
| `composition/` | Catalogs, editions, deployment policies, schemas, and examples |
| `bin/nexus-compose` | Deterministic product-composition generator |

## Generate a product composition

The root `compose.yml` remains the reviewed development reference while the
generator is introduced. Generate an equivalent development package with:

```sh
make composition-plan
make composition-generate
make composition-validate
```

For a different edition, target, environment, assurance profile, or component
selection, create a selection interactively:

```sh
bin/nexus-compose configure --output composition/selection.yaml
```

See [`composition/README.md`](composition/README.md) for the model, generated
artifacts, private-registry flow, and high-assurance boundaries.

## Start the development environment

The root `compose.yml` is the active definition for local development. Its
defaults work without an environment file:

```sh
make up
curl http://localhost/healthz
```

This starts the gateway, Keycloak with PostgreSQL, WordPress with MySQL, and
Kener with Redis and SQLite. The service template is not a product capability
and is not started by Compose.

Expected response:

```text
ok
```

The root Make targets load `secrets.env` automatically when it exists. Set
`SECRETS_ENV=/path/to/another.env` to use a different root secrets file.

Generate `secrets.env` from every service-level `.env` file under `system/`:

```sh
make collect-secrets
```

The collector stops if two files define the same key, preventing one service's
value from silently replacing another's.

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
make gateway
make status
```

The website and Keycloak stacks default to checked-in development placeholders.
Create private Keycloak `.env` files and override the root `secrets.env` values
before any shared deployment. Custom Keycloak provider and theme JARs are
optional; place them in `system/system-auth/system-auth/providers/` or
`theme/` when available.

## Local URLs

| Endpoint | URL |
| --- | --- |
| Gateway health | `http://localhost/healthz` |
| Website | `http://app.localhost` |
| Authentication | `http://auth.localhost` |
| Service status | `http://status.localhost` |

## Gateway operations

```sh
make gateway-test      # validate generated NGINX configuration
make gateway-config    # print the complete generated configuration
make gateway-reload    # reload runtime-mounted config after validation
make logs              # follow gateway logs
```

See `system/system-gateway/README.md` for configuration layout,
troubleshooting, and instructions for adding routes.

## Compose modes and templates

Only `compose.yml` is active and used by the development Make targets. Optional
TLS, OIDC API authentication, combined secure-development, and standalone stack
definitions live under `docs/compose/templates/` as documentation examples.

See `docs/compose/README.md` for the mode names, differences, example commands,
and the additional requirements for staging or production. The examples are
never loaded automatically.

## Runbooks

Operational runbooks are stored with the service or stack that owns them. See
`docs/runbooks/README.md` for the central index and contribution conventions.

## Add another routed capability

1. Attach the service to the Docker network named `nexus-system`.
2. Define its capability, owner, contract, data, and maturity in
   `product-system.yaml`.
3. Add its domain and upstream configuration to `compose.yml`.
4. Add a route template under the appropriate gateway template directory.
5. Rebuild the gateway and run `make gateway-test`.

Backends should expose only their internal application port. In normal
operation, host port `80` belongs exclusively to the gateway. Port `443` is
published only when intentionally applying the documented TLS example.
