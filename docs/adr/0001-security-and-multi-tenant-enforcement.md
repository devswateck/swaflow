# ADR 0001: Security and Multi-Tenant Enforcement

Status: Accepted

## Context

Swaflow is a multi-tenant SaaS. The backend owns orders, inventory, payments, conversations, permissions, and integrations. A single cross-tenant mistake could leak data or mutate the wrong tenant's business state.

## Decision

- Use JWT for authenticated sessions.
- Enforce RBAC plus module-level permissions.
- Require `company_id` on every tenant-owned business operation.
- Return `404` for cross-tenant resources and `403` for same-tenant permission denial.
- Encrypt secrets at rest and redact them in logs, UI, and API responses.
- Validate webhook signatures or secrets before any business mutation.
- Treat payment, webhook, and event processing as idempotent.

## Consequences

- Security checks must live in backend services and dependencies, not only in the frontend.
- Repositories and helpers must consistently enforce tenant scope.
- Idempotency records and secure secret storage are mandatory persistence concerns.
- Debugging needs internal logs that preserve the real failure reason even when the external response is `404`.
