# Continuous Integration

Application CI installs dependencies and runs the checks that demonstrate your application's correctness. It runs on pull requests and pushes to `main` in these templates.

Use lockfiles for reproducibility and install development dependencies when tests require them. Run tests against disposable services with test-only settings. A passing lint command is not a passing test suite.

The starter CI jobs intentionally fail when commands fail; there are no advisory test steps. Add database services, coverage reporting, or a build matrix when the application needs them. Avoid secrets for untrusted pull request code.

Publishing is a separate manual workflow here. Make CI and security checks required on `main`, and publish only a reviewed revision with completed checks. See the [CI template contract](../../../templates/workflows/ci/README.md).
