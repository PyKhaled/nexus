# Website Stack Runbooks

Operational runbooks for the website stack belong in this directory. Keep
WordPress and its private MySQL dependency together because they share an
operational lifecycle and owner.

## Runbooks

| Priority | Runbook | Scope | Exercise state |
| --- | --- | --- | --- |
| P0 / P1 | [WordPress database and content recovery](website-database-and-content-recovery.md) | Logical/content backup, trial verification, and explicitly destructive restore | Desk-reviewed; not exercised |
| P1 | [WordPress maintenance and upgrade](website-maintenance-and-upgrade.md) | Backed-up image/extension maintenance and rollback | Desk-reviewed; not exercised |
| P0 | [WordPress extension failure and outage](website-extension-failure-and-outage.md) | Diagnose outage and reversibly disable one plugin or theme | Desk-reviewed; not exercised |

Review evidence: [2026-08-30 minimum-runbook review](../../../../docs/runbooks/review-evidence-2026-08-30.md).
