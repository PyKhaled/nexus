# Authentication Capability

Status: Partial development implementation

Owner: Unassigned

Implementation: Keycloak 24.0.1 and PostgreSQL 16

## Capability

Provide product identity, sign-in, token issuance, and identity administration.
The current stack supplies a development realm and client for local integration.

The capability does not own product-domain authorization decisions. Product
roles, permissions, tenant rules, and resource policies must be defined by the
business capabilities that consume identity.

## Stack

```text
authentication capability
|-- keycloak          primary identity runtime
`-- keycloak-db       private PostgreSQL dependency
```

The database is private to this stack and must not be used by other product
capabilities.

## Interfaces

| Interface | Consumer | Current contract |
| --- | --- | --- |
| `http://auth.localhost` | Browsers, applications, administrators | Gateway-routed Keycloak HTTP interface |
| OIDC realm endpoints | Product applications | Development realm `nexus` |
| Keycloak administration | Identity administrators | Keycloak administrative interface |

## Configuration

- Keycloak settings: `system-auth/.env.example`
- PostgreSQL settings: `system-auth-db/.env.example`
- Development realm: `system-auth/realm-config/nexus-realm.json`
- Optional providers and themes: `system-auth/providers/` and
  `system-auth/theme/`

All `change-me` values are isolated-development placeholders. Shared
environments must supply unique external secrets and reviewed hostname,
redirect, origin, bootstrap-administrator, and database settings.

## Local composition

Compose services: `keycloak`, `keycloak-db`

Network: `nexus-system`

Public route: gateway only

Persistent data: `system-auth-db/data/`

Start and inspect the stack from the repository root:

```sh
make auth
docker compose ps keycloak keycloak-db
```

## Operations and data

Keycloak readiness is checked before the stack is treated as healthy.
PostgreSQL uses `pg_isready`. Backup, restore, upgrade, production clustering,
alerting, and recovery procedures are not yet implemented.

For an existing PostgreSQL data directory that predates the `keycloak`
database declaration, follow
[`docs/runbooks/postgres-database-initialization.md`](docs/runbooks/postgres-database-initialization.md)
instead of deleting the data directory.

## Replacement contract

A replacement identity implementation must deliberately migrate:

- user and credential ownership;
- supported authentication flows;
- issuer, discovery, token, claim, and session behavior;
- client identifiers, redirects, and origins;
- administrative access and auditability;
- product role and permission integration; and
- identity data export, migration, recovery, and retirement.

## Known gaps

- No product personas, tenants, roles, or authorization model.
- No approved shared-environment secret delivery.
- No backup, recovery, clustering, alerting, or upgrade runbooks.
- Development realm credentials and clients are intentionally insecure.
