# Composition Data

This directory is the data the `nexus-compose` compiler
([`tools/nexus_compose/compiler.rb`](../tools/nexus_compose/compiler.rb)) reads
to generate a Compose deployment package from a declarative selection. See
[issue #4](https://github.com/PyKhaled/Nexus/issues/4) for the feature
rationale and acceptance gate.

## Layout

| Path | Role |
| --- | --- |
| `base.compose.yml` | The empty Compose skeleton (name, `system` network, volumes) every selection starts from. |
| `editions/` | Named capability defaults, requirements, and allow-lists (`community`, `custom`). |
| `environments/` | Build and restart-policy behavior per environment (`development`, `production`). |
| `targets/` | Where the composition runs and what that implies for the registry (`local`, `self-hosted`). |
| `assurance/` | Supply-chain and runtime-security requirements (`standard`, `hardened`, `high-assurance`). |
| `catalog/` | One `ComponentImplementation` entry per selectable implementation, pointing at its Compose fragment. |
| `components/` | The Compose fragment each catalog entry merges into the base. |
| `examples/` | Selections the test suite compiles: `nexus-development`, `nexus-self-hosted-production`, `nexus-high-assurance`. |

## Current capabilities

| Capability | Implementation | Services |
| --- | --- | --- |
| `gateway` | `nginx` | `gateway` |
| `authentication` | `keycloak` | `keycloak`, `keycloak-db` |
| `website` | `wordpress` | `website`, `website-db` |
| `service-status` | `kener` | `status`, `status-redis` |

These match the services in the root [`compose.yml`](../compose.yml) exactly;
`nexus-development.yaml` is compiled and compared against it in
[`compiler_test.rb`](../tools/nexus_compose/test/compiler_test.rb).

## Running the tests

```sh
ruby tools/nexus_compose/test/compiler_test.rb
```
