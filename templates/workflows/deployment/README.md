# Development Deployment Request

Copy `devtron-notify.yml` to `.github/workflows/devtron-notify.yml` only when your Devtron integration accepts its `dockerImage` payload.

Create a `development` GitHub environment, configure any required approvals, and add `DEVTRON_WEBHOOK_URL_DEV` and `DEVTRON_API_TOKEN` secrets. Supply a previously published image reference when dispatching from `main`. The workflow does not build images or verify their scan status.

Adapt the payload to the receiving webhook and verify the request against a development pipeline first. An HTTP success means the request was accepted; verify the resulting rollout and application health separately. Missing credentials and unsuccessful HTTP requests fail. No automatic production deployment or hosted runtime verification is included.
