# Contributing Guide

Thank you for your interest in contributing.
This guide explains how to get started, how to propose changes, and how to submit pull requests.

## Ground Rules

- Keep changes focused and small where possible.
- Prefer clear, maintainable code over clever code.
- Write or update tests when behavior changes.
- Update docs for user-facing or developer-facing changes.

## Getting Started

1. Fork the repository and clone your fork.
2. Create a feature branch from `main`.
3. Install dependencies for this project.
4. Run the project locally and confirm it works before making changes.

Example workflow:

```bash
git clone <your-fork-url>
cd repository-template
git checkout -b feat/short-description
```

## Development Workflow

1. Make your changes in small, reviewable commits.
2. Run tests and linters locally.
3. Ensure formatting is consistent with the project.
4. Verify documentation stays accurate.

Before opening a pull request, confirm:

- The code builds successfully.
- Tests pass locally.
- No obvious lint or type errors remain.
- New behavior is covered by tests (when applicable).

## Commit Message Guidelines

Use clear commit messages that explain intent.
Recommended style:

`<type>: <short summary>`

Common types:

- `feat`: a new feature
- `fix`: a bug fix
- `docs`: documentation-only changes
- `refactor`: internal code improvements without behavior changes
- `test`: tests added or updated
- `chore`: maintenance tasks

Examples:

- `feat: add retry logic for API client`
- `fix: handle empty response in parser`
- `docs: clarify local setup steps`

## Pull Request Guidelines

When opening a pull request:

- Use a clear title that describes the change.
- Include a short summary of what changed and why.
- Link related issues (for example, `Closes #123`) when relevant.
- Add a test plan describing what you verified.
- Include screenshots or recordings for UI changes.

### Suggested PR Template

```md
## Summary
- What changed
- Why it changed

## Test Plan
- [ ] Unit tests pass
- [ ] Manual verification completed

## Related
- Closes #<issue-number>
```

## Reporting Bugs

Please include:

- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, runtime, versions)
- Logs, stack traces, or screenshots if available

## Requesting Features

Feature requests are welcome.
Please describe:

- The problem you are trying to solve
- The proposed solution
- Possible alternatives considered

## Code Review Expectations

- Reviews focus on correctness, readability, and maintainability.
- Be open to feedback and keep discussion constructive.
- If feedback is unclear, ask follow-up questions.
- Reviewers should provide actionable, respectful comments.

## License

By contributing, you agree that your contributions are licensed under the repository license.
