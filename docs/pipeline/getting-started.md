# Getting Started

## 1. Choose a capability

Start with application CI. Add security and publishing when you have verified the first workflow. Use [Choosing a Pipeline](choosing-a-pipeline.md) to select a combination.

Prerequisites: an application repository on GitHub, Actions enabled, a supported runtime, committed dependency manifests and lockfiles where applicable, and real tests. Container workflows additionally require Docker-compatible application source and a Dockerfile.

## 2. Copy the selected files

Use the file-by-file mappings in an [example](../../examples/README.md). Open the destination repository and copy files to their documented paths, including `.github/` and other hidden directories. Review existing files before replacing or merging them.

Security templates require the whole `tools/secreport/` directory and `security/` configuration, not just the workflow YAML. Choose one publisher; do not enable both container publishing templates.

## 3. Adapt before enabling

Set runtime versions, package manager commands, branch names, test settings, database services, and Docker paths. Review [permissions and secrets](reference/secrets-and-permissions.md), [risk policies](reference/risk-policies.md), and dependency updates. Add branch protection or rulesets for your required check names in GitHub.

## 4. Verify with a pull request

Run the documented application commands locally, then open a test PR. Confirm a passing check, deliberately introduce a failing test, and confirm CI blocks it. With security enabled, introduce a synthetic finding in a disposable branch and verify both the finding and gate failure. Remove the fixture afterward.

Done means the expected checks have run on the intended commit, failures are visible, and branch rules require them. A syntactically valid YAML file alone does not establish this.

## 5. Publish deliberately

After CI is green on `main`, manually run the chosen publisher. Confirm the commit-tagged image exists in your registry. For scan-gated publishing, verify a failed gate prevents the login/push steps. A deployment request is separate from confirming application health.
