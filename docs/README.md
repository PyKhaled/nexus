# Nexus Documentation

This directory is the canonical entry point for documentation that must remain
versioned with Nexus code and configuration. Unmerged work stays in
[GitHub Issues](https://github.com/PyKhaled/Nexus/issues) and pull requests
until it merges.

## Current architecture

- [Nexus product-system profile](architecture/product-system-profile.md) — current scope, boundaries, and evidence state.
- [Service and stack organization](architecture/service-and-stack-organization.md) — accepted repository layout and ownership decision.
- [Docker Compose modes](compose/README.md) — active local composition and intentionally selected examples.

## Operations and decisions

- [Runbook index](runbooks/README.md) — runbook ownership and discovery.
- [Runbook template](runbooks/Runbook-Template.md) — repository-local procedure scaffold.
- [ADR template](decisions/ADR-Template.md) — architecture decision scaffold.

## Project evidence

- [Project Takeover](project/takeover/README.md) — point-in-time evidence
  package captured on 2026-08-27; it does not represent current validation.
- [GitHub work index](project/github-work-index.md) — publication-time index
  for issues #16–#30; GitHub remains authoritative for current issue state.
- [Documentation reconciliation evidence](project/documentation-reconciliation-2026-08-30.md)
  — source-bound issue #30 review, capability comparison, and static validation
  results.

## Component documentation

- [Component README template](templates/component-readme.md) — capability, ownership, interfaces, data, configuration, lifecycle, and operations.

## Documentation boundary

Nexus owns its product-specific architecture, decisions, implementation
documentation, operational procedures, and evidence. Organization-level
engineering standards and reusable, technology-neutral guidance belong in
Engineering OS and are not duplicated here.
