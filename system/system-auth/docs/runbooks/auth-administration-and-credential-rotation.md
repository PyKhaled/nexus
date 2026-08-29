# Runbook: Administer Keycloak and rotate credentials

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P1; P0 for suspected credential compromise

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: the local `nexus` Keycloak realm and its dedicated PostgreSQL stack; shared environments require their own identity-change approval

Severity: routine or critical

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Make bounded realm/client administration changes and rotate admin, client, or
database credentials without relying on development bootstrap placeholders.

## Preconditions and safety

- Required access: a named Keycloak administrator, the approved secret store,
  and database administration when rotating the database user.
- Required tools: browser, Docker Compose, and `psql` for database rotation.
- User or data impact: client-secret and database-password changes can stop
  authentication immediately if consumers are not coordinated.
- Destructive or irreversible steps: regenerating a Keycloak client secret
  invalidates the old secret; deleting users/clients is outside this runbook.
- Escalate before proceeding when no second administrator can verify access,
  the affected clients are unknown, or compromise is suspected.

Take and verify a fresh logical database backup using
`auth-database-backup-and-restore.md` before material realm/client changes.
Never put secrets in Git, issue bodies, command history, or evidence logs.

## Detection

- A realm, role, redirect URI, origin, or client change is approved.
- A credential reaches its rotation date.
- A secret or administrator account may have been exposed.

## Procedure: realm or client administration

1. Record the approved change, affected realm/client, expected consumers, and
   rollback values without recording secret values.
2. Sign in to `http://auth.localhost/admin/` with a named administrator.
3. Select the `nexus` realm explicitly; do not make product changes in
   `master`.
4. Change only the approved fields. For redirect URIs and web origins, retain
   the exact scheme, hostname, port, and path required by the consumer.
5. Save, then verify an administrator login and one representative client flow.
6. Review the Keycloak event/admin-event view if enabled; otherwise retain a
   redacted change record.

## Procedure: replace the bootstrap administrator

1. Create or confirm a named administrator with the minimum required realm or
   admin permissions.
2. Sign out and prove the named account can perform a harmless read-only admin
   operation.
3. Disable the bootstrap account only after that independent login succeeds.
4. Remove `KC_BOOTSTRAP_ADMIN_PASSWORD` from shared-environment runtime secret
   injection when the deployment no longer needs first-boot creation. Changing
   the environment variable does not rotate an existing Keycloak user.

## Procedure: rotate a client secret

1. Identify every consumer and schedule a coordinated cutover. Keycloak secret
   regeneration invalidates the previous value immediately.
2. In the `nexus` realm, open the approved confidential client and regenerate
   its credential.
3. Transfer the new value through the approved secret channel and restart or
   reload every consumer.
4. Verify authorization-code/token exchange and one protected request.
5. If a consumer fails, regenerate again if needed and coordinate all
   consumers to the newly active value; do not paste the secret into logs.

## Procedure: rotate the Keycloak database password

The current database role is `keycloak`. If the environment overrides it, stop
and substitute the confirmed role consistently.

1. Open an interactive database shell so the new value is not placed on the
   command line:

   ```sh
   make auth-dbshell
   ```

2. At the `psql` prompt run `\password keycloak`, enter the new approved value,
   and exit with `\q`.
3. Update `KC_DB_PASSWORD` in `system/system-auth/.env` through the approved
   secret process. Keep `POSTGRES_PASSWORD` in
   `system/system-auth-db/.env` consistent for recovery/new initialization;
   changing that environment value alone does not alter an initialized role.
4. Recreate Keycloak without removing PostgreSQL data:

   ```sh
   make auth
   ```

5. Verify readiness and a representative login:

   ```sh
   docker compose ps keycloak keycloak-db
   curl --fail --show-error http://auth.localhost/realms/nexus/.well-known/openid-configuration
   ```

## Success criteria

- Named administrator access remains available.
- Approved client flows succeed with the active configuration/secret.
- Keycloak and PostgreSQL are healthy after database credential rotation.
- No credential value appears in Git, logs, issue comments, or review evidence.

## Rollback or recovery

- Realm/client configuration: restore the recorded prior non-secret values.
- Client secret: Keycloak cannot reactivate the previous generated secret;
  coordinate a new secret to every consumer.
- Database password: use the still-open privileged database session or another
  approved database administrator to run `\password keycloak` again, restore
  the previous application secret, and recreate only Keycloak. If database
  access is lost, escalate; do not delete `system/system-auth-db/data`.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| No named administrator can sign in | Identity owner and incident lead | Realm, last successful access, last change, health/log evidence |
| Client secret may be exposed | Security owner and client owners | Client ID, exposure window/channel, affected environments, rotation state |
| Keycloak cannot authenticate to PostgreSQL | Identity and database operators | Redacted error, role/database names, rotation timeline, backup reference |

## Follow-up

- Record who approved and verified the change, without secrets.
- Review active administrators, clients, redirect URIs, and unused credentials.
- Update consumer inventory before the next rotation.
