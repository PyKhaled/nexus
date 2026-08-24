# Public Website Capability

Status: Partial development implementation

Owner: Unassigned

Implementation: WordPress 7.0.2 with MySQL 8.0

## Capability

Provide the product's public information, marketing, landing, conversion, and
optional commerce presence. The capability is implementation-independent;
WordPress is the current default reference implementation.

Product application experiences, authentication, help-center ownership, and
business APIs are outside this stack unless an accepted decision explicitly
combines them.

## Stack

```text
public website capability
|-- website       WordPress runtime
`-- website-db    private MySQL dependency
```

The database and uploaded content are private to the website stack.

## Interfaces

| Interface | Consumer | Current contract |
| --- | --- | --- |
| `http://app.localhost` | Public visitors | Gateway-routed website |
| WordPress administration | Content administrators | WordPress administrative interface |
| MySQL protocol | WordPress only | Private internal dependency |

## Configuration and data

The active root Compose definition supplies database connection values. Local
defaults are development placeholders. WordPress files use the
`wordpress-data` volume and MySQL uses `website-db-data`.

The repository does not yet reproducibly package product themes, plugins,
content, uploads, migrations, or seed data. Local implementation files under
`system-website/system-website/` are not currently built or mounted by the
active composition.

## Local composition

Compose services: `website`, `website-db`

Network: `nexus-system`

Public route: gateway only

```sh
make website
docker compose ps website website-db
```

## Replacement contract

A WordPress, Drupal, Hugo, Jekyll, or custom replacement must deliberately
address:

- the stable public route;
- content ownership and editorial workflow;
- metadata, redirects, analytics, forms, and conversion behavior;
- commerce entry points when applicable;
- asset, media, and search behavior;
- migration and rollback; and
- build, deployment, health, security, backup, and recovery.

A static generator produces a versioned static artifact and does not require a
database merely to match the WordPress runtime shape.

## Known gaps

- No reproducible product theme, plugin, content, or static-site implementation.
- No backup, restore, migration, or upgrade runbook.
- No explicit help-center, commerce, analytics, or form contract.
- Shared-environment secret and media-storage strategies are undefined.
