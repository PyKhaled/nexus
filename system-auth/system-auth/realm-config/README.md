# Realm config

Realm exports live here and are mounted read-only into the container at
`/opt/keycloak/data/import` (see the `keycloak` service in `compose.yml`),
not baked into the image. This lets realm/client changes ship without a
rebuild and keeps old exports from lingering in image layers.

## Re-exporting

```
docker compose exec keycloak /opt/keycloak/bin/kc.sh export \
  --dir /opt/keycloak/data/import --realm coursemology
```

## Before committing an export

Realm exports include client secrets and user federation credentials in
plaintext. Scrub or replace with placeholders before committing:
- every `"secret"` field under `clients[]`
- `components` entries for user federation / DB federation providers
- any SMTP credentials under `smtpServer`
