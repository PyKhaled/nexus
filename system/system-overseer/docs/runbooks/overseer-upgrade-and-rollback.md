# Runbook: Upgrade or roll back Overseer

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P1

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: local development service `overseer`; non-local use remains blocked by issue #26

Severity: routine, escalating to critical for a security regression

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Replace the stateless Overseer image while retaining an exact rollback image
and verifying project scoping, health, discovery, resource visibility, and
bounded lifecycle control.

## Preconditions and safety

- Required access: repository and Docker Compose operation on a trusted local
  workstation.
- Required tools: Docker, `curl`, and a non-critical test service approved for
  lifecycle verification.
- User or data impact: the dashboard is briefly unavailable; a lifecycle test
  restarts the chosen test service.
- Destructive or irreversible steps: none to Overseer data because it is
  stateless. Restarting another service can interrupt it.
- Escalate before proceeding when the new version changes socket use, project
  scoping, authentication, lifecycle authorization, or CSRF behavior.

## Detection

- Reviewed patch/security update in the supported `3.0` line.
- Planned version change after upstream compatibility review.
- Rollback required after health, discovery, or control regression.

## Diagnosis and preflight

1. Review upstream release/security notes and image provenance.
2. Record the currently deployed image ID and RepoDigests:

   ```sh
   docker compose images overseer
   docker image inspect ghcr.io/pykhaled/overseer:3.0 --format '{{.Id}} {{json .RepoDigests}}'
   ```

3. Retain the previous exact digest/reference until the observation window
   closes. A floating `3.0` tag alone is not a rollback reference.
4. Validate the Compose model:

   ```sh
   docker compose -f compose.yml config --quiet
   ```

## Procedure

1. Pull the reviewed image and recreate only Overseer:

   ```sh
   docker compose pull overseer
   docker compose up -d overseer
   docker compose logs --tail 200 overseer
   ```

2. Verify health and discovery:

   ```sh
   curl --fail --show-error http://overseer.localhost/healthz
   curl --fail --show-error http://overseer.localhost/api/services
   curl --fail --show-error http://overseer.localhost/api/dashboard
   ```

3. Confirm Overseer excludes itself, includes only the intended Compose
   project, and shows declared dependencies/resources.
4. With explicit approval, test one restart against a non-critical service and
   include the CSRF header:

   ```sh
   curl --fail --show-error --header 'X-Overseer-CSRF: 1' --request POST http://overseer.localhost/api/service/APPROVED_CONTAINER_ID/restart
   ```

5. Confirm the same request without the CSRF header is rejected. Do not test
   stop/restart against the gateway, database, or active incident workload.

## Success criteria

- Overseer is healthy and scoped to the expected Compose project.
- Dashboard/service APIs show expected services and resource data.
- Approved lifecycle action succeeds only with CSRF protection.
- No new public host port or broader socket mount is introduced.
- Previous exact image digest remains available for rollback.

## Rollback or recovery

Restore the previous exact image digest in the reviewed Compose configuration,
then run `docker compose up -d overseer` and repeat health/discovery checks. If
the change indicates compromise or unsafe socket behavior, keep Overseer
stopped and use `overseer-socket-exposure-incident.md` instead of rolling back
into service.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| Project scoping or lifecycle authorization regresses | Overseer owner and security owner | Old/new digests, API evidence, affected services, rollback result |
| New image changes socket or privilege requirements | Security/change authority | Mounts, privileges, upstream rationale, threat-model impact |
| Rollback image unavailable | Platform operator | Recorded image ID/digests, local image state, registry result |

## Follow-up

- Record old/new digests, verifier, lifecycle test target, and observation.
- Remove superseded images only after rollback window closes.
- Update issue #26 when the security boundary changes.
