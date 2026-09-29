# Node Pipeline Guide

## Prerequisites

Provide `package.json`, `package-lock.json`, and `lint`, `test`, and `build` npm scripts. Node 24 is the starting runtime. Adapt the workflow and Dependabot together if using Yarn, pnpm, workspaces, or a monorepo. The test script must run once and return nonzero on failure; do not use watch mode.

## Assemble

Follow the [Node example mapping](../../../examples/node/README.md). Start with `.github/workflows/ci.yml` and `.github/dependabot.yml`; add `devsecops.yml`, report tooling, and policies when ready. Add `publish.yml` only if you have a Dockerfile and intend to publish to GHCR.

## Validate application checks

In a disposable application checkout, use the same settings as CI:

```bash
npm ci
npm run lint
npm test
npm run build
```

Open a PR and verify real tests are discovered and a deliberately failing test fails the job. If dependencies or database setup fail, fix that prerequisite before evaluating the pipeline result. Check the [security template requirements](../../../templates/workflows/security/README.md) before enabling its job.

## Publish

After the selected `main` revision passes required checks, manually run Scan and publish. Verify the scan report and resulting commit tag. Image publication does not deploy the application. See [Container Publishing](../concepts/container-publishing.md).
