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

- [Project Takeover](project/takeover/README.md) — evidence register, dated
  Engineering Baseline, migration ledger, and assurance plan for the current
  Nexus takeover review.
- [GitHub work index](project/github-work-index.md) — published issues #16–#30,
  priorities, dependencies, acceptance criteria, and source traceability.

## Component documentation

- [Component README template](templates/component-readme.md) — capability, ownership, interfaces, data, configuration, lifecycle, and operations.

## Documentation boundary

Nexus owns its product-specific architecture, decisions, implementation
documentation, operational procedures, and evidence. Organization-level
engineering standards and reusable, technology-neutral guidance belong in
Engineering OS and are not duplicated here.
