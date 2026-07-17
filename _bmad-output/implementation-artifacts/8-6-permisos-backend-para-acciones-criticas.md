---
baseline_commit: 8204f3fb988f24b54d9e93636c2fa0a38c181e0d
---

# Story 8.6: Permisos backend para acciones criticas

Status: done

## Story

Como operador del sistema,
quiero que las acciones criticas del Inbox e integraciones se validen en backend,
para que el frontend no sea la unica barrera de seguridad.

## Acceptance Criteria

1. Dado que un usuario autenticado sin permiso de modulo intenta ejecutar una mutacion critica del Inbox o de integraciones, cuando la solicitud llega al backend, entonces el sistema la rechaza con `403 Forbidden` y no modifica ningun estado.
2. Dado que un usuario intenta mutar un recurso de otro tenant, cuando la solicitud llega al backend, entonces el sistema responde `404 Not Found` y no filtra existencia cruzada entre tenants.
3. Dado que una accion critica del Inbox fue permitida por permisos de modulo y pertenencia al tenant, cuando la solicitud llega al backend, entonces el cambio se persiste, se emite el evento esperado y la auditoria sigue funcionando como antes.
4. Dado que un flujo interno del sistema reutiliza utilidades compartidas de mensajes o conversacion, cuando ese flujo no representa una accion humana directa, entonces no debe romperse por un candado de permisos demasiado amplio.
5. Dado que una mutacion de integraciones esta protegida, cuando falla por permisos o tenant, entonces no deben persistir credenciales, config parcial, eventos ni audit logs de exito.

## Tasks / Subtasks

- [x] Harden the human-facing Inbox write paths in `backend/app/conversations/routes.py`.
  - [x] Review every mutating endpoint and require the module permission that matches the surface instead of relying only on `get_current_user`.
  - [x] Keep the scope focused on write actions; do not gate read-only inbox views unless the story explicitly needs it.
  - [x] Preserve the existing 404 tenant isolation contract on every path that looks up a conversation or related resource.

- [x] Keep shared service functions safe for system flows in `backend/app/conversations/service.py`.
  - [x] Do not add a blanket permission check to `append_message`, because WhatsApp inbound and other internal flows reuse it.
  - [x] If a route-specific human action needs its own guardrail, prefer a thin wrapper or route-level dependency over changing the shared primitive.
  - [x] Make sure any new helper preserves the current audit/event/realtime behavior on successful writes.

- [x] Verify integrations stay module-protected and tenant-scoped in `backend/app/integrations/routes.py` and `backend/app/integrations/service.py`.
  - [x] Keep the `integrations` module gate on create, update and delete flows.
  - [x] Preserve encrypted credential handling and avoid partial writes on validation failure.
  - [x] Confirm cross-tenant access still returns `404`, not `403`, for existing resources.

- [x] Extend backend regressions for denied access and no side effects.
  - [x] Add/extend tests in `backend/tests/test_user_permissions.py` for Inbox write actions that should now reject missing module permission.
  - [x] Add/extend tests for integrations permission failures and cross-tenant resource lookups.
  - [x] Assert that denied requests do not mutate assignments, messages, integrations, audit logs or realtime events.

## Dev Notes

### Business Context

- This is a security hardening story, not a new feature.
- The product already uses module permissions and tenant scoping; the gap is that some human-facing write paths still depend too much on the frontend or on auth-only route dependencies.
- The expected behavior is consistent with the rest of the platform: `403` for missing permission, `404` for cross-tenant or missing resources.
- Keep system-driven flows working. WhatsApp inbound processing and other internal orchestration may reuse the same lower-level primitives as the human UI, so the guardrail must be placed with care.

### Current Code State

- `backend/app/users/permissions.py` already defines module keys, default safe modules and the `ensure_module_access` helper.
- `backend/app/auth/service.py` already exposes `require_module_access(...)`, which is the preferred backend dependency pattern for route-level authorization.
- `backend/app/conversations/routes.py` already protects `assign`, `assign-funnel`, `prepare-appointment`, `ai/pause` and `ai/resume` with `require_module_access("inbox")`, but `create_conversation`, `close_conversation`, `mark_conversation_read` and `send_message` still depend only on `get_current_user`.
- `backend/app/conversations/service.py` contains the actual state transitions, event emission and audit logging. `append_message(...)` is reused by WhatsApp and other internal flows, so a generic permission check there would be too broad.
- `backend/app/integrations/routes.py` already uses `require_module_access("integrations")` for all CRUD endpoints. The story should preserve that contract and ensure tests cover the denied paths.
- `backend/app/integrations/service.py` already encrypts secrets and records audit events after successful commits. Any new regression must verify that rejected requests do not leave partial records behind.
- Existing tests already cover several permission boundaries in `backend/tests/test_user_permissions.py` and WhatsApp module checks in `backend/tests/test_whatsapp_setup.py`, so extend those patterns instead of inventing a new testing style.

### Hidden Failure Modes

- A user without inbox permission can still create or send messages through auth-only routes if the backend does not enforce module access.
- A service-level guard added in the wrong place can accidentally break WhatsApp inbound processing, because shared helpers are used by both human and system paths.
- A failed permission check can still leave side effects if the code writes before validating, especially around integrations and audit hooks.
- Cross-tenant access can leak whether a resource exists if the implementation returns `403` instead of `404`.

### Implementation Guidance

- Prefer the existing backend authorization primitives: `require_module_access(...)` at the route layer and `ensure_module_access(...)` only where a service truly needs to defend itself.
- Keep the human/system split explicit. If the manual Inbox path needs extra protection, add a route-specific entry point instead of changing the shared message append primitive.
- Maintain the current error contract:
  - `403` for missing module permission.
  - `404` for wrong tenant or missing resource.
  - `422` only for invalid payloads or invalid permission keys.
- Do not introduce a new auth model, a new permission table or a new router structure for this story.
- Preserve side effects on success: realtime events, audit logs and commits should continue to happen exactly once for allowed actions.

### Project Structure Notes

- Primary route target:
  - `backend/app/conversations/routes.py`
- Primary service target:
  - `backend/app/conversations/service.py`
- Integration route/service targets:
  - `backend/app/integrations/routes.py`
  - `backend/app/integrations/service.py`
- Permission helpers:
  - `backend/app/users/permissions.py`
  - `backend/app/auth/service.py`
- Regression targets:
  - `backend/tests/test_user_permissions.py`
  - `backend/tests/test_whatsapp_setup.py`
  - `backend/tests/test_inbox_realtime.py` if an inbox-side regression is needed for the final route behavior
- Avoid changing the shared `append_message` primitive unless you can prove the internal WhatsApp flows still work.

### Testing Standards Summary

- Test the denial path first: missing permission should fail before any mutation happens.
- Test tenant isolation separately from permissions, because the error code is different and the behavior is part of the contract.
- Assert on side effects, not just HTTP codes. Check that assignments, messages, integration rows, audit logs and realtime publishes do not happen on denied requests.
- Keep existing success-path regressions intact so the story does not silently regress normal Inbox or integrations flows.

### Latest Tech Information

- No dependency upgrade is required for this story.
- Stay within the pinned project stack from `project-context.md`: FastAPI, SQLAlchemy 2, Pydantic and the existing auth helpers.
- Use the normal FastAPI dependency pattern already established in the codebase instead of introducing a new auth abstraction.
- The backend status-code contract is stable and should stay aligned with FastAPI's standard `HTTPException` handling.

### References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Epic 8, Historia 8.6 statement and acceptance criteria]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - module permissions, Inbox security and integration requirements]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - single-surface frontend and no-router guardrails]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/project-context.md` - backend stack, module permission helpers and tenant-scoped service rules]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/auth/service.py` - `require_module_access` and current auth dependencies]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/users/permissions.py` - module key set, default permissions and `ensure_module_access`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/conversations/routes.py` - current Inbox route dependencies and write-path gaps]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/conversations/service.py` - shared message and conversation primitives, event emission and tenant checks]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/integrations/routes.py` - current integrations authorization pattern]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/integrations/service.py` - encrypted config handling and audit behavior]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_user_permissions.py` - existing permission regressions]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_whatsapp_setup.py` - WhatsApp/integration permission regressions]

## Dev Agent Record

### Agent Model Used

GPT-5

### Baseline / Discovery Notes

- Story target resolved from sprint status as `8-6-permisos-backend-para-acciones-criticas`.
- The most likely gap is in Inbox write endpoints that still depend only on authentication, while shared lower-level helpers must stay usable by system flows.
- Integration CRUD already uses module authorization, so the implementation should preserve that contract and focus on regressions plus any missing write-path guards.

### Debug Log

- Added `require_module_access("inbox")` to the human-facing Inbox write routes in `backend/app/conversations/routes.py`.
- Kept `append_message(...)` unchanged so WhatsApp and other internal flows continue to reuse the shared primitive safely.
- Added regressions in `backend/tests/test_user_permissions.py` for denied Inbox writes, unchanged side effects, and integration permission / tenant isolation checks.
- Verified the impacted backend surfaces with `backend/.venv/bin/python -m pytest backend/tests/test_user_permissions.py backend/tests/test_inbox_realtime.py backend/tests/test_whatsapp_setup.py -q`.

### Completion Notes

- Inbox write routes now enforce backend module permissions on create, close, mark-read and send-message operations.
- Shared service-level message handling remains available to internal flows; the guardrail lives at the route boundary.
- Integration write routes remain module-protected and still return `404` for cross-tenant resource access.
- The new regression coverage confirms denied requests do not mutate conversation state, messages, integrations or audit logs.

## File List

- `backend/app/conversations/routes.py`
- `backend/tests/test_user_permissions.py`
- `_bmad-output/implementation-artifacts/8-6-permisos-backend-para-acciones-criticas.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-07-16: Created ready-for-dev story context for backend permission hardening on critical Inbox and integration actions.
- 2026-07-16: Implemented backend route-level permission guards for Inbox write actions and added regression coverage for denied access and tenant isolation.
