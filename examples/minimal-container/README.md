# Minimal-Container Configuration Example

This is an assembled pipeline configuration, not an application. Generated files mirror canonical sources; edit those sources and run the contributor sync utility to refresh them.

## Copy map

Copy the following files to the shown paths in your application repository. Preserve existing application files and merge configuration deliberately.

- [templates/configuration/dependabot/minimal-container.yml](../../templates/configuration/dependabot/minimal-container.yml) → `.github/dependabot.yml`
- [templates/configuration/pre-commit/.pre-commit-config.yaml](../../templates/configuration/pre-commit/.pre-commit-config.yaml) → `.pre-commit-config.yaml`
- [templates/workflows/containers/build-and-push.yml](../../templates/workflows/containers/build-and-push.yml) → `.github/workflows/publish.yml`

## Verify before adoption

Provide a Dockerfile and review GHCR permissions. This example has no application tests or security gate. Manually publish from `main` only after your own checks pass.

See [Getting Started](../../docs/pipeline/getting-started.md) for verification steps and [Secrets and Permissions](../../docs/pipeline/reference/secrets-and-permissions.md) for access requirements.
