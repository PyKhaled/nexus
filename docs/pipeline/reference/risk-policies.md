# Risk Policies

Copy all three files from `templates/configuration/security/` to `security/` in the application repository.

- `risk-policy.yaml` controls filesystem security checks.
- `release-policy.yaml` controls image publishing.
- `exceptions.yaml` starts empty and records reviewed acceptances.

The two starter policies intentionally block all unaccepted HIGH and CRITICAL findings, including baseline findings. `block_on_new_only: false` makes the historically named `max_new_high` and `max_new_critical` limits apply to all considered findings. The risk-score threshold is 101, above the engine's 100-point cap, so severity counts provide the ordinary blocking threshold.

Review internet exposure, data sensitivity, exception rules, and thresholds for your application. Do not imply that default context values describe your production system. Keep release decisions independent of a merge baseline.

An exception requires `id`, `reason`, `owner`, `approved_by`, and `expires`; use a concrete rule/CVE ID and an ISO date. Optional `scope` can constrain a path (`path:src/*`) or package (`package:example`). Missing or expired required fields block through the `expired_exception` rule. See the engine implementation when adding new policy fields; arbitrary YAML keys do not create enforcement.

After a policy change, rerun report generation before `gate`: gate consumes the stored report decision rather than reevaluating a supplied policy file.
