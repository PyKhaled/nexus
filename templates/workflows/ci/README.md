# Application CI Templates

Choose `node.yml`, `laravel.yml`, or `django.yml` and copy it as `.github/workflows/ci.yml`.

## Requirements and customization

Node needs a package-lock and npm lint/test/build scripts; Laravel needs Composer files, `.env.example`, and SQLite-compatible tests; Django needs `requirements.txt`, `manage.py`, and test settings. Runtime defaults are Node 24, PHP 8.3, and Python 3.12. Change commands and service setup to match the application.

Each job needs only repository read permission. No registry or deployment secrets are required. See the [stack guides](../../../docs/pipeline/choosing-a-pipeline.md) for local commands.

## Verification and limits

Run a passing PR and an intentional test failure. Confirm actual test discovery and configure required check names on the target branch. These templates do not set branch protection, publish images, or provide a coverage threshold.
