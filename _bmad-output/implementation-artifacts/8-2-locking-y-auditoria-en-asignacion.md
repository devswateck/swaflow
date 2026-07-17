---
baseline_commit: 8204f3fb988f24b54d9e93636c2fa0a38c181e0d
---

# Story 8.2: Locking y auditoria en asignacion

Status: done

## Story

Como admin o usuario autorizado del tenant,
Quiero que la asignacion y la autoasignacion no dupliquen responsables ni eventos,
Para que cada chat tenga un unico responsable trazable.

## Acceptance Criteria

1. Dado que dos acciones intentan asignar el mismo chat, cuando el backend procesa la mutacion, entonces solo una puede consolidarse y la otra debe quedar como no-op sin romper el estado final.
2. Dado que una asignacion ya dejo al chat en el responsable y estado correctos, cuando llega una repeticion del mismo cambio, entonces no se crea un segundo evento `conversation.assigned` ni una segunda entrada de auditoria para la misma transicion.
3. Dado que autoasignacion y reasignacion manual compiten sobre el mismo chat, cuando ambas rutas se ejecutan casi al mismo tiempo, entonces el resultado final conserva un unico responsable valido y una sola transicion auditable.
4. Dado que un usuario sin permisos intenta tomar o reasignar un chat, cuando la mutacion llega al backend, entonces sigue aplicando el control de permisos existente y no se relaja por el cambio de locking.
5. Dado que la autoasignacion de un tenant esta habilitada y existe exactamente un usuario adicional elegible, cuando entra un chat nuevo o se procesa un envio saliente que dispara autoasignacion, entonces se consolida una sola asignacion real y se publica un solo evento de cambio.
6. Dado que una asignacion valida sucede, cuando se persiste la auditoria, entonces el registro conserva el mismo `conversation.assigned` como accion y no expone credenciales ni campos sensibles.

## Tasks / Subtasks

- [x] Harden assignment serialization in backend conversation flows. (AC: 1, 3, 5)
  - [x] Review `assign_conversation()` and `auto_assign_single_additional_user_chat()` together so they share the same transition rules and do not diverge under contention.
  - [x] If the current `Conversation ... with_for_update()` lock is not enough for the manual-vs-auto race, mirror the tenant-row locking pattern already used in `users.service._lock_tenant_scope()` to serialize the competing assignment paths consistently.
  - [x] Keep the existing no-op shortcut for unchanged assignment/status combinations so repeated requests do not emit new side effects.

- [x] Prevent duplicate assignment side effects. (AC: 2, 3, 5, 6)
  - [x] Ensure `conversation.assigned` is published only for a transition that truly changed the assignment.
  - [x] Ensure the audit write happens once per winning transition and is not replayed for a no-op or stale request.
  - [x] Preserve the current event payload shape and `record_audit_best_effort()` contract unless a stronger in-transaction audit is demonstrably required.

- [x] Cover the race with regression tests. (AC: 1, 2, 3, 4, 5)
  - [x] Add a focused backend regression that proves a repeated assignment does not create duplicate audit/event side effects.
  - [x] Add a test for the autoassign/manual overlap path, using the existing `conversation.assigned` assertions already present in inbox/WhatsApp tests.
  - [x] Keep the permission-denied cases intact for non-privileged users and for inbox access checks on assignees.
  - [x] If true concurrency is hard to express in the SQLite test fixture, use deterministic lock/guard assertions instead of timing-based sleeps.

- [x] Verify the implementation end to end. (AC: 1-6)
  - [x] Run the smallest useful backend test slice first, then the broader conversation/WhatsApp/user-permission suite if the first pass is green.
  - [x] Confirm no schema or API contract changes were introduced unless they were unavoidable.

## Dev Notes

### Business Context

- This is a hardening story, not a new Inbox feature.
- The product requirement is unique ownership per chat and a single auditable assignment transition.
- Epic 8 is explicitly about removing consistency gaps surfaced after the first feature wave; do not add new assignment modes or UI behavior here.

### Current Code State

- `backend/app/conversations/service.py` already centralizes assignment logic in `_apply_conversation_assignment()`.
- `assign_conversation()` already loads the conversation with `with_for_update()`, checks permissions, short-circuits unchanged assignments, commits, publishes `conversation.assigned`, and writes audit via `record_audit_best_effort()`.
- `auto_assign_single_additional_user_chat()` already locks the company row and the conversation row, then returns `None` if the chat is already assigned or no unique eligible assignee exists.
- `backend/app/whatsapp/service.py` calls `auto_assign_single_additional_user_chat()` from multiple send/receive flows and publishes/audits only when the helper returns a transition payload.
- `backend/app/audit/service.py` redacts sensitive metadata keys; any new audit metadata added here must stay compatible with that sanitizer.
- Existing tests already cover single-user autoassign, permission boundaries, and audit presence, but they do not yet prove duplicate side-effect suppression under a race.

### Hidden Failure Modes to Prevent

- A late manual reassignment and an autoassign decision both persist, leaving two `conversation.assigned` events for one real transition.
- A repeated assignment to the same user creates an extra audit row even though the chat state did not change.
- The race is "fixed" only in one path, while the other path still publishes stale assignment events.
- Permissions get bypassed while refactoring the locking path.
- A solution assumes SQLite concurrency behavior matches MySQL row locking. It does not.

### Implementation Guidance

- Prefer reusing the existing transition helper rather than splitting assignment rules across call sites.
- If you need stronger serialization than the current conversation lock provides, make the locking strategy explicit and consistent across manual assignment and autoassign.
- Keep the current event type `conversation.assigned` and the current audit action name.
- Do not change response schemas, route shapes, or frontend behavior for this story.
- Keep the change backend-only unless a test failure proves a frontend contract was accidentally relied on.
- Avoid schema churn unless a concrete, testable race requires it; there is no known need for a migration at this stage.

### Project Structure Notes

- The backend follows a domain layout under `backend/app/<domain>/` with `models.py`, `routes.py`, `schemas.py`, and `service.py`.
- For this story, the primary implementation target should remain `backend/app/conversations/service.py`.
- `backend/app/whatsapp/service.py` is a secondary target because it triggers autoassignment from multiple inbound/outbound paths.
- `backend/tests/test_user_permissions.py`, `backend/tests/test_whatsapp_setup.py`, and possibly `backend/tests/test_inbox_realtime.py` are the natural regression homes.
- Keep MySQL compatibility in mind even though the tests run on SQLite in memory.

### Testing Standards Summary

- Add regression coverage for both the winning transition and the losing no-op path.
- Prefer deterministic assertions on side effects, audit rows, and published events over sleep-based concurrency tests.
- Maintain the existing permission and tenant isolation expectations.
- Keep the suite focused on the smallest paths that prove the race is closed.

### Latest Tech Information

- No dependency upgrade is needed for this story.
- Use the existing Python 3.12, FastAPI, SQLAlchemy 2, and MySQL-compatible locking patterns already established in the codebase.
- Treat SQLite test behavior as a convenience layer only; MySQL row-level locking remains the production contract.

## Change Log

- 2026-07-15: Implemented shared company/conversation locking for assignment flows, preserved idempotent no-op behavior, and added regressions for repeated assignment and autoassign/manual overlap.
- 2026-07-15: Corrected a session-refresh edge case so autoassign does not wipe unflushed funnel defaults during conversation creation.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 8, Historia 8.2 and the success criteria around unique responsibility and auditable transitions]
- [Source: `_bmad-output/implementation-artifacts/epic-8-propuesta.md` - Epic 8 scope, history ordering, and the note that assignments must not duplicate responsible parties or audit entries]
- [Source: `_bmad-output/implementation-artifacts/8-1-blindaje-de-inbox-contra-estado-obsoleto.md` - previous story learnings about stale async state and the need for guarded side effects]
- [Source: `_bmad-output/project-context.md` - backend stack, MySQL decision, tenant-scoped services, and locking/audit rules]
- [Source: `backend/app/conversations/service.py` - `_apply_conversation_assignment()`, `assign_conversation()`, and `auto_assign_single_additional_user_chat()`]
- [Source: `backend/app/whatsapp/service.py` - inbound/outbound autoassignment call sites]
- [Source: `backend/app/audit/service.py` - audit persistence and redaction behavior]
- [Source: `backend/app/users/service.py` - tenant-row locking pattern used elsewhere in the backend]
- [Source: `backend/tests/test_user_permissions.py` - existing take/reassign permission coverage]
- [Source: `backend/tests/test_whatsapp_setup.py` - existing autoassign and audit assertions]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Story target resolved from sprint status as `8-2-locking-y-auditoria-en-asignacion`.
- Previous story `8-1` was analyzed to carry forward the stale-state hardening pattern.
- Conversation assignment flow already had partial locking, but the main risk was duplicate side effects across competing manual/auto assignment paths.
- The first implementation attempt exposed a stale-session edge case: refreshing the conversation row during autoassign could erase unflushed funnel defaults. The helper now locks without clobbering pending conversation state.

### Completion Notes List

- Shared the same locking order across manual assignment and autoassign by locking the tenant scope before the conversation row.
- Kept the no-op shortcut for repeated assignments, so only a real transition emits `conversation.assigned` and audit.
- Added regression coverage in `backend/tests/test_user_permissions.py` and `backend/tests/test_whatsapp_setup.py` for repeated assignment and autoassign/manual overlap.
- Verified the relevant backend suites with `backend/.venv/bin/python -m pytest backend/tests/test_user_permissions.py -q`, `backend/.venv/bin/python -m pytest backend/tests/test_whatsapp_setup.py -q`, `backend/.venv/bin/python -m pytest backend/tests/test_inbox_realtime.py -q`, and targeted autoassign checks in `backend/tests/test_tenant_and_orders.py`.
- Fixed a session-state edge case so default funnel assignment is preserved while assignment locking still uses the fresh database state for the tenant row.

### File List

- `backend/app/conversations/service.py`
- `backend/tests/test_user_permissions.py`
- `backend/tests/test_whatsapp_setup.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/8-2-locking-y-auditoria-en-asignacion.md`
