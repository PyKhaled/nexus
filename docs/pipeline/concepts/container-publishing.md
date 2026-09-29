# Container Publishing

Both container templates build one local Docker image, give it a full commit-SHA tag, and push it to `ghcr.io/<owner>/<repository>:<sha>`. Repository names are lowercased for registry compatibility. A SHA-shaped tag identifies a revision but is not registry-enforced immutability; use the published digest for deployment identity.

Basic publishing has no security gate. Scan-gated publishing scans the local image, validates the report input, and enforces `security/release-policy.yaml` before login and push. It uses `docker push` on the scanned local image rather than rebuilding after scanning.

Preserve artifact identity in downstream workflows. Runtime testing should load
an exported copy of the scanned image, and deployment should select the
published digest. Rebuilding for DAST, release publication, or deployment can
produce different bits and breaks the evidence chain.

These starters publish a single-platform image from manual dispatch on `main`. They do not test your application, wait for another workflow, sign images, or automatically deploy. Review CI and security results for the selected revision first.

Checksums, provenance, attestations, smoke tests, DAST handoff, and general
release records remain target architecture rather than current template
behavior. See [Delivery Architecture](delivery-architecture.md) and the
[Implementation Guide](../implementation-guide.md).

A login failure usually requires checking package permissions and GHCR access. A Docker build failure requires checking the build context, Dockerfile, and build arguments. A blocked gate requires fixing findings or recording reviewed, time-limited exceptions—not bypassing the gate in a commit message.

See [Container Template Requirements](../../../templates/workflows/containers/README.md).
