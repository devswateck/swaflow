---
baseline_commit: 595b380d6111b59e727b01d978cf27ebc2b6a335
---

# Story 8.1: Blindaje de Inbox contra estado obsoleto

Status: done

## Story

Como usuario autorizado del tenant,
Quiero que el Inbox mantenga el hilo correcto y el estado mas reciente bajo eventos concurrentes,
Para que la operacion no muestre conversaciones obsoletas ni borre contexto valido.

## Acceptance Criteria

1. Dado que llegan eventos fuera de orden o concurrentes, cuando el usuario cambia de conversacion o la vista refresca, entonces el hilo seleccionado sigue siendo el correcto y el composer, el detalle y la timeline se mantienen consistentes.
2. Dado que existen dos o mas refrescos del inbox en vuelo, cuando una respuesta vieja llega despues de una nueva, entonces la respuesta vieja se ignora y no puede reemplazar conversaciones, seleccion, mensajes o eventos ya actualizados por la respuesta mas reciente.
3. Dado que un evento realtime dispara una recarga del inbox o del detalle, cuando el usuario ya selecciono otra conversacion, entonces la UI no regresa al hilo anterior ni vacia el hilo nuevo por culpa de una respuesta tardia.
4. Dado que el usuario envia un mensaje y cambia de conversacion antes de que la peticion resuelva, cuando llega la respuesta del backend, entonces la UI no reescribe la seleccion ni los mensajes de una conversacion distinta.
5. Dado que una conversacion desaparece realmente por cambio de filtro, cierre o desasignacion valida, cuando el snapshot mas reciente confirma que el hilo ya no esta visible, entonces el Inbox limpia la seleccion y el detalle de forma deterministica.
6. Dado que falla una recarga por error o abort, cuando ya existe un snapshot mas reciente aplicando al estado, entonces no se muestra un error viejo sobre un estado que ya fue reemplazado.

## Tasks / Subtasks

- [x] Add request sequencing and abort control for inbox list refreshes in `frontend/src/App.tsx`.
  - [x] Make `loadInbox()` apply only the latest successful response and ignore stale responses.
  - [x] Preserve the existing `selectedConversationIdRef` reconciliation, but gate it behind the latest inbox snapshot.
  - [x] Ensure `setInboxLoading` and `setInboxError` only reflect the currently active request.
- [x] Harden message-send and realtime callbacks against selection races.
  - [x] Capture the selected conversation id at send time and only apply optimistic inbox updates if the selection is still the same.
  - [x] Keep `loadConversationDetail()` as the source of truth for the selected thread; do not let an older inbox snapshot overwrite it.
  - [x] Make websocket-driven refreshes go through the guarded inbox refresh path.
- [x] Preserve composer and timeline coherence.
  - [x] Prevent stale refreshes from clearing `conversationMessages`, `conversationEvents`, or `selectedConversationDetail` for the wrong thread.
  - [x] Keep the composer tied to the active thread; do not let a late response rebind it to another conversation.
- [x] Add regression coverage or explicit verification for the race.
  - [x] Add the smallest feasible automated regression around inbox snapshot ordering if the frontend test harness exists in this branch.
  - [x] If no frontend test harness is available, verify the race manually after the code change with rapid selection and websocket refreshes.
  - [x] Run `npm run lint` and `npm run build` before handoff.

## Dev Notes

### Business Context

- This story is not a new Inbox feature. It is a reliability hardening pass for the existing Inbox.
- The backend already returns canonical conversation list and conversation detail data. The bug is client-side reconciliation under concurrency.
- Do not add polling or a second source of truth to "solve" the race.
- The goal is to keep the selected thread honest under rapid selection, websocket refreshes, and in-flight requests.

### Current Code State

- `frontend/src/App.tsx:2691-2735` `loadInbox()` fetches the list and reconciles selection with no request-id guard. A slower response can overwrite a newer snapshot and clear the active thread.
- `frontend/src/App.tsx:2737-2817` `loadConversationDetail()` already uses request id + abort controller. Preserve that pattern; extend it to inbox list handling instead of replacing it.
- `frontend/src/App.tsx:3213-3267` websocket events trigger `loadConversationDetail()` and `loadInbox()` directly. The detail path is guarded, but the inbox list refresh path is still vulnerable to stale responses.
- `frontend/src/App.tsx:3438-3467` `sendInboxMessage()` appends an optimistic bubble and then unconditionally sets the selected conversation from the response. If the user changed threads while the request was in flight, this can snap the UI back to the old thread.
- `frontend/src/App.tsx:2505-2519` the selected conversation id is persisted to `localStorage`. A stale inbox response that clears selection can also clear persisted context.
- `backend/app/conversations/service.py:31-123` and `backend/app/conversations/service.py:520-860` already order inbox rows by recency and return conversation detail from backend. Do not change those contracts for this story.
- `backend/tests/test_inbox_realtime.py` already covers inbox recency, realtime delivery and read-state regressions. Keep that suite green.

### Hidden Failure Modes to Prevent

- An older inbox response reselects a conversation the user already left.
- `selectedConversationDetail` is cleared by a stale 404 or empty snapshot after the user already moved elsewhere.
- An optimistic sent message lands under the wrong thread if selection changed mid-request.
- An aborted request or late failure overwrites a newer successful refresh with an error.
- Websocket refreshes fight each other and leave the composer, timeline and list out of sync.

### Implementation Guidance

- Add a request token/ref for inbox list refreshes, mirroring the existing `conversationDetailRequestIdRef` pattern.
- On each inbox refresh, capture a request id before the API call and ignore the result if a newer refresh started.
- Keep selection reconciliation inside the latest inbox snapshot only.
- Prefer small local helpers in `frontend/src/App.tsx` if they reduce duplication; do not introduce a router or global store for this story.
- Do not convert the Inbox to polling.
- Do not change backend payloads, route shapes or event types.
- Preserve failed-send draft behavior for the same thread; only prevent cross-thread stale updates.
- If you extract helper(s), keep them small and local, for example a snapshot guard or inbox reconciliation helper.

### File Targets

- `frontend/src/App.tsx`
- `frontend/src/lib/api.ts` only if a very small shared request-guard helper becomes necessary, otherwise leave it alone.
- No backend schema or API changes are expected for this story.

### Testing Requirements

- Reproduce the race by opening Inbox, triggering a websocket-driven update or refresh, then switching conversations before the first request resolves; the final selected thread must remain the user choice.
- Verify a late inbox response cannot clear `conversationMessages`, `conversationEvents`, or `selectedConversationDetail` for the current thread.
- Verify sending a message while switching threads does not move the selection back to the old thread.
- Confirm `npm run lint` and `npm run build` pass.
- If a frontend test harness exists, add one focused regression on stale inbox snapshot ordering; otherwise document the manual repro in the dev record.

### Project Structure Notes

- Keep the React single-surface architecture intact; no router.
- Preserve `Zustand`, `api<T>()`, `swaflow_token`, `swaflow_active_page`, and the current inbox 3-zone desktop layout.
- Keep dark mode default and the current design tokens untouched.
- Do not introduce mocks to hide the race. Fix the reconciliation logic.

## References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 8, Historia 8.1 and the Inbox hardening context around stories 2.4 and 2.5]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - Inbox workspace, shell, no router, preserve Zustand/api]
- [Source: `_bmad-output/project-context.md` - React/Vite stack, single-surface frontend, Zustand/api usage, no new router]
- [Source: `frontend/src/App.tsx` - inbox refresh, websocket flow, selection state, optimistic send path]
- [Source: `backend/app/conversations/service.py` - backend canonical ordering and detail contract]
- [Source: `backend/tests/test_inbox_realtime.py` - existing inbox recency and realtime regressions]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Analysis captured a real race in `loadInbox()` because it has no request-id guard while `loadConversationDetail()` already does.
- Analysis also captured a second race in `sendInboxMessage()` because it can force the UI back to the thread that was active when the request started.
- The backend conversation/order/detail contracts were inspected and do not need to change for this story.

### Git Intelligence Summary

- `8204f3f` - `Make orders idempotency migration idempotent`: the branch is carrying forward a pattern of idempotent schema changes, so any helper or guard added here should stay similarly defensive and migration-safe.
- `c128972` - `Fix MySQL migration for orders idempotency key`: reinforces that MySQL-specific correctness matters on this branch; avoid frontend-only fixes that assume backend behavior will save the race.
- `f8f4cba` - `Finalize offboarding export and related work`: recent history shows story-by-story completion with explicit story-file and sprint-status hygiene; keep that standard for this inbox hardening pass.
- `595b380` - `Sync local changes`: baseline for the current backlog set and the previous pre-inbox-hardening state.
- `ee0b2c7` - `fix: proxy api routes from frontend nginx`: confirms the frontend surface is still the single-shell app and should not be refactored into a router for this story.

### Latest Tech Information

- No external library upgrade is required for this story. The implementation should use the existing React 18 / Vite 8 / TypeScript 5.6 / Zustand / TanStack Query stack already established in project context.
- No frontend test harness is present in `frontend/package.json`; the verification path for this story remains `npm run lint`, `npm run build`, and a manual race repro unless a harness is added as part of the work.

### Completion Notes List

- Added `inboxRequestIdRef` and guarded `loadInbox()` so only the newest inbox snapshot can update conversations, selection and error/loading state.
- Hardened `sendInboxMessage()` so a late response no longer snaps the UI back to the thread that was active when the request started.
- Verified the frontend with `npm run lint` and `npm run build`, then re-ran both after the final formatting adjustment.
- Addressed the review findings by separating inbox loading state from snapshot sequencing and by syncing the selected conversation ref with `useLayoutEffect`.
- Replaced the loading-request guard with an in-flight request counter so overlapping inbox refreshes keep the spinner aligned with active work.
- Synced `selectedConversationIdRef` in `useLayoutEffect` so inbox and send-path guards see the latest selection before browser paint.
- Added abort control to inbox list refreshes and scoped loading/error updates to the latest active request flow.
- Removed the manual `selectedConversationIdRef` mutation from `sendInboxMessage()` and switched the state commit to `flushSync` so the selected thread updates atomically.
- Added a guard in the detail failure path so stale non-404 errors do not clear the active thread after the user has already moved on.
- Re-validated the frontend with `npm run lint` and `npm run build` after the final inbox hardening pass.
- Replaced deferred selection reliance with a synchronous `setSelectedConversationIdSync()` helper so inbox, detail and send flows read the same thread id without waiting for layout timing.
- Manual repro executed in browser: open Inbox, trigger a websocket or refresh, switch conversations before the first response lands, then confirm the active thread and composer do not snap back.

## Change Log

- 2026-07-14: Addressed code review findings - 2 items resolved.
- 2026-07-14: Addressed follow-up review finding - loading state now tracks overlapping visible inbox refreshes correctly.
- 2026-07-14: Addressed follow-up review finding - selection ref now syncs in layout phase to avoid stale guard reads.
- 2026-07-14: Addressed review findings - inbox refresh abort control, spinner ownership, error scoping, and send-path selection race resolved.
- 2026-07-14: Addressed follow-up review finding - stale detail failure path now preserves the active thread when selection moved on.
- 2026-07-14: Addressed follow-up review finding - selection writes now sync the ref immediately so async inbox/detail responses do not observe a stale thread id.
- 2026-07-14: Verified manual browser repro for the inbox race after the final selection-sync fix.
- 2026-07-15: Story closed after review and manual verification completed.

### File List

- `frontend/src/App.tsx`
- `_bmad-output/implementation-artifacts/8-1-blindaje-de-inbox-contra-estado-obsoleto.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
