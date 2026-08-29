# Runbook: Rotate gateway TLS certificates

Owner: Unassigned; ownership confirmation is tracked in [issue #16](https://github.com/PyKhaled/Nexus/issues/16)

Priority: P1 normally; P0 when expiry or compromise is imminent

Last reviewed: 2026-08-30 against source revision `bb9ea7d8502145867f0d73dfed71b972b4d906f3`

Last exercised: Not exercised; see `docs/runbooks/review-evidence-2026-08-30.md`

Applies to: the documented local TLS overlay; every shared environment must supply its own certificate paths and approval process

Severity: routine or critical

Command context: run from the repository root. When `secrets.env` is the
selected environment source, add `--env-file secrets.env` immediately after
`docker compose`; do not fall back to development placeholders.

## Purpose

Replace the gateway certificate and private key as one validated pair without
committing secret material or leaving an unverified pair active.

## Preconditions and safety

- Required access: approved certificate source and write access to the target
  secret mount.
- Required tools: OpenSSL, Docker Compose, and `curl`.
- User or data impact: a gateway recreation or reload can briefly interrupt
  HTTPS.
- Destructive or irreversible steps: replacing the active key pair; retain the
  previous pair in the approved secret store until verification completes.
- Escalate before proceeding when compromise is suspected, the private key was
  transmitted insecurely, or the target filenames/mount are uncertain.

Never add `fullchain.pem`, `privkey.pem`, or backups to Git.

## Detection

- Certificate expiry falls within the operator's rotation window.
- The issuer supplies a renewed pair.
- Security response orders emergency rotation after suspected key compromise.

## Diagnosis and preflight

Run these against the candidate files in their approved source location:

```sh
openssl x509 -in /absolute/approved/source/fullchain.pem -noout -subject -issuer -dates
openssl x509 -in /absolute/approved/source/fullchain.pem -checkend 604800 -noout
openssl x509 -in /absolute/approved/source/fullchain.pem -pubkey -noout | openssl pkey -pubin -outform DER | openssl dgst -sha256
openssl pkey -in /absolute/approved/source/privkey.pem -pubout -outform DER | openssl dgst -sha256
```

The two SHA-256 results must match. Confirm SAN coverage for every configured
TLS hostname. Stop if validation fails.

## Procedure

1. Preserve the active pair in the approved secret store. Do not create a
   repository backup file.
2. Install the candidate pair with certificate mode `0644` and key mode `0600`
   at the deployment's configured `GATEWAY_TLS_DIR`. For the local example the
   expected filenames are:
   `system/system-gateway/ssl/fullchain.pem` and
   `system/system-gateway/ssl/privkey.pem`.
3. Validate the TLS Compose overlay and NGINX configuration:

   ```sh
   docker compose -f compose.yml -f docs/compose/templates/compose.tls.example.yml config --quiet
   docker compose -f compose.yml -f docs/compose/templates/compose.tls.example.yml run --rm --no-deps gateway nginx -t
   ```

4. Recreate the gateway with the same overlay:

   ```sh
   docker compose -f compose.yml -f docs/compose/templates/compose.tls.example.yml up -d --build gateway
   ```

5. Verify the served certificate and endpoint:

   ```sh
   curl --fail --show-error --cacert /absolute/approved/source/issuer-ca.pem https://localhost/healthz
   openssl s_client -connect 127.0.0.1:443 -servername localhost </dev/null 2>/dev/null | openssl x509 -noout -serial -dates
   ```

   Omit `--cacert` only when the client already trusts the issuing chain; do
   not use `--insecure` as rotation verification.

## Success criteria

- Candidate certificate and private key public-key digests match.
- NGINX validation passes before activation.
- HTTPS health succeeds and the served serial/expiry match the candidate.
- The private key remains outside Git and is readable only as intended.

## Rollback or recovery

Restore the previously approved certificate and matching private key as a pair,
repeat NGINX validation, recreate the gateway, and verify the served serial.
Never mix one file from the old pair with one from the new pair. For suspected
compromise, rollback to the compromised key is not allowed; escalate for a new
pair instead.

## Escalation

| Condition | Contact or role | Information to provide |
| --- | --- | --- |
| Key compromise suspected | Security incident lead | Hostnames, issuer, serial, exposure window, storage and transfer path |
| New pair fails after old pair expired | Gateway operator and incident lead | Validation output, served serial, affected hosts, client errors |

## Follow-up

- Record issuer, serial, expiry, environment, activation time, and verifier.
- Revoke a compromised or superseded certificate when policy requires it.
- Update monitoring for the new expiry date.
