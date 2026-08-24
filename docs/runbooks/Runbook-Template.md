# Runbook: <Event or operation>

> Copy this template into the owning service or stack's `docs/runbooks/`
> directory and replace every placeholder.

Owner: `<operational owner>`

Last verified: `YYYY-MM-DD`

Applies to: `<capability, versions, and environments>`

Severity: `<routine | degraded | incident | critical>`

## Purpose

Describe the condition this runbook handles and the intended safe outcome.

## Preconditions and safety

- Required access: `<access>`
- Required tools: `<tools>`
- User or data impact: `<impact>`
- Destructive or irreversible steps: `<none or explicit warning>`
- Escalate before proceeding when: `<conditions>`

## Detection

List the alert, symptom, query, or observation that identifies the condition.

## Diagnosis

1. `<safe diagnostic step>`
2. `<expected evidence and interpretation>`

## Procedure

1. `<action>`
2. `<verification immediately following the action>`

Commands must be safe to copy and identify every environment-specific value.

## Success criteria

- `<observable condition proving recovery or completion>`

## Rollback or recovery

Describe how to reverse the procedure or recover if it fails. State
irreversibility before any irreversible action.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| `<condition>` | `<role>` | `<logs, identifiers, timeline, impact>` |

## Follow-up

- Record the event and outcome.
- Create corrective work for discovered gaps.
- Update this runbook when actual behavior differs from the procedure.
