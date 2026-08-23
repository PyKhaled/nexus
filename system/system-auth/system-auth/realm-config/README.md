# Realm config

Realm exports live here and are mounted read-only into the container at
`/opt/keycloak/data/import` (see the root `compose.yml`),
not baked into the image. This lets realm/client changes ship without a
rebuild and keeps old exports from lingering in image layers.

## Re-exporting

```sh
docker compose -f compose.yml \
  exec keycloak /opt/keycloak/bin/kc.sh export \
  --file /tmp/nexus-realm.json --realm nexus

docker compose -f compose.yml \
  cp keycloak:/tmp/nexus-realm.json \
  system/system-auth/system-auth/realm-config/nexus-realm.json
```

## Before committing an export

Realm exports include client secrets and user federation credentials in
plaintext. Scrub or replace with placeholders before committing:

- every `"secret"` field under `clients[]`
- `components` entries for user federation / DB federation providers
- any SMTP credentials under `smtpServer`

The checked-in `nexus-realm.json` is intentionally a development placeholder.
Its client secret must match `OIDC_CLIENT_SECRET` when the protected gateway
profile is used.
