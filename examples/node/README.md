# Node Configuration Example

This is an assembled pipeline configuration, not an application. Generated files mirror canonical sources; edit those sources and run the contributor sync utility to refresh them.

## Copy map

Copy the following files to the shown paths in your application repository. Preserve existing application files and merge configuration deliberately.

- [templates/configuration/dependabot/node.yml](../../templates/configuration/dependabot/node.yml) → `.github/dependabot.yml`
- [templates/configuration/pre-commit/.pre-commit-config.yaml](../../templates/configuration/pre-commit/.pre-commit-config.yaml) → `.pre-commit-config.yaml`
- [templates/workflows/ci/node.yml](../../templates/workflows/ci/node.yml) → `.github/workflows/ci.yml`
- [templates/workflows/security/devsecops.yml](../../templates/workflows/security/devsecops.yml) → `.github/workflows/devsecops.yml`
- [templates/workflows/containers/scan-and-push.yml](../../templates/workflows/containers/scan-and-push.yml) → `.github/workflows/publish.yml`
- [templates/configuration/security/risk-policy.yaml](../../templates/configuration/security/risk-policy.yaml) → `security/risk-policy.yaml`
- [templates/configuration/security/release-policy.yaml](../../templates/configuration/security/release-policy.yaml) → `security/release-policy.yaml`
- [templates/configuration/security/exceptions.yaml](../../templates/configuration/security/exceptions.yaml) → `security/exceptions.yaml`
- [tools/secreport/secreport.py](../../tools/secreport/secreport.py) → `tools/secreport/secreport.py`
- [tools/secreport/requirements.txt](../../tools/secreport/requirements.txt) → `tools/secreport/requirements.txt`
- [tools/secreport/validate_evidence.py](../../tools/secreport/validate_evidence.py) → `tools/secreport/validate_evidence.py`

## Verify before adoption

Follow the [node guide](../../docs/pipeline/guides/node.md) for application prerequisites and commands. Security needs the report tooling and policies above; publishing additionally needs a Dockerfile. Confirm actual test discovery and both clean and failing gate outcomes.

See [Getting Started](../../docs/pipeline/getting-started.md) for verification steps and [Secrets and Permissions](../../docs/pipeline/reference/secrets-and-permissions.md) for access requirements.
