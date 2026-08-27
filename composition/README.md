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
| `editions/` | Named product-capability defaults, requirements, and allow-lists (`community`, `custom`). Editions do not encode deployment behavior. |
| `environments/` | Lifecycle behavior such as build, development-default, secret, and restart rules. The implemented environments are `development` and `production`. |
| `targets/` | The execution boundary and its registry implications (`local`, `self-hosted`). Environment and target together establish the deployment shape. |
| `assurance/` | Independent supply-chain and runtime-security requirements (`standard`, `hardened`, `high-assurance`). |
| `catalog/` | One `ComponentImplementation` entry per selectable implementation, pointing at its reusable Compose fragment. |
| `components/` | Compose fragments merged into the base. They represent capabilities and operational layers, not complete environment-specific stacks. |
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

## Selection and Compose-mode model

Every generated package is resolved from the same selection dimensions:

```text
Edition + Environment + Target + Assurance + Capabilities
                           │
                           ▼
                    Compose mode
                           │
                           ▼
               Generated deployment package
```

A **Compose mode** is a useful name for the outcome of a selection. It is not
another independent compiler dimension and does not require a separately
maintained, complete Compose file.

| Concept | Question it answers | Nexus representation |
| --- | --- | --- |
| Edition | What product capabilities are available, required, or selected by default? | `product.edition` resolved through `editions/` |
| Environment | How should the composition behave at this lifecycle stage? | `deployment.environment` resolved through `environments/` |
| Target | Where does the composition run? | `deployment.target` resolved through `targets/` |
| Assurance | Which security and supply-chain constraints apply? | `deployment.assurance` resolved through `assurance/` |
| Capabilities and layers | Which implementations and supporting services are included? | `capabilities` resolved through `catalog/` and `components/` |
| Compose mode | What recognizable deployment outcome did those choices produce? | A descriptive name reported for the resolved selection, not a separate source file |
| Generated package | What should an operator deploy and validate? | The resolved Compose file, selection, lock, build plan, secrets contract, policy report, and package README |

The division of responsibility is strict:

```text
Edition      = what the product contains
Environment  = how it behaves during this lifecycle stage
Target       = where it runs
Assurance    = what security constraints apply
Capabilities = which component implementations are present
Compose mode = convenient name for the resulting combination
```

For example, lightweight and full development may use the same edition,
development environment, local target, and standard assurance profile. Full
development differs because it explicitly selects additional database, cache,
mail-sandbox, or engineering-tool capabilities.

### Deployment catalog

The catalog below separates implemented selections from proposed extensions.
Adding a row to this document does not make that mode compiler-supported.

| Compose mode | Selection interpretation | Additional layers or behavior | Status |
| --- | --- | --- | --- |
| Lightweight development | Community edition + development + local + standard | Edition defaults and explicitly required services only; local builds and source mounts are allowed | Implemented by `nexus-development` |
| Full / integration development | Development + local + assurance choice | Explicit PostgreSQL, Redis, mail sandbox, observability, and engineering tools as needed | Proposed capability combination |
| Local test | Test + local | Disposable database/cache and a test-runner lifecycle | Proposed environment |
| CI | Test + CI target | The same disposable integration topology with CI exit and reporting behavior | Proposed target |
| Preview / PR | Preview + managed or self-hosted target | Prebuilt candidate image, isolated namespace, bounded secrets, disposable data, and expiry | Proposed environment |
| Managed production | Production + managed-container target | Prebuilt application image with external database, cache, storage, email, and ingress | Proposed target |
| Self-hosted staging | Staging + self-hosted target | Production-like image and real integrations without source mounts | Proposed environment |
| Self-hosted production | Community edition + production + self-hosted + hardened or high-assurance | Prebuilt images, gateway/TLS, durable private services, registry and security controls | Implemented by `nexus-self-hosted-production` and `nexus-high-assurance` |

Test, CI, preview, managed-container, and staging remain design targets. Add
their environment or target definitions only with compiler behavior, example
selections, policy checks, and tests.

### Optional operational layers

Observability and engineering tools are capabilities, not Compose modes. They
must be represented as catalog implementations and checked for compatibility
with the selected environment, target, and assurance profile.

| Layer | Eligibility | Constraints |
| --- | --- | --- |
| Database and cache | When an application capability declares a real dependency or an integration test exercises it | PostgreSQL, Redis, and other private services communicate on the Compose network and must not publish host ports, including loopback-only mappings. |
| Mail sandbox | Development, test, and optionally CI | Must not consume production credentials; UI exposure remains development-scoped. |
| Observability | Implementation-specific | Overseer is development-only because it lacks built-in authentication and mounts the Docker socket. A future production implementation requires its own catalog entry and security controls. |
| Engineering/admin tools | Explicit local-development selection by default | Disabled by default, attached to the private network, and never a reason to publish database or Redis ports. Production use would require authentication, authorization, audit, and an explicit exception. |
| Worker and scheduler | Only when a selected capability declares the dependency | Production roles reuse the same immutable application image and vary command/configuration rather than image lineage. |

Redis, storage emulators, or other supporting services must not be selected
merely to make a topology look production-like. They belong in a mode only
when a component declares a dependency or a test actually exercises the
integration.

### Compiler evolution

The compiler should keep the existing selection sections and resolve all
fragments before writing one self-contained package. Operators should not need
to remember an ordered list of post-generation override files.

Future catalog metadata should remain generic rather than branching on names
such as `overseer` or `wordpress` in `compiler.rb`. Candidate fields include
environment/target/assurance compatibility, component classification,
capability dependencies and conflicts, and ephemeral/persistent state
lifecycle. These names are proposals until the schema and tests implement
them.

Future required policies should:

- reject components incompatible with the resolved environment, target, or
  assurance profile;
- reject unsafe Docker-socket or equivalent host-control mounts outside their
  explicitly allowed scope;
- require disposable state for test, CI, and preview by default;
- require namespace, secret, and cleanup isolation for preview compositions;
- require authentication, authorization, and audit controls when engineering
  tools are allowed outside local development.

Existing controls remain authoritative: production forbids `build:` and uses
prebuilt images; private services publish no host ports; hardened and
high-assurance selections use immutable images from the selected private
registry and apply the existing runtime security controls.

## Commands

`bin/nexus-compose` wraps `NexusCompose::Compiler`'s read/write operations.
Every command accepts a selection like
[`composition/examples/nexus-development.yaml`](examples/nexus-development.yaml)
— see that file for the selection shape (`product`, `deployment`,
`registry`, `capabilities`).

| Command | Purpose |
| --- | --- |
| `bin/nexus-compose plan --selection FILE` | Resolve a selection and print the components, artifacts, and policy status as JSON, without writing anything. |
| `bin/nexus compose --selection FILE --output DIR [--force]` | Preferred spelling of `generate` through the new `nexus` entry point. Before writing, validates every required source repository declared by the selection. |
| `bin/nexus-compose generate --selection FILE --output DIR [--force]` | Compile the selection and write a full deployment package to `DIR`. Refuses to replace a non-empty directory unless `--force` is given. |
| `bin/nexus-compose validate PATH` | Validate a generated `compose.yml` or package directory: structure, the selection-digest/locked-image match, and (when Docker is available) `docker compose config`. |
| `bin/nexus-compose secrets --selection FILE --output FILE` | Merge the `.env` files of the selection's components into one secrets file. Refuses to write on a duplicate key across files, and warns (without failing) about any of the components' declared `secrets:` names that no `.env` file supplies. |

Both `bin/nexus` and the backward-compatible `bin/nexus-compose` entry point
use the same implementation. `compose` is an alias for `generate`.

### Source repositories

A selection may declare source repositories that must be checked out as Git
submodules below `system/`:

```yaml
repositories:
  - name: system-service
    url: git@github.com:example/system-service.git
    path: system/system-service
    branch: main
    required: true
```

Repository names and paths must be unique. Paths must be normalized relative
paths below `system/`; absolute paths and `..` traversal are rejected. `required`
defaults to `true`. `branch` controls `git submodule add`, while the parent
repository's Gitlink remains the reproducible record of the exact child commit.

| Command | Purpose |
| --- | --- |
| `bin/nexus repository add NAME URL --selection FILE [--path PATH] [--branch BRANCH] [--optional]` | Add the declaration, create/update `.gitmodules` through Git, and clone the submodule. The default path is `system/NAME`. |
| `bin/nexus repository list --selection FILE` | Print declarations together with their local state as JSON. |
| `bin/nexus repository status --selection FILE` | Return exit code `3` when a required repository is unavailable or inconsistent. Optional missing repositories are warnings. |
| `bin/nexus repository sync --selection FILE` | Add missing declared submodules, run recursive Git submodule sync, and initialize their recorded commits. This is the only repository command that may clone several repositories. |
| `bin/nexus repository validate --selection FILE` | Locally compare the selection, `.gitmodules`, parent Gitlinks, and checked-out commits without network access. |

`plan`, `validate`, and repository validation never clone or fetch. `compose`
also remains network-free: it fails when a required repository has not already
been initialized. A pipeline can therefore use an explicit checkout phase:

```sh
git clone --recurse-submodules "$NEXUS_REPOSITORY"
bin/nexus repository validate --selection nexus.yaml
bin/nexus compose --selection nexus.yaml --output dist/nexus
```

The repository currently contains only a commented `.gitmodules` example, and
`system/system-service` remains an ordinary tracked directory. With a matching
declaration the CLI reports the module as missing; if the template is merely
uncommented, it reports `not-a-submodule` because no Gitlink exists. Repository
commands never remove or convert existing content implicitly.

The equivalent Make targets default to `composition/examples/nexus-development.yaml`
and `generated/nexus-development` (override with `COMPOSITION_SELECTION` /
`COMPOSITION_OUTPUT`):

```sh
make composition-plan
make composition-generate
make composition-validate
make composition-test
make collect-secrets
```

`generated/` is gitignored beyond its own placeholder — a local
`composition-generate` run is scratch output, not something to commit.

## Catalog schema: `production` and `secretsEnvFiles`

Two catalog fields are read declaratively by the compiler rather than being
special-cased by capability name — this is what keeps `compiler.rb` from
needing to know that "website" or "keycloak" exist:

- `secretsEnvFiles: [path, ...]` — repo-relative paths to this component's own
  `.env` file(s) (the ones `secrets` merges). A path that doesn't exist is
  silently skipped, matching a fresh checkout before any `.env` has been
  created from its `.env.example`.
- `production:` — what this component needs when `deployment.environment` is
  `production`, applied generically by `prepare_production_mounts!` /
  `prepare_production_gateway!` / `copy_production_assets`:
  - `assetCopies: [{source, destination}]` — directories copied into the
    generated package's `assets/`.
  - `volumeRewrites: [{service, matchPrefix, replacement}]` or
    `[{service, matchPrefix, namedVolume}]` — rewrites a development
    bind-mount prefix into its production form, or into a named volume.
  - `gatewayVolumes: [mount, ...]` — volume mounts appended to the gateway
    service (a TLS route template, a certificate mount).
  - `environmentOverrides: [{service, key, value}]` / `portMappings:
    [{service, mapping}]` — environment or port entries applied to a named
    service.

See `composition/catalog/authentication-keycloak.yaml` and
`composition/catalog/gateway-nginx.yaml` for the fullest examples of each.

## Generated package contents

`generate` writes:

| File | Contents |
| --- | --- |
| `compose.yml` | The fully resolved Compose file, equivalent to root `compose.yml` for the `nexus-development` selection. Optional operational layers are merged here by the compiler rather than applied later by an operator. |
| `selection.yaml` | The normalized edition, environment, target, assurance, registry, and capability choices that produced this package. |
| `compose.lock.yaml` | Selection digest, resolved components, and artifact records — what `validate` checks the package against. |
| `build-plan.yaml` | Per-artifact build/mirror/sign actions and the assurance profile's SBOM/provenance/signature/reproducible-build requirements. |
| `.env.example` | Every capability's configuration variables, with development defaults or blanks for production. |
| `secrets.required` | Secret variable names and which capability needs them (names only, never values). |
| `policy-report.json` | The full policy check/warning output described below. |
| `README.md` | A generated summary of the resolved deployment shape, selected layers, policy status, and how to run it. |
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
| Only `development` and `production` environments and `local` and `self-hosted` targets are implemented | Test, CI, preview, managed-container, and staging are documented outcomes rather than supported selections | Unassigned | None |
| Catalog entries do not yet declare generic environment/target/assurance compatibility, dependencies, conflicts, or state lifecycle | Optional operational layers could otherwise require capability-name branches or be selected into unsafe deployment shapes | Unassigned | None |
| Overseer has no production-safe implementation | Enabling it outside development would expose an unauthenticated control surface with Docker socket access | Unassigned | Review only after authenticated access and socket isolation exist |

## Running the tests

```sh
ruby tools/nexus_compose/test/compiler_test.rb
ruby tools/nexus_compose/test/cli_test.rb
```
