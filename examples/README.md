# Worked Pipeline Configurations

- [Node](node/README.md): npm CI, filesystem security, and manual scan-gated publishing.
- [Laravel](laravel/README.md): Composer/Laravel tests, filesystem security, and manual scan-gated publishing.
- [Django](django/README.md): Django checks/tests, filesystem security, and manual scan-gated publishing.
- [Minimal container](minimal-container/README.md): manual basic publishing without application tests or a security gate.

Each example is a set of configuration files for an existing application. It does not include a demo app or promise that arbitrary applications will run unchanged. The README provides exact source-to-destination mappings.

`manifest.json` defines canonical sources. Maintainers run `bash scripts/sync_examples.sh` to refresh copies and add `--check` to detect drift. Consumers follow the guides and copy deliberately; there is no installer for application repositories.
