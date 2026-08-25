# Composition Data

This directory is the data the `nexus-compose` compiler
([`tools/nexus_compose/compiler.rb`](../tools/nexus_compose/compiler.rb)) reads
to generate a Compose deployment package from a declarative selection, and
[`bin/nexus-compose`](../bin/nexus-compose) is the command line for it. See
[issue #4](https://github.com/PyKhaled/Nexus/issues/4) for the feature
rationale and acceptance gate.

## Layout

| Path | Role |
| --- | --- |
| `base.compose.yml` | The empty Compose skeleton (name, `system` network, volumes) every selection starts from. |
| `editions/` | Named capability defaults, requirements, and allow-lists (`community`, `custom`). |
| `environments/` | Build and restart-policy behavior per environment (`development`, `production`). |
| `targets/` | Where the composition runs and what that implies for the registry (`local`, `self-hosted`). |
| `assurance/` | Supply-chain and runtime-security requirements (`standard`, `hardened`, `high-assurance`). |
| `catalog/` | One `ComponentImplementation` entry per selectable implementation, pointing at its Compose fragment. |
| `components/` | The Compose fragment each catalog entry merges into the base. |
| `examples/` | Selections the test suite compiles: `nexus-development`, `nexus-self-hosted-production`, `nexus-high-assurance`. |

## Current capabilities

| Capability | Implementation | Services |
| --- | --- | --- |
| `gateway` | `nginx` | `gateway` |
| `authentication` | `keycloak` | `keycloak`, `keycloak-db` |
| `website` | `wordpress` | `website`, `website-db` |
| `service-status` | `kener` | `status`, `status-redis` |
| `observability` | `overseer` | `overseer` |

These match the services in the root [`compose.yml`](../compose.yml) exactly;
`nexus-development.yaml` is compiled and compared against it in
[`compiler_test.rb`](../tools/nexus_compose/test/compiler_test.rb).

`observability` is selected in `nexus-development.yaml` only. It is
deliberately **absent** from `nexus-self-hosted-production.yaml` and
`nexus-high-assurance.yaml`: Overseer has no built-in authentication and
mounts the Docker socket, so it must not appear in a composition whose policy
report can pass without an authenticating overlay in front of it. See
`system/system-overseer/README.md` for the drafted (not yet implemented)
production-auth approach.

## Commands

`bin/nexus-compose` wraps `NexusCompose::Compiler`'s three read/write
operations. Every command accepts a selection like
[`composition/examples/nexus-development.yaml`](examples/nexus-development.yaml)
— see that file for the selection shape (`product`, `deployment`,
`registry`, `capabilities`).

| Command | Purpose |
| --- | --- |
| `bin/nexus-compose plan --selection FILE` | Resolve a selection and print the components, artifacts, and policy status as JSON, without writing anything. |
| `bin/nexus-compose generate --selection FILE --output DIR [--force]` | Compile the selection and write a full deployment package to `DIR`. Refuses to replace a non-empty directory unless `--force` is given. |
| `bin/nexus-compose validate PATH` | Validate a generated `compose.yml` or package directory: structure, the selection-digest/locked-image match, and (when Docker is available) `docker compose config`. |

The equivalent Make targets default to `composition/examples/nexus-development.yaml`
and `generated/nexus-development` (override with `COMPOSITION_SELECTION` /
`COMPOSITION_OUTPUT`):

```sh
make composition-plan
make composition-generate
make composition-validate
make composition-test
```

`generated/` is gitignored beyond its own placeholder — a local
`composition-generate` run is scratch output, not something to commit.

## Generated package contents

`generate` writes:

| File | Contents |
| --- | --- |
| `compose.yml` | The resolved Compose file, equivalent to root `compose.yml` for the `nexus-development` selection. |
| `selection.yaml` | The normalized selection that produced this package. |
| `compose.lock.yaml` | Selection digest, resolved components, and artifact records — what `validate` checks the package against. |
| `build-plan.yaml` | Per-artifact build/mirror/sign actions and the assurance profile's SBOM/provenance/signature/reproducible-build requirements. |
| `.env.example` | Every capability's configuration variables, with development defaults or blanks for production. |
| `secrets.required` | Secret variable names and which capability needs them (names only, never values). |
| `policy-report.json` | The full policy check/warning output described below. |
| `README.md` | A generated summary of the selection and how to run it. |
| `runtime/auth.env.example` | Present only when `authentication` is selected — the Keycloak/Postgres runtime environment contract kept out of the main `.env.example`. |

A `production` environment selection additionally copies portable assets
(Keycloak realm config, Postgres config, TLS route templates) under
`assets/` inside the package.

## Policy checks

`evaluate_policies` runs on every `compile` and reports in
`policy-report.json` / the `generate` and `validate` output:

| Check | Applies when | What it enforces |
| --- | --- | --- |
| `unique-services` | Always | Two selected components cannot own the same Compose service name. |
| `runtime-builds-forbidden` | `environment: production` | No service declares `build:`; every image is pre-built. |
| `no-development-secret-defaults` | `environment: production` | No `change-me` placeholder survives into the output. |
| `production-tls` | `environment: production` | The gateway redirects to HTTPS and mounts certificate material. |
| `immutable-images` | `assurance: hardened` or `high-assurance` | Every artifact resolves through a required digest variable, not a mutable tag. |
| `private-registry-only` | `assurance: hardened` or `high-assurance` | Every image resolves through the selection's own registry host. |
| `privileged-forbidden` | `assurance: hardened` or `high-assurance` | No service runs `privileged: true`. |
| `no-new-privileges` | `assurance: hardened` or `high-assurance` | Every service sets `security_opt: [no-new-privileges:true]`. |
| `private-ports-forbidden` | Always | A component's declared `security.privateServices` (databases, Redis, etc.) publish no host port. |

A failed `required` check fails the whole report (`status: failed`); `plan`,
`generate`, and `validate` all surface this. Two warning classes never fail
the report but are worth reading: `dormant-gateway-route-<capability>` (the
gateway image still contains a route template for a capability you didn't
select — those requests will `502`) and `host-controls-outside-compose`
(`high-assurance` selections still need host hardening, admission control,
external secrets, backup, and audit handled outside Compose).

## Known gaps

| Gap | Risk | Owner | Target or review date |
| --- | --- | --- | --- |
| `validate` checks the selection digest and locked image references but does not recompile the selection and rerun policy checks against the generated content | A security-relevant Compose edit made after `generate` would not be caught by `validate` (tracked as the core unresolved item in issue #4) | Unassigned | None |
| No `configure`, `list`, `explain`, or `diff` commands | Selections must be hand-written; there's no interactive builder, catalog browser, or lock-comparison tool | Unassigned | None |
| `nexus-compose` is a repo-local script, not a packaged/distributable artifact | Can't be installed or version-pinned outside this repository | Unassigned | None |

## Running the tests

```sh
ruby tools/nexus_compose/test/compiler_test.rb
ruby tools/nexus_compose/test/cli_test.rb
```
