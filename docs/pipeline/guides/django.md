# Django Pipeline Guide

## Prerequisites

Provide `manage.py`, `requirements.txt`, configured Django settings, and discoverable tests. Python 3.12 is the starting runtime. Add DJANGO_SETTINGS_MODULE, test-only environment values, and database services if your settings need them. Install development/test requirements if separate. This workflow contains no Node or Sanity steps.

## Assemble

Follow the [Django example mapping](../../../examples/django/README.md). Start with `.github/workflows/ci.yml` and `.github/dependabot.yml`; add `devsecops.yml`, report tooling, and policies when ready. Add `publish.yml` only if you have a Dockerfile and intend to publish to GHCR.

## Validate application checks

In a disposable application checkout, use the same settings as CI:

```bash
python -m pip install -r requirements.txt
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Open a PR and verify real tests are discovered and a deliberately failing test fails the job. If dependencies or database setup fail, fix that prerequisite before evaluating the pipeline result. Check the [security template requirements](../../../templates/workflows/security/README.md) before enabling its job.

## Publish

After the selected `main` revision passes required checks, manually run Scan and publish. Verify the scan report and resulting commit tag. Image publication does not deploy the application. See [Container Publishing](../concepts/container-publishing.md).
