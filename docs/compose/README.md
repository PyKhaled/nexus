# Docker Compose Modes

The repository root [`compose.yml`](../../compose.yml) is the only active Compose definition. It is the source of truth for the local development environment and is the file used by every `make` target.

Files under [`templates/`](templates/) are documentation examples. They are not loaded automatically and are not part of the default development workflow.

## Modes

| Mode | Files | Purpose |
| --- | --- | --- |
| `development` | `compose.yml` | Complete local environment over HTTP |
| `development-tls` | `compose.yml` + `compose.tls.example.yml` | Partial local HTTPS testing for website, authentication, and reserved API routes |
| `development-auth` | `compose.yml` + `compose.api-auth.example.yml` | Test the OIDC boundary in front of the reserved API route |
| `development-secure` | Root file plus all three gateway examples | Test that partial HTTPS surface and API OIDC boundary together |

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

The API upstream remains reserved as `api:8000`. `system-service` is a
repository scaffold rather than a runnable Nexus API, so it is not declared in
`compose.yml`.

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

## Example boundaries

- `compose.tls.example.yml` mounts HTTPS virtual hosts for the default,
  website, authentication, and reserved API hosts. It does not mount the
  checked-in status or Overseer TLS templates. Because it enables the global
  HTTP-to-HTTPS redirect, `status.localhost` and `overseer.localhost` redirect
  to the default HTTPS server and return `404` in this example.
- `compose.api-auth.example.yml` adds OAuth2 Proxy and protects the reserved API
  route. No runnable `api` service exists, so the example can exercise the OIDC
  boundary but cannot prove an authenticated application request end to end.
- The example credentials, cookie secret, HTTP issuer/redirect URLs, and
  optional certificates are local test inputs, not shared-environment secrets
  or production controls.
- Overseer remains an unauthenticated Docker-socket administration surface.
  Adding TLS alone does not make it safe for an untrusted network; its active
  hardening work is tracked in
  [issue #26](https://github.com/PyKhaled/Nexus/issues/26).

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
