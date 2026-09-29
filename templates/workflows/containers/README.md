# Container Publishing Templates

Choose one file and copy it to `.github/workflows/publish.yml`:

- `build-and-push.yml`: build and publish without a vulnerability gate.
- `scan-and-push.yml`: scan the locally built image, enforce release policy, then publish that same image.

## Requirements

Provide a root Dockerfile and correct build context. Scan-gated publishing additionally needs `tools/secreport/` and the three `security/` files, as described in the [security contract](../security/README.md). Both use GHCR, `GITHUB_TOKEN`, and job-level `contents: read` plus `packages: write`.

## Customize and verify

Review `main`, Docker paths, runtime requirements, registry access, retention, and the release policy. Dispatch manually on a revision whose CI has passed. Check the commit-tagged image in GHCR and, for scan-gated publishing, confirm policy failure skips login and push. Deploy by image digest when possible.

## Limits

Single-platform Docker builds only. Publishing does not wait for CI, deploy, sign images, or establish registry tag immutability. No production credentials are supplied to build steps, but job token permissions remain job-scoped. Basic publishing deliberately has no scan gate. See [Container Publishing](../../../docs/pipeline/concepts/container-publishing.md).
