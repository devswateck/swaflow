# ADR 0003: API and Communication Patterns

Status: Accepted

## Context

Swaflow exposes a FastAPI backend to a React/Vite frontend. The API must be predictable across domains and should not leak tenant or permission complexity into the UI.

## Decision

- Use a versioned REST API under `/api/v1`.
- Keep routers thin and put business logic in domain services.
- Use a fixed request order: authenticate, resolve tenant, enforce tenant guard, check permissions, then run domain validation.
- Standardize responses with `data` for single resources and `items + meta` for lists.
- Standardize errors: `401`, `403`, `404`, `409`, and `422` with stable meanings.
- Keep visible error messages in Spanish.
- Use typed frontend API helpers such as `api<T>()` and TanStack Query.

## Consequences

- Frontend and backend can share stable contracts.
- Controllers stay small and domain rules remain in services.
- Cross-domain behavior becomes easier to test and reason about.
- The frontend should never rely on hidden UI state for security.
