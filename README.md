# System

A SaaS platform mono-repo composed of Docker services managed via a single `docker-compose.yml`. Each subdirectory is a git submodule with its own repository.

## Services

| Service | Image | Port |
|---|---|---|
| `loadbalancer` | nginx:1.29-alpine (custom build) | 80, 443 |
| `auth-server` | authentik/server:2026.5.3 | 9000, 9443 |
| `auth-worker` | authentik/server:2026.5.3 | — |
| `auth-db` | postgres:16-alpine | — |
| `website` | wordpress:latest | 8080 |
| `website-db` | mysql:8.0 | 3306 |

`system-service/` contains a reference Dockerfile showing how to extend a production image — it is not wired into the compose stack.

## Setup

### 1. Initialize submodules

```bash
git submodule update --init --recursive
git submodule foreach --recursive 'git fetch origin main || true; git checkout main 2>/dev/null || git checkout -b main; git pull origin main'
```

### 2. Create environment files

**`.env`** (root — used by auth-server, auth-worker):
```
PG_DB=authentik
PG_USER=authentik
PG_PASS=<required>
AUTHENTIK_SECRET_KEY=<required>
COMPOSE_PORT_HTTP=9000
COMPOSE_PORT_HTTPS=9443
MYSQL_ROOT_PASSWORD=<required>
MYSQL_PASSWORD=<required>
```

**`system-auth-db/.env`** (used by auth-db):
```
PG_DB=authentik
PG_USER=authentik
PG_PASS=<required>
```

### 3. Start the stack

```bash
make up
```

## URLs (after `make up`)

| Service | URL |
|---|---|
| WordPress | http://localhost:8080 |
| Authentik | http://localhost:9000 |
| Authentik (HTTPS) | https://localhost:9443 |

## Common Commands

```bash
make up / down / restart   # stack lifecycle
make ps                    # running containers
make logs                  # tail all logs
make build                 # build images
make rebuild               # build without cache
make clean                 # down --remove-orphans
make prune                 # remove all containers, images, volumes (destructive)
```

## Nginx Routing

Virtual host configs live in `system-loadbalancer/conf.d/`. SSL certificates go in `system-loadbalancer/ssl/` and are mounted read-only into the container.