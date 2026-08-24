# Authentication Stack Runbooks

Operational runbooks for the authentication stack belong in this directory.
Keep Keycloak and its private PostgreSQL dependency together because they share
an operational lifecycle and owner.

Add runbooks here for realm and client administration, database backup and
restore, credential rotation, upgrades, and authentication incidents. Link
each new runbook from this file.

## Runbooks

- [Initialize a missing Keycloak database](postgres-database-initialization.md)
