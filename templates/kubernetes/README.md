# Kubernetes Deployment Sample

Copy `deployment.yaml` to a chosen manifests directory when you need a starting Deployment resource. Replace `ghcr.io/OWNER/IMAGE:COMMIT_SHA`, port, health path, resource budgets, user ID, and writable-volume requirements. The sample assumes a non-root application on port 8080 with `/health`.

A cluster, namespace, registry access, and application configuration are prerequisites. Supply credentials through your cluster's secret-management process. This sample creates no Service, Ingress, database, or secrets.

Validate with your cluster's server-side dry run before applying, then check rollout status and readiness. Restricted permissions and a read-only filesystem require application compatibility; a valid manifest alone does not prove that it will start.
