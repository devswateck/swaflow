# ADR 0002: Data Architecture and Persistence

Status: Accepted

## Context

Swaflow needs reporting, filtering, joins, and durable operational records. JSON-heavy storage would weaken queryability, tenant filtering, and idempotency.

## Decision

- Use a normalized relational core in MySQL.
- Restrict `JSON` to metadata, provider payloads, and flexible configuration fields.
- Require `company_id` on every tenant-owned table.
- Use unique constraints scoped by `company_id` where natural keys exist.
- Keep audit and event tables durable and queryable.
- Apply backward-compatible Alembic migrations first, then cleanup later.

## Consequences

- The schema will be more explicit and easier to report against.
- Provider-specific payloads stay flexible without turning the core into a blob store.
- Migration discipline becomes part of the delivery process.
- Large-table changes must be additive and carefully rolled out.
