# ADR 0004: Integrations, Events, Audit, and Outbox

Status: Accepted

## Context

Swaflow integrates with WhatsApp, payment providers, calendars, and outbound webhooks. These providers retry, reorder, or duplicate events, so the backend needs a durable contract for external interactions.

## Decision

- Normalize provider integrations through adapters per provider type.
- Keep payment, WhatsApp, calendar, and outbound webhook logic behind canonical backend contracts.
- Store provider credentials encrypted and scoped by tenant.
- Treat event and audit records as first-class persistence concerns.
- Use an outbox or equivalent durable dispatch pattern for external delivery.
- Track processed external events to prevent duplicate side effects.
- Keep n8n peripheral only; it never owns critical state.

## Consequences

- Providers can be swapped without rewriting domain logic.
- Outbound delivery is safer because it happens after commit.
- Audit trails support support, export, and offboarding use cases.
- Additional schema and operational complexity are unavoidable, but they are cheaper than inconsistent business state.
