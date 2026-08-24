# Runtime Usage

The starter implementation exposes a small JSON HTTP interface:

| Path | Purpose |
| --- | --- |
| `/` | Placeholder service identity and runtime state |
| `/healthz` | Process liveness |
| `/readyz` | Dependency-free starter readiness |

Supported starter configuration:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SERVICE_NAME` | `replace-me` | Logical service identity |
| `ENVIRONMENT` | `development` | Runtime environment label |
| `SERVICE_HOST` | `127.0.0.1` locally | Bind address |
| `SERVICE_PORT` | `8000` | HTTP port |

These are template contracts, not permanent product interfaces. A derived
service must document its real API, authentication, authorization, errors,
compatibility policy, and operational endpoints.
