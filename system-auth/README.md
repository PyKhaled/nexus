# authentik-service

A minimal Docker Compose setup for running Authentik (server, worker, and Postgres) with local volumes for data, certs, and custom templates.

## Repository structure

- `docker-compose.yml` - Compose file defining `postgresql`, `server`, and `worker` services.
- `certs/` - Place TLS certificates here if you want the worker to access them.
- `custom-templates/` - Override or add Authentik templates here; mounted into the server and worker.
- `data/` - Persistent runtime data and uploads.
- `.env` - Environment file (not committed) used by `docker-compose.yml`.

## Prerequisites

- Docker
- Docker Compose (or `docker compose` plugin)

## Environment variables

Create a `.env` file in the repo root with values for at least the required variables. Example:

```
# Postgres
PG_DB=authentik
PG_USER=authentik
PG_PASS=supersecretpostgrespw

# Authentik
AUTHENTIK_SECRET_KEY=supersecretkey

# Compose ports (optional)
COMPOSE_PORT_HTTP=9000
COMPOSE_PORT_HTTPS=9443

# Optional image override
# AUTHENTIK_IMAGE=ghcr.io/goauthentik/server
# AUTHENTIK_TAG=2026.5.3
```

Note: `PG_PASS` and `AUTHENTIK_SECRET_KEY` are required by the Compose file and will fail if omitted.

## Quickstart

Start the stack:

```bash
docker compose up -d
```

View logs:

```bash
docker compose logs -f server
```

Stop and remove containers (preserve volumes):

```bash
docker compose down
```

To remove volumes as well (destructive):

```bash
docker compose down -v
```

## Volumes and data

- The Postgres data is stored in a named Docker volume `database`.
- The `./data` directory is bind-mounted into the server and worker for uploaded files and runtime state.
- Back up `./data` and the Docker volume if you need persistence across hosts.

## Custom templates

Place template overrides in `custom-templates/`. Those files are mounted into the container at `/templates` and will be picked up by Authentik where applicable.

## Certificates

If you need to expose TLS or have worker tasks that require cert files, place them in `certs/` (the worker mounts `./certs:/certs`). Ensure file permissions are appropriate for container access.

## Updating the Authentik image

By default the Compose file uses `authentik/server:2026.5.3`. To change this, either edit the image tags in `docker-compose.yml` or set `AUTHENTIK_IMAGE` and `AUTHENTIK_TAG` in `.env` and uncomment the `image:` override lines.

## Troubleshooting

- If Postgres fails to become healthy, check `docker compose logs postgresql` and ensure `PG_PASS` is correct.
- If the server won't start due to secrets, verify `AUTHENTIK_SECRET_KEY` is set.

## Contributing

Feel free to open issues or submit PRs to improve the compose setup, add healthchecks, or provide example templates.

## License

No license specified. Add a `LICENSE` if you intend to open-source the repo.
