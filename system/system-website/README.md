# Website Capability

Status: Partial

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Implementation type: stack

Technology: WordPress `7.0-apache` with MySQL `8.0`

## Capability

Provide the Nexus public website through the system gateway. WordPress is the
current replaceable implementation; its MySQL database is a private dependency
owned and operated with the website stack.

## Scope

Owns:

- public website content and administration;
- WordPress application files, uploaded media, themes, and plugins stored in
  the website data volume;
- the private WordPress MySQL database; and
- website-specific maintenance, backup, recovery, and upgrade procedures.

Does not own:

- the gateway's public-port or route policy;
- authentication for other Nexus capabilities; or
- a general-purpose database shared with another stack.

## Implementation

```text
website capability
|-- website       WordPress application and persistent content
`-- website-db    private MySQL database
```

The root `compose.yml` is the active local definition. There is no standalone
Compose file in this directory and neither website service publishes a host
port.

## Interfaces

| Interface | Consumer | Contract |
| --- | --- | --- |
| `http://localhost/` | Visitors | Public website routed through the gateway |
| `http://localhost/wp-admin/` | Website administrators | WordPress administration through the gateway |
| `website:80` | Gateway only | Private HTTP upstream on `nexus-system` |
| `website-db:3306` | WordPress only | Private MySQL protocol; no host-published port |

## Data ownership

| Compose volume | Mounted at | Contents |
| --- | --- | --- |
| `wordpress-data` | `website:/var/www/html` | WordPress core/runtime files, plugins, themes, uploads, and generated configuration |
| `website-db-data` | `website-db:/var/lib/mysql` | Private MySQL data for WordPress |

In the default Compose project the Docker volume names resolve to
`nexus-development_wordpress-data` and
`nexus-development_website-db-data`. Do not delete either volume to recover an
outage. Use the [database and content recovery runbook](docs/runbooks/website-database-and-content-recovery.md).

## Configuration

| Setting | Purpose | Required | Secret | Safe development value |
| --- | --- | --- | --- | --- |
| `APP_DOMAIN` | Gateway hostname for the website | No in local development | No | `localhost` |
| `MYSQL_DATABASE` | WordPress database name | Yes | No | `wordpress` |
| `MYSQL_USER` | WordPress database user | Yes | No | `wordpress` |
| `MYSQL_PASSWORD` | WordPress database-user password | Yes | Yes | Isolated `change-me` placeholder only |
| `MYSQL_ROOT_PASSWORD` | MySQL administrative password | Yes | Yes | Isolated `change-me` placeholder only |

Root Compose derives `WORDPRESS_DB_HOST`, `WORDPRESS_DB_NAME`,
`WORDPRESS_DB_USER`, and `WORDPRESS_DB_PASSWORD` from the `website-db` service
and the `MYSQL_*` values above. The other WordPress/site variables that used to
appear in this directory's environment example were not consumed by the active
Compose definition and have been removed.

For private local values:

```sh
cp system/system-website/.env.example system/system-website/.env
# Replace every change-me value in the private .env file.
make collect-secrets
```

`make collect-secrets` writes the ignored root `secrets.env`; root Make targets
load it automatically. Do not commit either private environment file or
`secrets.env`.

## Local composition

Compose services: `website`, `website-db`

Network: `nexus-system`

Public route: gateway only

From the repository root:

```sh
make website
docker compose ps gateway website website-db
curl --fail --show-error http://localhost/
```

Use `make website-dbshell` for an interactive database session. The default
workflow does not use `docker-compose`, a directory-local Compose file, or host
port `8080`.

## Deployment and release

Local development runs `wordpress:7.0-apache` and `mysql:8.0`. Reviewed
self-hosted production and high-assurance blueprints replace those tags with
required private-registry digest references. Image selection alone does not
provide backup, recovery, resource limits, external secret management, or
production approval.

## Security and operations

- MySQL is private to the stack and must never publish a host port.
- Development placeholders are allowed only on an isolated workstation.
- WordPress administrator credentials are created through WordPress itself;
  the active root Compose file does not consume `WORDPRESS_ADMIN_*` variables.
- Treat plugins and themes as executable code. Review their source and version
  before installation or upgrade.
- Use the [website runbook index](docs/runbooks/README.md) for maintenance,
  extension failures, backup, and recovery.

## Replacement contract

A replacement website implementation must deliberately migrate:

- the stable gateway route and public content URLs;
- pages, posts, media, users, roles, and administrative access;
- theme/plugin behavior and any generated configuration;
- database/content backup, restore, retention, and upgrade procedures; and
- private dependency and no-host-port boundaries.

## Known gaps

| Gap | Risk | Owner | Target or review date |
| --- | --- | --- | --- |
| Accountable website ownership is unassigned | Maintenance and risk decisions lack a confirmed authority | [#16](https://github.com/PyKhaled/Nexus/issues/16) | Unscheduled |
| Root Compose has no application-level WordPress health check | Container running state does not prove the site can serve a page | Unassigned | None |
| Backup/restore and upgrade runbooks are desk-reviewed but not exercised | Actual recovery behavior may differ from the written procedure | Unassigned | Exercise before relying on them outside local development |
| Local development falls back to `change-me` database passwords | Accidental shared exposure would use known credentials | Unassigned | Replace through `secrets.env` before any non-isolated use |
