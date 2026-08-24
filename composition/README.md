# Nexus Composition Generator

The composition generator compiles a product selection into one explicit
Docker Compose deployment package. It separates decisions that are often
incorrectly mixed together:

| Dimension | Responsibility |
| --- | --- |
| Edition | Default, required, allowed, and entitled product capabilities |
| Environment | Development or production lifecycle rules |
| Target | Local or self-hosted deployment assumptions |
| Assurance | Standard, hardened, or high-assurance security requirements |
| Capability | What the product needs |
| Implementation | Which replaceable component supplies that capability |

Docker Compose profiles may still be used inside a component for developer
convenience. They are not the product selection or security policy model.

## Quick start

Inspect the available dimensions and implementations:

```sh
bin/nexus-compose list dimensions
bin/nexus-compose list components
bin/nexus-compose explain website wordpress
```

Create a selection interactively:

```sh
bin/nexus-compose configure --output composition/selection.yaml
```

Or start with a checked-in example, inspect its resolution, and generate it:

```sh
bin/nexus-compose plan \
  --selection composition/examples/nexus-development.yaml

bin/nexus-compose generate \
  --selection composition/examples/nexus-development.yaml \
  --output generated/nexus-development

bin/nexus-compose validate generated/nexus-development
```

Generation refuses to replace a non-empty output directory unless `--force` is
explicitly provided.

## Inputs

A selection contains no secret values. It selects the product identity,
edition, deployment target, environment, assurance profile, registry policy,
and capability implementations. See `schemas/selection.schema.json` and the
files under `examples/`.

Catalog entries under `catalog/` describe one implementation of one capability.
They own:

- a Compose fragment;
- dependency and service boundaries;
- build, mirror, and digest information;
- configuration and secret contracts;
- public and private service classification; and
- declared runtime-security support.

An edition supplies defaults and constraints. It does not define where the
product runs or how secure the deployment claims to be.

## Outputs

Every generated directory contains:

| File | Contract |
| --- | --- |
| `compose.yml` | Resolved executable composition |
| `selection.yaml` | Exact normalized generation input |
| `compose.lock.yaml` | Selection digest, components, artifacts, and image decisions |
| `build-plan.yaml` | Build or mirror actions and required attestations |
| `.env.example` | Configuration names and intentionally empty secret/digest values |
| `runtime/auth.env.example` | Separate Keycloak and PostgreSQL runtime environment contract when authentication is selected |
| `secrets.required` | Secret names, owning capabilities, and descriptions |
| `policy-report.json` | Machine-readable checks, failures, and limitations |
| `README.md` | Generated deployment handoff |

Production authentication and PostgreSQL configuration assets are copied into
the generated package. Persistent PostgreSQL state becomes a named volume; it
is never copied from the development workstation.

## Production and high assurance

Production generation removes every Compose `build:` section and changes each
runtime artifact to a digest selected from the configured private registry.
It also enables HTTP-to-HTTPS redirect, publishes the HTTPS entry point,
requires externally supplied certificate material, and packages the selected
TLS route templates.
The separate build plan distinguishes:

- `internal-build`: source owned and built by the product organization; and
- `verified-mirror`: an approved upstream artifact resolved, verified, scanned,
  mirrored, attested, signed, and promoted internally.

`high-assurance` additionally requires `self-hosted` + `production`, a
`private-only` registry policy, immutable artifacts, no development secret
defaults, no privileged containers, no published private-dependency ports,
no-new-privileges, and a deny-by-default internal application network.

Compose cannot enforce registry admission, signature verification, host kernel
hardening, an external secret provider, encrypted backups, or external audit.
The policy report records this boundary. The deployment platform must enforce
those controls before the generated package can be called high assurance.

## Extension workflow

To add an implementation:

1. Add its owned fragment under `components/<capability>/`.
2. Add a catalog entry and artifact metadata under `catalog/`.
3. Add the capability to each edition that may select it.
4. Add secrets and configuration descriptions without values.
5. Add compiler tests for dependencies, policy behavior, and generated output.
6. Run `make composition-test` and generate all examples.

Generated output is ignored by Git. Commit the selection, catalog, fragments,
schemas, and policy definitions; publish generated deployment artifacts through
the release process that owns the target environment.
