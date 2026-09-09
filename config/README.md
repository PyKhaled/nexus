# Runtime configuration

Use Make as the interface. Bash loads ordinary private files; Docker Compose
explicitly maps values into the services that consume them. No schema service,
Vault dependency, or additional CLI is required.

## Development

```sh
make config-init
make config-path
# Edit .env/development/config.env and .env/development/secret.env privately.
make config-check
make compose-check
make up
```

`config-init` copies the Nexus templates from `config/compose/` with mode 600
and never overwrites an existing file. These templates describe the current
Nexus Compose stack; application-specific templates are not loaded automatically.

The root Compose file still starts without runtime files using its development
defaults. If either runtime file exists, both must exist. `config-check` always
requires both. It checks syntax and file permissions, not required credentials,
credential validity, or production readiness. `compose-check` additionally runs
Compose validation without printing the resolved values. Neither starts Docker
containers. Run `make config-test` for isolated helper tests and `make config-compose-test`
for Compose mapping and secret-isolation tests (requires Ruby and Compose).

## File format and precedence

Use one `KEY=value` entry per line, with no spaces around the key or equals sign.
Blank lines and full-line `#` comments are allowed. Values may have one pair of
surrounding single or double quotes. Everything inside the value is literal:
`$`, backticks, backslashes, and `#` are not expanded or executed. There are no
inline comments, escape sequences, multiline values, or `export` statements.
Duplicate keys within a file are errors. Diagnostics never print values.

Order, from lowest to highest priority:

1. Development defaults in Compose.
2. Existing development `system/system-auth/.env`, then
   `system/system-auth-db/.env`, then root `secrets.env` (or `SECRETS_ENV`).
3. Runtime `config.env`.
4. Runtime `secret.env`.
5. Explicit exported process environment, including empty values.

The legacy files use this same literal syntax and permission check when loaded
through Make. Review them if they previously relied on dotenv expansion.
Production never loads these development legacy files. Existing
`make collect-secrets` remains available; migration is manual and originals
are not rewritten. Once copied and checked, archive legacy files outside the
checkout so omitted keys do not keep falling back to old values.

Both runtime files must be regular, non-symlink files readable by the invoking
user, with mode 600 or 640 (or stricter readable permissions). Keep secrets only in `secret.env`; this convention
is documented rather than inferred by a schema. Shell/loader control keys
such as PATH, HOME, BASH_ENV, and NEXUS_* are reserved. Set runtime selection
variables outside the files.

The helper exports values only to the child process. Compose receives
`--env-file /dev/null` to avoid an implicit `.env` lookup and a second dotenv
interpretation. This also permits `.env/` to be a directory. Prefer Make over
calling Compose directly when using these files. Compose does not copy the
whole host environment into containers: service `environment` mappings select
which keys they receive. The development-only `compose.config.yml` overlay supplies Keycloak mappings
when Make uses the root model; generated packages keep their own authentication
contract. Keycloak's existing service env-files are retained for
additional component-specific settings; mapped keys take precedence.

Use the same password for `KC_DB_PASSWORD` and `POSTGRES_PASSWORD`. WordPress
and MySQL already consume the same `MYSQL_PASSWORD` key. Administrative MySQL
credentials are mapped only to the database container.

## Mounted WordPress / MySQL secrets

The optional `compose.secrets.yml` overlay replaces the WordPress/MySQL password
environment variables with `_FILE` references. It requires Compose support for
`!reset` (verified locally with Compose v5.5.0). It is an overlay for the root
development model, not a complete production deployment.

Create two private files, each containing only its password, on the Docker host.
Do not put `KEY=` in these files. Store them outside Git, for example under
`/etc/nexus/secrets/`, then set absolute paths in runtime `config.env`:

```dotenv
MYSQL_PASSWORD_FILE=/etc/nexus/secrets/mysql_password
MYSQL_ROOT_PASSWORD_FILE=/etc/nexus/secrets/mysql_root_password
```

```sh
make compose-check COMPOSE_SECRETS=compose.secrets.yml
make up COMPOSE_SECRETS=compose.secrets.yml
```

Pass the same overlay to subsequent lifecycle commands. The website receives
only the application password; MySQL receives both passwords. Kener and
Keycloak retain their explicit environment mappings; `_FILE` is image-specific,
not a Docker-wide feature. Do not retain WordPress/MySQL passwords in `secret.env`
when using the overlay.

Compose mounts these host files into `/run/secrets/`; it does not encrypt their
contents on disk. Set host ownership and permissions so the Docker daemon and
intended container user can read the files. For remote Docker engines, the
source paths must exist on the daemon host. Changing a password file does not
rotate an existing database password: update the database credential and
coordinate application restarts using the service rotation runbook.

See Docker's [Compose secrets documentation](https://docs.docker.com/compose/how-tos/use-secrets/).

## Production paths

`ENV=production` selects `/etc/nexus/config.env` and `/etc/nexus/secret.env`.
It does not turn the root development Compose model into a production model.
The Make lifecycle targets reject that combination. Supply the Compose file
from a reviewed production deployment package explicitly.

Create `/etc/nexus` once as an administrator, owned by the deployment account
with mode 700 (or use a deployment group and mode 750). Then run as that account:

```sh
make config-init ENV=production
# Populate the files privately with deployment-specific values.
make config-check ENV=production
make compose-check ENV=production COMPOSE_FILE=/opt/nexus/deployment/compose.yml
make up ENV=production COMPOSE_FILE=/opt/nexus/deployment/compose.yml
```

`up` requests local builds only in development. Generated production package
requirements still apply, including any private `AUTH_ENV_FILE`, image values,
TLS assets, and external controls. Configuration initialization does not provide
these or attest to their correctness.

Override the directory for either environment:

```sh
make config-path ENV=production NEXUS_CONFIG_DIR=/srv/nexus/config
```

The runtime files belong on the host, never in an image. Do not dump resolved
Compose configuration or use shell tracing when handling real credentials.

## Docker containers and Swarm

The helper can supply interpolation variables to another explicitly written
Docker command, for example `bash scripts/config.sh run -- docker run --rm
--env APP_SETTING image`. Only explicitly forwarded variables enter that
container. Docker's own `--env-file` has different parsing rules; do not assume
it implements the literal/quoted format above.

Swarm deployment is intentionally not implemented yet. A future `make deploy`
needs a separate reviewed stack definition, versioned Swarm configs/secrets,
per-service grants, and a rotation procedure. Do not feed `compose.secrets.yml`
to `docker stack deploy`: Compose overlay tags and host-file secret delivery
are not the Swarm lifecycle. See Docker's [interpolation documentation](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
for the Compose-only `.env` behavior.
