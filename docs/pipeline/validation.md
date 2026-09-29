# Source Migration Validation

The standalone Pipeline workspace recorded local verification on 2026-09-28:

- 44 active/example YAML files parsed successfully.
- All local Markdown links checked by the repository validator resolved.
- Seven canonical workflow templates passed actionlint 1.7.12; optional ShellCheck and Pyflakes integrations were disabled because those tools were not installed.
- Four unittest cases passed. The integration case covered clean and blocking SARIF under both risk and release policies, including CLI exit status.
- All generated example files matched their canonical sources.
- All 47 archive/protected-file SHA-256 entries matched, including the unchanged root AGENTS.md.
- The inherited report engine and its dependency file matched their archived originals byte-for-byte.

Validation used Python 3.12 and PyYAML 6.0.3. Full report-rendering dependencies, external enrichment, actual scanner execution, GitHub-hosted runs, container builds/pushes, and deployment were not exercised. No Git history was available in this checkout.

Those results describe the source workspace before import. For current repeatable checks, see [Contributing](contributing.md) and the [SecReport documentation](../../tools/secreport/README.md). Successful static checks and synthetic tests are not hosted runtime evidence.
