---
baseline_commit: 595b380d6111b59e727b01d978cf27ebc2b6a335
---

# Story 8.1: Blindaje de Inbox contra estado obsoleto

Status: backlog

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

- [ ] Add request sequencing and abort control for inbox list refreshes in `frontend/src/App.tsx`.
  - [ ] Make `loadInbox()` apply only the latest successful response and ignore stale responses.
  - [ ] Preserve the existing `selectedConversationIdRef` reconciliation, but gate it behind the latest inbox snapshot.
  - [ ] Ensure `setInboxLoading` and `setInboxError` only reflect the currently active request.
- [ ] Harden message-send and realtime callbacks against selection races.
  - [ ] Capture the selected conversation id at send time and only apply optimistic inbox updates if the selection is still the same.
  - [ ] Keep `loadConversationDetail()` as the source of truth for the selected thread; do not let an older inbox snapshot overwrite it.
  - [ ] Make websocket-driven refreshes go through the guarded inbox refresh path.
- [ ] Preserve composer and timeline coherence.
  - [ ] Prevent stale refreshes from clearing `conversationMessages`, `conversationEvents`, or `selectedConversationDetail` for the wrong thread.
  - [ ] Keep the composer tied to the active thread; do not let a late response rebind it to another conversation.
- [ ] Add regression coverage or explicit verification for the race.
  - [ ] Add the smallest feasible automated regression around inbox snapshot ordering if the frontend test harness exists in this branch.
  - [ ] If no frontend test harness is available, verify the race manually after the code change with rapid selection and websocket refreshes.
  - [ ] Run `npm run lint` and `npm run build` before handoff.

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

### Completion Notes List

- To be filled by the implementation agent.

### File List

- `_bmad-output/implementation-artifacts/8-1-blindaje-de-inbox-contra-estado-obsoleto.md`
