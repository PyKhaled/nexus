# Secrets and Permissions

Application CI and security checks use job-level `contents: read`; top-level permissions are empty. Checkout has `persist-credentials: false`. Do not add deployment or registry credentials to PR jobs.

GHCR publishing uses the built-in `GITHUB_TOKEN` with `packages: write` and `contents: read`. Set repository/package access in GitHub as needed. No custom registry password is required by these starters. Adapt registry authentication explicitly if moving away from GHCR.

The optional Devtron workflow needs `DEVTRON_WEBHOOK_URL_DEV` and `DEVTRON_API_TOKEN` as secrets on a `development` environment. Configure any desired environment approvals and branch restrictions. The workflow does not create those controls. Never supply a production endpoint to this development recipe.

GitHub artifact storage receives scanner evidence and generated reports. Limit repository/artifact access and review retention. Do not place secrets in build arguments, examples, policy exceptions, or screenshots.

Actions use commit pins inherited from the source kit. Dependabot handles Actions updates after copying to a real `.github/workflows/` directory; it does not discover these canonical files under `templates/` as active workflows. Maintainers must review pins when updating canonical templates.
