# <Capability or Component Name>

> Copy this template beside the owning implementation and replace every
> placeholder.

Status: `<Planned | Partial | Implemented | Verified | Deprecated>`

Owner: `<team or person>`

Implementation type: `<service | stack | static | external | module>`

Technology: `<implementation or provider>`

## Capability

Describe the stable product responsibility, consumers, and expected outcome
independently of the current technology.

## Scope

Owns:

- `<responsibility>`

Does not own:

- `<explicit exclusion and owner>`

## Implementation

Describe the implementation and why it satisfies the capability.

## Interfaces

| Interface | Consumer | Contract | Compatibility |
| --- | --- | --- | --- |
| `<API, event, route, package, or configuration>` | `<consumer>` | `<link>` | `<policy>` |

## Data ownership

Document authoritative records, classification, migration, retention, backup,
recovery, and deletion responsibilities. State when the component is stateless.

## Configuration

| Setting | Purpose | Required | Secret | Owner | Safe development value |
| --- | --- | --- | --- | --- | --- |
| `<name>` | `<purpose>` | `<yes/no>` | `<yes/no>` | `<owner>` | `<value or none>` |

## Local composition

Identify Compose service names, build context or artifact, private dependencies,
networks, volumes, health checks, ports, and optional profiles.

## Development

```sh
<setup>
<test>
<check>
<build>
```

## Deployment and release

Document artifacts, versioning, compatibility, migrations, deployment,
rollback, and environment responsibilities.

## Security and operations

Document trust boundaries, privileged capabilities, health, logs, metrics,
alerts, objectives, common failures, runbooks, backup, recovery, and escalation.

## Replacement contract

For a replaceable capability, define what another implementation must preserve
and which migration concerns must be resolved.

## Known gaps

| Gap | Risk | Owner | Target or review date |
| --- | --- | --- | --- |
| `<gap>` | `<risk>` | `<owner>` | `<date>` |
