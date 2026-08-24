# Initialize a Missing Keycloak Database

Use this runbook when `keycloak-db` is healthy but Keycloak repeatedly exits
with `database "keycloak" does not exist`.

The official PostgreSQL image applies `POSTGRES_DB` only when it initializes an
empty data directory. A data directory created before the Keycloak database was
declared will not be changed automatically.

## Verify the condition

From the repository root:

```sh
docker compose logs --tail=100 keycloak
docker compose exec -T keycloak-db sh -lc \
  'PGPASSWORD="$POSTGRES_PASSWORD" psql -U "$POSTGRES_USER" -d postgres -Atc \
  "select datname from pg_database where datistemplate = false order by datname"'
```

Continue only when the log reports the missing `keycloak` database and the
database list does not contain `keycloak`.

## Create the database without replacing existing data

```sh
docker compose exec -T keycloak-db sh -lc \
  'PGPASSWORD="$POSTGRES_PASSWORD" createdb -U "$POSTGRES_USER" \
  -O "$POSTGRES_USER" keycloak'
docker compose restart keycloak
```

Do not delete `system/system-auth/system-auth-db/data/` to solve this condition;
that would also delete every database already stored there.

## Verify recovery

```sh
docker compose ps keycloak keycloak-db
curl --fail http://auth.localhost/realms/nexus/.well-known/openid-configuration
```

Both containers must become healthy and the discovery endpoint must return an
OIDC configuration document. If the database already exists or Keycloak still
fails, stop and diagnose the new log message rather than rerunning `createdb`.
