# Laravel Pipeline Guide

## Prerequisites

Provide `composer.json`, `composer.lock`, `.env.example`, `artisan`, and a test suite. PHP 8.3 is the starting runtime. The workflow runs tests with an in-memory SQLite database; adapt services and variables for MySQL/PostgreSQL-specific tests. Composer scripts run in CI, with no publishing credentials supplied. Copy .env only in a disposable checkout; preserve an existing local environment.

## Assemble

Follow the [Laravel example mapping](../../../examples/laravel/README.md). Start with `.github/workflows/ci.yml` and `.github/dependabot.yml`; add `devsecops.yml`, report tooling, and policies when ready. Add `publish.yml` only if you have a Dockerfile and intend to publish to GHCR.

## Validate application checks

In a disposable application checkout, use the same settings as CI:

```bash
composer install --prefer-dist --no-interaction --no-progress
cp .env.example .env
php artisan key:generate
php artisan test
```

Open a PR and verify real tests are discovered and a deliberately failing test fails the job. If dependencies or database setup fail, fix that prerequisite before evaluating the pipeline result. Check the [security template requirements](../../../templates/workflows/security/README.md) before enabling its job.

## Publish

After the selected `main` revision passes required checks, manually run Scan and publish. Verify the scan report and resulting commit tag. Image publication does not deploy the application. See [Container Publishing](../concepts/container-publishing.md).
