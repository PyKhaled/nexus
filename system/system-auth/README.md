# Nexus Keycloak image

This image builds and runs without custom extensions. The `providers/` and
`theme/` directories contain placeholders; add provider or theme JAR files to
either directory and rebuild when extensions are available.

The placeholder realm in `realm-config/nexus-realm.json` creates a
`nexus` realm and confidential `nexus-api` client for local integration with
OAuth2 Proxy. Its client secret is intentionally insecure. Replace the secret,
redirect URIs, origins, hostname, database password, and bootstrap password
before using the stack outside an isolated development machine.

Keycloak imports realm files only when the realm does not already exist. To
apply later changes, use Keycloak administration or recreate the development
database intentionally.
