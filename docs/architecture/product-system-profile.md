# Nexus Product-System Profile

Status: Draft product profile; current implementation requires fresh
verification

## Purpose

Describe how Nexus applies the composable product-system model without turning
proposed capabilities or historical audit results into current implementation
claims.

## Current repository baseline

The root `compose.yml` is the source of truth for local development. On current `main`, it assembles:

- NGINX
- keycloak
- wordpress
- kener and redis
- overseer


The repository also contains a service scaffold, Compose examples, and component documentation. Those artifacts do not by themselves establish a complete product, production readiness, operational coverage, or an accountable product owner.

## Capability vocabulary

- **Capability:** a stable responsibility the product must provide.
- **Service:** one independently running application or process.
- **Stack:** a primary runtime and private dependencies operated together.
- **Adapter:** an implementation that translates between Nexus and another system.
- **Private dependency:** a data store or runtime owned by one component or stack.
- **Composition:** selected implementations and configuration assembled into a runnable environment.

Technology names do not replace capability definitions. For example, authentication is a capability; keycloak is Nexus's current development implementation.

## Deployment composition vocabulary

Nexus applies the proposed Engineering OS composition model through a
declarative blueprint:

```text
Edition + Environment + Target + Assurance + Capabilities
                           │
                           ▼
                    Compose mode
                           │
                           ▼
                    Deployment package
```

- **Edition** defines product-capability defaults, requirements, and
  allow-lists. It answers what the product contains, not where it runs.
- **Environment** defines lifecycle behavior. Nexus currently implements
  `development` and `production`; test, preview, and staging are proposed.
- **Target** defines the execution boundary. Nexus currently implements
  `local` and `self-hosted`; CI and managed-container targets are proposed.
- **Assurance** independently tightens security and supply-chain controls
  through `standard`, `hardened`, or `high-assurance` profiles.
- **Capabilities** select catalog implementations and supporting operational
  layers.
- **Compose mode** is a descriptive name for the resolved combination, not an
  additional selector or independently maintained Compose file.

Nexus Assembler produces one deployment package containing the resolved
Compose model, normalized blueprint, lock data, build plan, secrets contract,
policy report, and operating summary.

Lightweight development and full integration development illustrate the
separation: both may use the same edition, development environment, local
target, and standard assurance. Full development adds database, cache, mail,
or engineering-tool capabilities explicitly.

## Current deployment constraints

- Production blueprints use prebuilt images and may not contain `build:`.
- Components declare private database and cache services; those services must
  not publish host ports.
- Hardened and high-assurance blueprints require immutable images resolved
  through the blueprint's private registry and apply the current runtime
  security checks.
- Overseer remains development-only because it lacks built-in authentication
  and mounts the Docker socket. Production observability requires a different
  implementation or completed authentication and socket-isolation controls.
- Test, CI, preview, managed production, full development, and staging are
  design targets until their schema, catalog metadata, policies, examples, and
  tests are implemented. Their active implementation issues are linked from
  the [composition guide](../../composition/README.md#deployment-catalog).

## Ownership boundaries

- The gateway owns public HTTP entry and route policy.
- A stack owns its private databases, caches, configuration, migration, and recovery concerns.
- Product-specific business rules must remain outside generic foundation components.
- Provider-specific integration behavior belongs in adapters rather than product-domain rules.
- Operational runbooks remain beside the service or stack they operate.

See [Service and Stack Organization](service-and-stack-organization.md) for the accepted repository decision.

Help center, notifications, client and administration experiences, business
domains, and integrations are not Nexus commitments. Their disposition is
tracked in [issue #29](https://github.com/PyKhaled/Nexus/issues/29), which must
define users, scope, ownership, and acceptance criteria before any
implementation issue is opened.

## Reusable guidance

The generic concept, reference architecture, proposed standard, policies, and
review checklist were migrated to Engineering OS as proposed material. They do
not make Nexus conformant or create organization-level policy. Nexus remains
the product-owned reference implementation and evidence source; Engineering OS
owns the reusable vocabulary and proposed requirements.
