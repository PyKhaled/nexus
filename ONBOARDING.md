# Onboarding: Nexus

Welcome. This is a practical entry point — how to get the stack running, how
the repository is organized, and how work actually gets done here. For deep
detail, follow the links out to `docs/`; this file stays a map, not the
territory.

## What Nexus is

Nexus is a self-hosted application stack fronted by a reusable NGINX edge
gateway. The gateway is the only component that publishes a host port;
every backend service talks over the shared `nexus-system` Docker network
and is reached through a `*.localhost` route.

The repository is also used to explore a broader, technology-neutral model
for structuring, developing, and operating composable software products
(`product-system.yaml`, `docs/architecture/product-system-profile.md`).
That model is a deliberate, separate draft — don't treat it as describing
current runtime behavior. When in doubt, `compose.yml` and `docs/` describe
what actually runs; `product-system.yaml` describes what the product is
trying to become.

## Prerequisites

- Docker and Docker Compose v2 (`docker compose version`)
- Ruby (any recent 3.x) — only needed for the `nexus-compose` tooling under
  `tools/nexus_compose/` and its tests, not for running the stack itself

## Quick start

```sh
git clone git@github.com:PyKhaled/Nexus.git
cd Nexus
make up
curl http://localhost/healthz   # -> ok
```

`make up` builds and starts everything `compose.yml` declares. No `.env`
file is required — every service has a working development default.

| Route | Backs onto |
| --- | --- |
| `http://localhost/` | WordPress |
| `http://auth.localhost` | Keycloak |
| `http://status.localhost` | Kener (service status page) |
| `http://overseer.localhost` | Overseer (Compose observability/control — **unauthenticated by design**, trusted-network only) |
| `http://api.localhost` | Reserved; no runnable API service exists yet |

Start one part of the stack instead of everything with `make website`,
`make auth`, `make status`, `make overseer`, or `make gateway` — each starts
the gateway first, then attaches its own service(s) to `nexus-system`. Run
`make help` for the full command list, including database shells and the
`nexus-compose` targets described below.

## Repository map

| Path | What it is |
| --- | --- |
| `compose.yml` | The one active Compose definition. Source of truth for local development; every `make` target reads it. |
| `makefile` | Every supported operation — stack lifecycle, gateway operations, database shells, composition tooling. Start here before running a raw `docker compose` command by hand. |
| `system/` | One directory per deployable service or stack (`system-gateway`, `system-auth` + `system-auth-db`, `system-website` + `system-website-db`, `system-status`, `system-overseer`, and the non-runnable `system-service` scaffold). Each owns its own README, config, and `docs/runbooks/`. |
| `composition/` + `tools/nexus_compose/` + `bin/nexus-compose` | A separate generator that can compile a declarative selection (edition/environment/target/assurance/capabilities) into a Compose deployment package. Not wired into the default workflow — `compose.yml` stays hand-maintained and the generator is kept in sync with it by tests. See `composition/README.md`. |
| `docs/` | Canonical documentation index (`docs/README.md`), architecture decisions, Compose mode reference, runbook index, and reusable templates (component README, runbook, ADR). |
| `product-system.yaml` | The declarative product-capability model referenced above. |
| `bin/nexus-compose secrets` | Merges the selected components' `.env` files into root `secrets.env`; `make collect-secrets` runs it, and other root Make targets load the result automatically when present. |

## The mental model

- **Service**: one independently deployable runtime (`system-gateway`,
  `system-overseer`).
- **Stack**: a primary service plus private dependencies operated together
  (`system-auth` + its Postgres, `system-status` + its Redis).
- A private dependency (a database, Redis, etc.) never gets a host port and
  never gets its own gateway route — only the stack's primary service does.
- The gateway is the *only* thing bound to a host port in normal operation.
  An unavailable upstream returns `502`; it never stops the gateway itself
  from starting.

Full decision record: `docs/architecture/service-and-stack-organization.md`.

### Adding a new routed service

1. Attach it to the external `nexus-system` Docker network.
2. Add its domain and upstream env vars to the gateway service in
   `compose.yml`, following the existing `*_DOMAIN`/`*_UPSTREAM` pattern.
3. Add a route template under `system/system-gateway/templates/` (and its
   `templates-tls/` counterpart if you're touching TLS).
4. Give it its own `system/system-<name>/` directory: README (using
   `docs/templates/component-readme.md`), and `docs/runbooks/` registered in
   `docs/runbooks/README.md`.
5. `make gateway-test` to confirm the rendered NGINX config is valid.
6. If you want `nexus-compose` to keep generating an equivalent package,
   mirror the change into a `composition/catalog/` entry and its component
   fragment — see `composition/README.md`.

## How work actually happens here

- **Issues are the source of truth for scope.** A feature's rationale,
  acceptance criteria, and security requirements live in its GitHub Issue,
  not in a design doc. Read the issue before touching the code it names.
- **Small, reviewable PRs — not big-bang rewrites.** This repo has direct,
  lived history of the alternative: an earlier all-at-once "composable SaaS
  composition system" commit (`76bf1c1`) was reverted the day after it
  landed, specifically because it bundled an unrelated rewrite with real
  features. The pieces worth keeping came back one deliberately scoped PR at
  a time. If a change is touching more than the issue in front of you, split
  it.
- **Every component owns its own docs.** Follow
  `docs/templates/component-readme.md`'s shape (capability, scope,
  interfaces, configuration, security, **known gaps**) and
  `docs/runbooks/Runbook-Template.md` for operational procedures. A gap you
  know about and haven't fixed belongs in the "Known gaps" table, not
  silently omitted.
- **Say what you deliberately left out, and why.** When a feature is scoped
  down from what a prior prototype or issue implied, write that down in the
  README/PR rather than let it read like an oversight — see how
  `composition/README.md` explains why `observability` (Overseer) is
  selected in the development example but deliberately absent from the
  production ones.
- **Docs must not describe unmerged work as current.** `docs/README.md`'s
  "Proposed work" list and each capability's state in `product-system.yaml`
  should match what's actually merged to `main`, not what's in flight.

## Before opening a PR

- [ ] `make gateway-test` if you touched anything under `system/system-gateway/`
- [ ] `docker compose -f compose.yml config --quiet` if you touched `compose.yml`
- [ ] `ruby tools/nexus_compose/test/compiler_test.rb` and
      `ruby tools/nexus_compose/test/cli_test.rb` (or `make composition-test`)
      if you touched `composition/` or `tools/nexus_compose/`
- [ ] New or changed service: does it have a README, a runbook index entry,
      and — if it's gateway-routed — a documented route?
- [ ] Does anything you removed or scoped down need a note explaining why,
      the way `composition/README.md` and component "Known gaps" tables do?

## Current state, honestly

- Capabilities actually running today: `gateway` (nginx), `website`
  (WordPress), `authentication` (Keycloak), `service-status` (Kener),
  `observability` (Overseer). See `composition/README.md`'s capability table
  for the authoritative, tested list.
- `system-service` is a scaffold, not a runnable service — the `api.localhost`
  route is reserved but has nothing behind it.
- Overseer has no built-in authentication and mounts the Docker socket; its
  default route is trusted-network-only by design, and a production
  authenticated overlay is drafted but not yet built (see
  `system/system-overseer/README.md`).
- `nexus-compose` (`bin/nexus-compose`) is a real, tested CLI, but it's a
  repo-local script — not a packaged or distributable artifact — and
  `validate` doesn't yet recompile and rerun policy checks against generated
  content. See `composition/README.md`'s "Known gaps."
- Open work is tracked in [GitHub Issues](https://github.com/PyKhaled/Nexus/issues).
  As of this writing the only open one is #6, a from-scratch evidence audit
  of current `main` — a good first read if you want to see exactly what has
  and hasn't been independently re-verified.

## Where to go next

Start with [`docs/README.md`](docs/README.md) — it's the canonical index for
architecture, operations, and decisions, and it links out to everything else
mentioned here.
