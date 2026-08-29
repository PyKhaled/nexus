# Runbook: Respond to Overseer or Docker-socket exposure

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P0

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: local Overseer service with host mount `/var/run/docker.sock:/var/run/docker.sock`; any non-local exposure requires the additional controls tracked in issue #26

Severity: critical

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Contain suspected unauthorized access to Overseer or its Docker socket while
preserving evidence and treating the entire Docker host as potentially
compromised.

## Preconditions and safety

- Required access: Docker host/Compose operation, gateway/network controls,
  incident coordination, and secret owners.
- Required tools: Docker CLI and an approved evidence location outside Git.
- User or data impact: stopping Overseer removes lifecycle controls but should
  not stop other Nexus services. Host isolation may interrupt all workloads.
- Destructive or irreversible steps: none in initial containment. Do not prune,
  remove containers, rotate logs, or rebuild the host before evidence capture
  and incident direction.
- Escalate immediately. Docker-socket access is host-wide administrative
  access, not limited by Overseer's project display filter.

Replace example evidence paths and timestamps with approved values. Never save
container environment output or secrets in the repository.

## Detection

- Overseer route became reachable from an untrusted network.
- Unexpected lifecycle actions, containers, images, mounts, or Docker events.
- Security alert or vulnerability indicates possible code execution in
  Overseer.
- Gateway/access logs show unauthorized administrative requests.

## Immediate containment

1. Record incident time and affected host; notify the security incident lead.
2. Stop Overseer without removing it:

   ```sh
   docker compose stop overseer
   docker compose ps overseer
   ```

3. Restrict the affected gateway/network path using the environment's approved
   control. Do not rely on a `502` route as the only containment boundary.
4. If active host compromise is suspected, isolate the Docker host at the
   network/platform layer under incident-lead direction.

## Evidence preservation and diagnosis

1. Save bounded logs outside Git:

   ```sh
   docker compose logs --no-color --timestamps overseer > /absolute/approved/evidence/overseer.log
   docker compose logs --no-color --timestamps gateway > /absolute/approved/evidence/gateway.log
   ```

2. Record, without changing, the relevant container/image metadata and recent
   Docker events:

   ```sh
   docker inspect nexus-development-overseer-1 > /absolute/approved/evidence/overseer-inspect.json
   docker events --since '2026-08-30T00:00:00Z' --until '2026-08-30T01:00:00Z' > /absolute/approved/evidence/docker-events.log
   docker ps --no-trunc > /absolute/approved/evidence/docker-ps.txt
   ```

3. Do not publish raw inspection evidence; it can contain environment values,
   mounts, labels, and other sensitive metadata.
4. Determine exposure window, reachable route, executed lifecycle actions,
   unexpected containers/images, and whether arbitrary Docker API access was
   possible.

## Credential and host recovery

Treat every secret readable from any container, bind mount, volume, image, or
host file as exposed until the incident lead narrows the scope. Coordinate
rotation with each owning component. If host integrity cannot be established,
rebuild from a trusted image and restore only reviewed data/configuration; do
not restart Overseer on the suspect host.

## Success criteria

- Overseer and the untrusted access path are contained.
- Evidence is preserved in an approved restricted location.
- Host and credential impact are assessed by the responsible security role.
- Recovery uses a trusted host/image boundary when integrity is uncertain.
- Overseer is not re-enabled until issue #26 controls or an explicit local-only
  risk acceptance applies.

## Rollback or recovery

Containment is intentionally not rolled back during active investigation.
Re-enable Overseer only after the incident lead approves the host, route,
socket boundary, and credential state. Follow `overseer-upgrade-and-rollback.md`
for an approved image replacement; restoring the same suspect image is not
recovery.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| Any untrusted access or unexplained lifecycle action | Security incident lead | Host, route, exposure window, containment time, evidence locations |
| Host integrity cannot be established | Platform/host owner | Images/containers, socket exposure, indicators, required rebuild boundary |
| Secrets may be exposed | Each secret owner | Secret identifiers only, affected workloads/environments, exposure window |

## Follow-up

- Complete incident timeline, impact, credential rotation, and host disposition.
- Track access authentication and socket isolation in issue #26.
- Update this runbook from the exercised response without copying sensitive
  evidence into Git.
