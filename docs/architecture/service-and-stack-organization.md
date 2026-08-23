# Service and Stack Organization

Status: Accepted

## Purpose

Nexus contains two kinds of deployable units:

- **Service**: one independently deployable application or runtime.
- **Stack**: a group containing a primary service and one or more private
  dependencies that are operated together.

This distinction describes deployment topology and ownership. It should not be
replaced with terms such as "application" and "infrastructure," because both
categories can contain application and infrastructure concerns.

## Classification

| Type | Definition | Current examples |
| --- | --- | --- |
| Service | A single independently built and deployed runtime | `system-gateway`, `system-service` |
| Stack | Multiple tightly related services with a shared lifecycle | `system-auth`, `system-website` |
| Dependency | A supporting runtime owned by one stack | PostgreSQL for Keycloak, MySQL for WordPress |

## Repository structure

```text
nexus/
├── compose.yml
├── system/
│   ├── system-gateway/
│   ├── system-service/
│   ├── system-auth/
│   │   ├── system-auth/
│   │   └── system-auth-db/
│   └── system-website/
│       ├── system-website/
│       └── system-website-db/
└── docs/
    └── compose/
        └── templates/
```

The root `compose.yml` is the only active Compose definition and the integration
entry point for the complete development environment. All deployable units live
under `system/`. Alternative and standalone Compose definitions are retained
only as documented examples under `docs/compose/templates/`.

## Location mapping

| Previous location | Current location |
| --- | --- |
| `system-gateway/` | `system/system-gateway/` |
| `system-service/` | `system/system-service/` |
| `system-auth/` | `system/system-auth/` |
| `system-website/` | `system/system-website/` |

## Ownership rules

Place every deployable unit under `system/`. Treat it as a standalone service
when it:

- can be built and deployed independently;
- has its own release lifecycle; and
- is not an implementation detail of one stack.

Treat a directory under `system/` as a stack and nest its components when a
component:

- exists exclusively to support that stack;
- is normally started and stopped with the stack; and
- is configured and operated by the same owning boundary.

Promote a dependency from its owning stack to its own top-level directory under
`system/` only when it becomes shared by multiple stacks or gains a genuinely
independent lifecycle. A runtime declared from an unmodified upstream image
does not require its own directory unless the repository stores configuration,
migrations, initialization files, or other owned artifacts for it.

## Naming rules

- Keep the existing `system-` prefix for the current service directories.
- Prefer responsibility names for future first-party services.
- Prefer explicit technology names for packaged third-party runtimes, such as
  `keycloak`, `postgres`, `wordpress`, and `mysql`.
- Keep nesting shallow: category, deployable boundary, then component.
- Keep the active development topology in the root `compose.yml`.
- Keep alternative Compose examples under `docs/compose/templates/`; do not
  load them implicitly from development commands.

## Runbook placement

Operational runbooks live with the deployable boundary that owns them:

```text
system/
├── system-gateway/docs/runbooks/README.md
├── system-service/docs/runbooks/README.md
├── system-auth/docs/runbooks/
│   └── README.md
└── system-website/docs/runbooks/
    └── README.md
```

A standalone service keeps all of its runbooks in its own `docs/runbooks/`
directory. A stack keeps runbooks for its primary service and private
dependencies together in the stack-level `docs/runbooks/` directory. This
matches the operational ownership boundary and keeps procedures versioned with
the configuration they describe.

The repository-level [`docs/runbooks/README.md`](../runbooks/README.md) is a
discovery index only. Do not place service-specific procedures there. When a
dependency becomes independently operated, move its runbooks with it to the
new top-level service directory.

## Decision summary

The repository groups all independently deployable services and multi-service
stacks under `system/`. Private databases and other dependencies remain
nested under their owning stack. This keeps the repository root small while
preserving ownership and lifecycle boundaries.
