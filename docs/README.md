# Nexus Documentation

This directory is the canonical entry point for documentation that must remain
versioned with Nexus code and configuration. Proposed features stay in GitHub
Issues and pull requests until they merge.

## Current architecture

- [Nexus product-system profile](architecture/product-system-profile.md) — current scope, boundaries, and evidence state.
- [Service and stack organization](architecture/service-and-stack-organization.md) — accepted repository layout and ownership decision.
- [Docker Compose modes](compose/README.md) — active local composition and intentionally selected examples.

## Operations and decisions

- [Runbook index](runbooks/README.md) — runbook ownership and discovery.
- [Runbook template](runbooks/Runbook-Template.md) — repository-local procedure scaffold.
- [ADR template](decisions/ADR-Template.md) — architecture decision scaffold.

## Component documentation

- [Component README template](templates/component-readme.md) — capability, ownership, interfaces, data, configuration, lifecycle, and operations.

## Proposed work

- [Product composition system](https://github.com/PyKhaled/Nexus/issues/4)
- [Current-main evidence audit](https://github.com/PyKhaled/Nexus/issues/6)

The linked issues own feature rationale, scope, risks, and acceptance criteria.
Draft pull requests own implementation review and progress. Documentation must
not describe an unmerged feature as current behavior.

## Documentation boundary

Nexus owns its product-specific architecture, decisions, implementation
documentation, operational procedures, and evidence. Organization-level
engineering standards and reusable, technology-neutral guidance belong in
Engineering OS and are not duplicated here.
