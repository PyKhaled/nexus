# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

This is a mono-repo orchestrating a SaaS platform as Docker Compose services. Each subdirectory is a **git submodule** with its own repo:

| Submodule | Purpose |
|---|---|
| `system-auth/` | Authentik identity provider (server + worker containers) |
| `system-auth-db/` | PostgreSQL database for Authentik |
| `system-loadbalancer/` | Nginx reverse proxy (nginx:1.29-alpine) |
| `system-service/` | Keycloak-based service (alternative auth, custom theme + DB federation plugin) |
| `system-website/` | WordPress site with custom `wp-content/` |
| `system-website-db/` | MySQL database for WordPress |

The root `docker-compose.yml` wires together: `loadbalancer`, `auth-db`, `auth-server`, `auth-worker`, `website-db`, `website`.

**Important**: The `makefile` targets reference `compose.yaml` and `compose.dev.yaml` (not `docker-compose.yml`). Those compose files are expected but not yet present — use `docker compose -f docker-compose.yml <command>` directly until they are added, or run `make` targets after creating them.

## Common Commands

```bash
# Stack lifecycle (once compose.yaml/compose.dev.yaml exist)
make up           # Start all services
make down         # Stop all services
make restart      # Bounce the stack
make ps           # Show running containers
make logs         # Tail all logs
make build        # Build images
make rebuild      # Build without cache

# Individual services
make backend / make auth / make help-center / make admin

# Django (runs inside the backend container)
make migrate
make makemigrations
make shell        # Django shell
make bash         # Bash shell in backend container
make test         # pytest
make lint         # ruff check
make format       # ruff format
make createsuperuser
make collectstatic

# Infrastructure
make dbshell      # psql into postgres
make redis        # redis-cli
make mail         # start mailpit

# Cleanup
make clean        # down --remove-orphans
make prune        # docker system prune -af --volumes (destructive)
```

## Environment Variables

Each service expects a `.env` file (not committed). Minimum required variables for the root compose:

```
# Auth DB
PG_DB=authentik
PG_USER=authentik
PG_PASS=<required>

# Authentik
AUTHENTIK_SECRET_KEY=<required>

# WordPress DB
MYSQL_ROOT_PASSWORD=<required>
MYSQL_PASSWORD=<required>
```

Copy `system-website/.env.example` for the WordPress service variables.

## Submodules

Initialize and update all submodules:

```bash
git submodule update --init --recursive
git submodule foreach --recursive 'git fetch origin main || true; git checkout main 2>/dev/null || git checkout -b main; git pull origin main'
```

## Nginx Routing

`system-loadbalancer/conf.d/` holds per-domain virtual host configs. The load balancer proxies:
- `localhost` → `app:8000` (backend)
- `help.localhost` → `helpcenter:3000`
- Auth routes are handled via `auth.conf`

SSL certs go in `system-loadbalancer/ssl/` and are mounted read-only into the container.

## Auth Stack Note

`system-service/dockerfile` builds Keycloak 24.0.1 (with a custom theme and DB federation plugin), while the root `docker-compose.yml` runs Authentik. These are two different identity providers — clarify which is active/intended before making auth changes.