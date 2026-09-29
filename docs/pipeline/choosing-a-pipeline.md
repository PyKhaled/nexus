# Choosing a Pipeline

## Application checks only

Choose a [CI template](../../templates/workflows/ci/README.md) for fast feedback on tests and builds. Node assumes npm; Django assumes `manage.py` and `requirements.txt`; Laravel assumes Composer and SQLite-compatible tests.

## Application checks plus security

Add [DevSecOps](../../templates/workflows/security/README.md), the report engine, and security policies. The starter scans filesystem vulnerabilities and misconfigurations. Add other scanners only after defining evidence formats, configuration, and failure handling; the archived suites are historical references.

## Container publishing

Use [scan-and-push](../../templates/workflows/containers/README.md) when policy enforcement is required before publishing. Use basic build-and-push only when you deliberately want no vulnerability gate. Both require a Dockerfile and publish a commit tag to GHCR through manual dispatch on `main`.

## Deployment

The [Devtron example](../../templates/workflows/deployment/README.md) requests a development deployment of an existing image. Adapt its payload and environment controls to your installation. The [Kubernetes sample](../../templates/kubernetes/README.md) is an independent deployment specification, not an automated rollout.

## Worked configurations

The [examples](../../examples/README.md) combine application CI, security, and scan-gated publishing for Node, Laravel, and Django. The minimal example contains basic publishing only. These examples are configuration recipes, not demo applications.

## Repository profiles

Application repositories usually need quality, tests, dependency and
configuration evidence, with container and DAST coverage when those delivery
surfaces exist. Library repositories should emphasize package provenance and
consumer compatibility. Infrastructure repositories should emphasize policy,
secrets, configuration, and plan evidence.

Select applicable evidence explicitly. An omitted scanner is acceptable only
when the repository profile and reviewed policy mark that evidence class as
inapplicable. See [Delivery Architecture](concepts/delivery-architecture.md).
