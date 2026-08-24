# Architecture Baseline

The template begins as one independently deployable process with no private
data store or external dependency. `project/app.py` owns the starter HTTP
interface, the Dockerfile owns packaging, and `tests/` verifies behavior.

A derived service repository must make these boundaries explicit before it is
added to a product composition:

- capability and accountable owner;
- consumers and versioned interfaces;
- domain and data ownership;
- private dependencies and migrations;
- identity, authorization, and secret boundaries;
- health, readiness, telemetry, and objectives; and
- build artifact, deployment, rollback, backup, and recovery contracts.

Do not retain unused generic directories merely to resemble a standard. Adapt
the template to the service's real operational boundary and record material
decisions as architecture decision records.
