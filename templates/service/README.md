# SaaS Service Template

This directory is a runnable starting structure for a future owned service
repository. It is not a Nexus product capability and is not loaded by the root
Compose environment.

Copy the template into a new repository, then replace its identity, ownership,
capability contract, interfaces, and placeholder implementation before adding
the released service to a product composition.

## Included baseline

- dependency-free Python HTTP service;
- `/healthz` and `/readyz` operational endpoints;
- unit tests and a local validation command;
- non-root container image with a health check;
- image smoke test;
- development configuration example;
- documentation, contribution, governance, and runbook starting material; and
- repository workflow and issue templates.

## Quick start

```sh
make check
make run
```

Open `http://127.0.0.1:8000/healthz`.

Build and verify the container:

```sh
make build
make smoke
```

## Required adoption work

Before treating a derived repository as an implemented product capability:

1. Name the capability, service, owner, consumers, and lifecycle.
2. Replace the placeholder response with real domain or application behavior.
3. Define interfaces, compatibility, authorization, and data ownership.
4. Add required dependencies and lock their versions.
5. Expand tests according to product and operational risk.
6. Replace example contacts, maintainers, governance, and support information.
7. Define configuration, secrets, migrations, observability, backup, recovery,
   release, and deployment.
8. Publish an immutable artifact and add that artifact to the consuming product
   system's composition and capability manifest.

The template is evidence of structure only. A copied directory is not evidence
that the resulting service is implemented, secure, release-ready, or
operational.
