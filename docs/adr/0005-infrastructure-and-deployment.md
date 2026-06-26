# ADR 0005: Infrastructure and Deployment

Status: Accepted

## Context

Swaflow is a brownfield FastAPI + MySQL + Vite project. The repo already has Docker, migration tooling, and environment files. The deployment model should reinforce what exists instead of introducing platform overhead early.

## Decision

- Keep the backend stateless.
- Persist application state in MySQL.
- Use `.env`-based config per environment.
- Keep Docker Compose as the local development standard.
- Require lint, tests, migration checks, and container build validation in CI.
- Expose health checks for the app and critical dependencies.
- Scale vertically first, then horizontally only if needed.

## Consequences

- The operational model stays simple and understandable.
- CI becomes a gate for schema and code quality.
- The service can restart or scale without relying on local process state.
- Kubernetes and similar platform overhead remain out until the project genuinely needs them.
