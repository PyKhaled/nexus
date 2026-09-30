# Architecture

Nexus separates reusable library capabilities from repository tools and operational scripts.

```text
nexus_assembler/         reusable Python APIs
├── assembly/            orchestration, resolution, package writing
├── validation/          read-only validation
├── inspection/          read-only information extraction
├── policy/              policy evaluation
├── config/              YAML/canonicalization/merge primitives
└── repository/          repository declarations + explicit mutating operations

tools/                   inspect / validate / audit / verify
scripts/                 operations that may change state
```

## Rule

- **Tools** inspect, validate, audit, or verify. They are designed to be safe building blocks for developers, CI, and AI agents.
- **Scripts** perform operations. They may change files, Git state, configuration, or runtime state and should document those side effects.

The `nexus` CLI remains the human-facing product interface and preserves the original Ruby command model.
