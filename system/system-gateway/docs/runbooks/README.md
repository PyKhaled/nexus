# System Gateway Runbooks

Operational runbooks for the Nexus NGINX gateway belong in this directory.

## Runbooks

| Priority | Runbook | Scope | Exercise state |
| --- | --- | --- | --- |
| P0 | [Gateway upstream failure](gateway-upstream-failure.md) | Distinguish gateway health from an unavailable routed service and recover only the owning boundary | Desk-reviewed; not exercised |
| P1 | [Gateway deploy and reload](gateway-deploy-and-reload.md) | Validate, deploy baked configuration, reload mounted configuration, and roll back | Desk-reviewed; not exercised |
| P1 / P0 | [Gateway certificate rotation](gateway-certificate-rotation.md) | Validate and replace a TLS key pair; emergency compromise boundary | Desk-reviewed; not exercised |

Review evidence: [2026-08-30 minimum-runbook review](../../../../docs/runbooks/review-evidence-2026-08-30.md).
