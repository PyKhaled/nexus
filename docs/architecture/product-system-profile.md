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


The repository also contains a service scaffold, Compose examples, and component documentation. Those artifacts do not by themselves establish a complete product, production readiness, operational coverage, or an accountable product owner.

## Capability vocabulary

- **Capability:** a stable responsibility the product must provide.
- **Service:** one independently running application or process.
- **Stack:** a primary runtime and private dependencies operated together.
- **Adapter:** an implementation that translates between Nexus and another system.
- **Private dependency:** a data store or runtime owned by one component or stack.
- **Composition:** selected implementations and configuration assembled into a runnable environment.

Technology names do not replace capability definitions. For example, authentication is a capability; keycloak is Nexus's current development implementation.

## Ownership boundaries

- The gateway owns public HTTP entry and route policy.
- A stack owns its private databases, caches, configuration, migration, and recovery concerns.
- Product-specific business rules must remain outside generic foundation components.
- Provider-specific integration behavior belongs in adapters rather than product-domain rules.
- Operational runbooks remain beside the service or stack they operate.

See [Service and Stack Organization](service-and-stack-organization.md) for the accepted repository decision.

## Planned capabilities

Planned work is not current architecture. It is tracked in GitHub:

- [Overseer integration](https://github.com/PyKhaled/Nexus/issues/2)
- [Product composition system](https://github.com/PyKhaled/Nexus/issues/4)

Help center, notifications, client and administration experiences, business
domains, and integrations are not Nexus commitments until a concrete issue
defines users, scope, ownership, and acceptance criteria.

## Reusable guidance

The generic concept, reference architecture, proposed standard, policies, and
review checklist were migrated to Engineering OS as proposed material. They do
not make Nexus conformant or create organization-level policy.
