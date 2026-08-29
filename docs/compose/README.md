# Docker Compose Modes

The repository root [`compose.yml`](../../compose.yml) is the only active Compose definition. It is the source of truth for the local development environment and is the file used by every `make` target.

Files under [`templates/`](templates/) are documentation examples. They are not loaded automatically and are not part of the default development workflow.

## Modes

| Mode | Files | Purpose |
| --- | --- | --- |
| `development` | `compose.yml` | Complete local environment over HTTP |
| `development-tls` | `compose.yml` + `compose.tls.example.yml` | Local HTTPS testing |
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
- keycloak and its PostgreSQL database;
- wordpress website;
- Kener status page and its Redis dependency; and
- overseer.
<!-- 
The API upstream remains reserved as `api:8000`. `system-service` is currently a repository scaffold rather than a runnable Nexus API, so it is not declared in `compose.yml`. 
-->
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

Create environment-specific definitions in the deployment repository or
platform that owns those concerns. Keep `compose.yml` focused on reproducible
local development.
