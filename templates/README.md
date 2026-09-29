# Template Catalog

Each family has a contract describing required files, destinations, customization, checks, and limitations:

- [Application CI](workflows/ci/README.md)
- [Security scanning](workflows/security/README.md)
- [Container publishing](workflows/containers/README.md)
- [Development deployment request](workflows/deployment/README.md)
- [Shared configuration](configuration/README.md)
- [Kubernetes deployment](kubernetes/README.md)

Templates are canonical. Files under `examples/` are maintained copies, checked against `examples/manifest.json`. Copy templates into the receiving repository's documented locations; they are not active Actions workflows in this repository.
