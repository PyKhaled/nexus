# Docker Compose Modes

The repository root [`compose.yml`](../../compose.yml) is the only active
Compose definition. It is the source of truth for the local development
environment and is the file used by every `make` target.

Files under [`templates/`](templates/) are documentation examples. They are
not loaded automatically and are not part of the default development workflow.

Target-specific product compositions are generated from the catalogs and
selection policies under [`composition/`](../../composition/). The manual
overlays on this page remain useful for focused gateway experiments; they are
not the edition, environment, deployment-target, or assurance model.

## Modes

| Mode | Files | Purpose |
| --- | --- | --- |
| `development` | `compose.yml` | Complete local environment over HTTP |
| `development-tls` | `compose.yml` + `compose.tls.example.yml` | Local HTTPS testing |
| `development-api` | `compose.yml` + `compose.api.example.yml` | Add an unprotected route for an implemented API service |
| `development-api-tls` | Root file plus TLS, API, and API-TLS examples | Add HTTP and HTTPS routes for an implemented API service |
| `development-auth` | `compose.yml` + `compose.api-auth.example.yml` | Test OIDC protection for the API route |
| `development-secure` | Root file plus all three gateway examples | Test HTTPS and OIDC together |

`development` is the supported default. The other modes are examples for
intentional local testing; they are not production configurations.

## Default development

Start every runnable development component:

```sh
docker compose up -d --build
```

This starts:

- NGINX gateway;
- Keycloak and its PostgreSQL database;
- WordPress and its MySQL database; and
- Kener with its private Redis dependency and persistent SQLite data.

No API route or product API is declared by default. The reusable service
scaffold lives under `templates/service/`; it is not a product capability and
is not declared in `compose.yml`.

## Using an example overlay

The examples may be inspected directly or applied explicitly. For TLS testing:

```sh
docker compose \
  -f compose.yml \
  -f docs/compose/templates/compose.tls.example.yml \
  config
```

For API authentication testing:

```sh
docker compose \
  -f compose.yml \
  -f docs/compose/templates/compose.api-auth.example.yml \
  config
```

The API examples configure gateway routing but do not invent a product API.
The applied composition must also declare an `api` service or override
`API_UPSTREAM` with another reachable implementation.

For the combined secure-development mode, order matters:

```sh
docker compose \
  -f compose.yml \
  -f docs/compose/templates/compose.tls.example.yml \
  -f docs/compose/templates/compose.api-auth.example.yml \
  -f docs/compose/templates/compose.api-auth-tls.example.yml \
  config
```

Replace `config` with `up -d --build` only when intentionally running that
mode. TLS requires `fullchain.pem` and `privkey.pem` in
`system/system-gateway/ssl/`, unless `GATEWAY_TLS_DIR` points elsewhere.

## Standalone stack examples

The following files document how a component group could be extracted from the
main development environment:

- `compose.auth-stack.example.yml`: Keycloak and PostgreSQL;
- `compose.website-stack.example.yml`: WordPress and MySQL.

They are references for deployment design and troubleshooting. The default
workflow does not use them. They expect the `nexus-system` network to have
already been created by the root development environment.

## Deployment environments

Do not treat any example as a production Compose file. A staging or production
definition must provide, at minimum:

- externally managed secrets instead of development placeholders;
- pinned and approved image versions;
- persistent storage and backup policies;
- real domains and certificates;
- resource limits, monitoring, and recovery behavior; and
- an explicit image build and release strategy.

Use `bin/nexus-compose` to create environment-specific packages, then publish
the reviewed package through the deployment repository or platform that owns
artifact promotion and runtime controls. Keep root `compose.yml` focused on
reproducible local development until the generated development composition is
formally adopted as authoritative.
