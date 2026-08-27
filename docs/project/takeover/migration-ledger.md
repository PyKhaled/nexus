# Nexus Takeover Migration Ledger

## Purpose

Route validated takeover findings into existing Nexus authorities without
creating duplicate architecture pages, runbook registries, project backlogs, or
organization-level standards.

## Destination map

| Content | Canonical Nexus destination | Migration gate |
| --- | --- | --- |
| Current product scope and evidence state | [Product-system profile](../../architecture/product-system-profile.md) | Commit-bound evidence supports the wording |
| Service and stack boundaries | [Service and stack organization](../../architecture/service-and-stack-organization.md) | Architecture decision and implementation remain aligned |
| Composition behavior, selections, policies, and gaps | [Composition documentation](../../../composition/README.md), `composition/`, and `tools/nexus_compose/` | Code, tests, examples, and documentation change together |
| Material architecture choice | `docs/decisions/` | Decision authority and status are recorded |
| Proposed feature, defect, or validation work | [GitHub Issues](https://github.com/PyKhaled/Nexus/issues) | Scope and acceptance criteria are explicit |
| Service operating procedure | Owning service's `docs/runbooks/` directory | Procedure, environment, prerequisites, safety, verification, and review evidence exist |
| Runbook discovery | [Runbook index](../../runbooks/README.md) | Owning procedure link exists |
| Reusable, technology-neutral method or standard | Engineering OS | Project-specific facts and implementation claims are removed |
| Initiative status, milestones, risks, and delivery decisions | Explicitly created project record | The initiative exists and its authority is defined |

## Ledger

| Finding | Destination | Action | State | Required confirmation |
| --- | --- | --- | --- | --- |
| FND-001: inspected revision | [Engineering Baseline](engineering-baseline-2026-08-27.md) | Retain as dated evidence | Recorded | Full commit on next refresh |
| FND-002: root Compose role | [Root README](../../../README.md) and [product profile](../../architecture/product-system-profile.md) | Keep existing authority; do not duplicate | Linked | Runtime validation before stronger claims |
| FND-003 and FND-004: composition implementation | [Composition documentation](../../../composition/README.md) | Keep code and docs canonical; attach future test evidence to the relevant issue or review | Linked | Passing tests and validated packages |
| FND-005: runbook coverage gap | [Runbook index](../../runbooks/README.md) and service-local runbook directories | Keep indexes; add procedures only when written and validated | Deferred | Operator scope, procedure content, and review evidence |
| FND-006: fresh verification required | [GitHub issue #6](https://github.com/PyKhaled/Nexus/issues/6) | Use the issue for actionable audit work; update baseline from resulting evidence | Routed | Current issue state and completed acceptance evidence |
| FND-007: owner Unknown | Appropriate project or governance record | Do not infer from repository activity | Deferred | Explicit accountable-owner confirmation |
| FND-008: readiness Unknown | Existing architecture, issue, and runbook authorities | Do not create a blanket readiness statement | Deferred | Bounded test, security, deployment, and operational evidence |

## Migration rules

1. Search the current destination before adding a page.
2. Preserve observation dates and Git revisions.
3. Do not promote Inferred or Unknown claims as current state.
4. Keep recommendations in issues or an explicitly created project record.
5. Keep reusable Engineering OS guidance free of Nexus implementation facts.
6. Update [Nexus documentation](../../README.md), service runbook indexes, and
   related links in the same change as a migrated claim.
7. Do not add Nexus to an organization-level production inventory until the
   required owner, lifecycle, environment, and operational evidence are
   confirmed.

## Related

- [Takeover index](README.md)
- [Evidence register](evidence-register.md)
- [Engineering Baseline](engineering-baseline-2026-08-27.md)
