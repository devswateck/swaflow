---
baseline_commit: 8204f3fb988f24b54d9e93636c2fa0a38c181e0d
---

# Story 8.5: Rehidratacion de agenda desde snapshot persistido

Status: done

## Story

Como usuario autorizado del tenant,
Quiero que la intencion de agenda se reconstruya desde un snapshot persistido,
Para que el contexto de agenda no dependa de memoria local ni de carreras de UI.

## Acceptance Criteria

1. Dado que existe un snapshot de agenda preparado, cuando el usuario vuelve a abrir el hilo o filtra la bandeja, entonces el contexto se rehidrata desde backend usando el snapshot persistido mas reciente.
2. Dado que llega un snapshot mas nuevo mientras el mismo hilo sigue seleccionado, cuando la UI termina de resolver las solicitudes en vuelo, entonces el draft visible queda alineado con el snapshot nuevo y no con una version local obsoleta.
3. Dado que no existe snapshot preparado para la conversacion activa, cuando el usuario entra al modulo de citas, entonces no se muestra un draft inventado ni se arrastra contexto de otro hilo.
4. Dado que el usuario abre un borrador manual, cuando el inbox o sus filtros se refrescan, entonces el borrador manual permanece aislado y no es sobreescrito por el flujo de rehidratacion del inbox.
5. Dado que la rehidratacion depende de eventos y de respuestas async, cuando una respuesta vieja llega despues de una mas nueva, entonces la UI ignora la respuesta vieja y conserva el snapshot vigente.

## Tasks / Subtasks

- [x] Harden the appointment draft rehydration flow in `frontend/src/App.tsx`. (AC: 1, 2, 3, 5)
  - [x] Re-read the backend snapshot whenever the selected conversation is reopened, the inbox filter changes, or a newer persisted snapshot is observed.
  - [x] Treat `prepared_at` as the snapshot version marker and do not keep a draft only because `conversationId` did not change.
  - [x] Cancel or ignore stale async responses so an older `appointment-intent` response cannot overwrite a newer one.
  - [x] Keep the manual draft path separate; inbox refreshes must not clear or replace a manual draft unless the user explicitly starts a new one.

- [x] Verify the backend snapshot contract stays deterministic. (AC: 1, 2, 5)
  - [x] Confirm `GET /conversations/{id}/appointment-intent` keeps returning the most recent `conversation.appointment_intent_prepared` event for the company and conversation.
  - [x] Preserve the existing event ordering strategy so ties and repeated prepares still resolve to a single stable snapshot.
  - [x] Avoid introducing a new persisted draft store if the existing event timeline already provides the source of truth.

- [x] Add or extend regressions around stale draft handling. (AC: 1-5)
  - [x] Extend `backend/tests/test_inbox_realtime.py` to prove the latest prepared snapshot wins after multiple prepares and repeated reads.
  - [x] Add a regression that covers the no-snapshot path so the UI/API contract stays honest when the conversation has not prepared agenda context yet.
  - [x] If the frontend flow changes materially, validate the inbox and appointments surfaces with `npm run lint` and `npm run build`.

## Dev Notes

### Business Context

- This is a consistency story, not a new agenda feature.
- The system already models appointment intent as a persisted backend event; this story makes the frontend treat that persisted snapshot as the only source of truth.
- The main risk is stale UI state: a selected conversation can keep showing an old draft after filters, thread reopens, or concurrent realtime updates.
- Manual appointment drafts must stay isolated. Rehydration logic should only touch inbox-derived context.

### Current Code State

- `frontend/src/App.tsx:3218-3251` currently decides when to build or clear `appointmentDraft`. It only rehydrates when the selected conversation changes, so a newer backend snapshot can be missed if the same thread remains selected.
- `frontend/src/App.tsx:3427-3445` creates the manual appointment draft. That path must stay separate from inbox-derived rehydration.
- `frontend/src/App.tsx:2871` loads `GET /conversations/{conversationId}/appointment-intent` through `api<ApiAppointmentIntentContext>()`.
- `frontend/src/App.tsx:5850-5862` derives `draftKey` from `source`, `contactId`, and `preparedAt`. That is the right versioning signal, but it only works if the draft state actually updates when a newer backend snapshot arrives.
- `frontend/src/App.tsx` also refreshes conversation detail on realtime events, but the appointment draft effect still short-circuits when `conversationId` is unchanged, so a newer backend snapshot can remain invisible unless the draft is explicitly rehydrated.
- `backend/app/conversations/service.py:439-475` selects the latest `conversation.appointment_intent_prepared` event and builds the appointment intent context from that payload.
- `backend/tests/test_inbox_realtime.py:1280-1455` already covers the prepare/availability flow and proves the snapshot endpoint is stable across repeated reads. Extend it rather than replacing the contract.

### Hidden Failure Modes

- The UI keeps the last successful draft because the conversation id did not change, even though the backend snapshot did.
- A slower `appointment-intent` response overwrites a newer one after the user filtered the inbox or reopened the thread.
- Manual draft state is accidentally cleared by an inbox refresh, making the appointments page feel lossy.
- The frontend uses a stale `prepared_at` value as if it were still current, so the form pre-fills the wrong contact or funnel context.

### Implementation Guidance

- Keep the backend event timeline as the source of truth. Do not invent a second local persistence layer for agenda context.
- In React, prefer explicit cleanup and request cancellation for the async rehydration path. React treats `useEffect` as synchronization with external systems, and the browser `AbortController` is the correct primitive for cancelling in-flight requests.
- Rehydrate only when the active appointment context really changed. Equality by `conversationId` alone is not enough.
- If you need a version check, compare the latest backend `prepared_at` or the event timestamp against the current draft before committing state.
- Preserve existing labels and the `source` split between `inbox` and `manual`.

### Project Structure Notes

- Primary target:
  - `frontend/src/App.tsx`
- Regression target:
  - `backend/tests/test_inbox_realtime.py`
- Possible backend touchpoint only if the current contract proves insufficient:
  - `backend/app/conversations/service.py`
- Keep the single-surface React/Vite shell intact. Do not add a router, a new store, or `localStorage` persistence for this story.

### Testing Standards Summary

- Add a regression for the latest-snapshot-wins behavior.
- Add a regression for the no-snapshot path if the UI behavior changes.
- Verify stale async work cannot overwrite a newer draft.
- Prefer deterministic assertions on `prepared_at`, `conversation_id`, and selected payload fields over brittle text checks.

### Latest Tech Information

- No dependency upgrade is required for this story.
- The current project stack stays on the pinned React/Vite/TypeScript versions from project context.
- React `useEffect` is designed to synchronize with external systems and supports cleanup on dependency changes and unmount. Official docs: https://react.dev/reference/react/useEffect
- Use `AbortController` for request cancellation when a newer snapshot should replace an older in-flight fetch. Official docs: https://developer.mozilla.org/en-US/docs/Web/API/AbortController

### References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/backlog.md` - priority item 5 and its exit criterion for the latest persisted snapshot]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/backlog-por-historias.md` - Historia 5 objective, scope, files and exit criterion]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/epic-8-propuesta.md` - Historia 8.5 statement and success criteria]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Epic 8, Historia 8.5 acceptance criteria]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - agenda and persistence requirements]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/project-context.md` - React/Vite stack, `api<T>()`, Zustand and no-new-store rules]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - single-surface frontend, inbox workspace and no-router rule]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx` - appointment draft state, rehydration effect and `appointment-intent` loader]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/conversations/service.py` - latest persisted snapshot selection]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py` - current regressions around appointment intent and preference selection]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Story target resolved from sprint status as `8-5-rehidratacion-de-agenda-desde-snapshot-persistido`.
- The key risk is stale draft state in `frontend/src/App.tsx` when the same conversation remains selected and a newer backend snapshot arrives.
- The backend already persists appointment intent as events and exposes the latest snapshot through `GET /conversations/{id}/appointment-intent`; the frontend should rehydrate from that contract instead of caching its own version.

### Completion Notes List

- Rehydrated appointment drafts from the backend snapshot marker `prepared_at` instead of only from `conversationId`.
- Added abortable appointment-intent loading so stale async responses cannot overwrite a newer snapshot.
- Kept the manual draft path isolated from inbox-derived rehydration.
- Extended the backend regression so the latest prepared snapshot is the one returned after multiple prepares and repeated reads.
- Verified the impacted backend slice with `backend/.venv/bin/python -m pytest backend/tests/test_inbox_realtime.py -q`.
- Verified the frontend with `npm run lint` and `npm run build`.
- Resolved review findings by reloading the selected conversation detail after inbox filter refreshes and by ignoring stale `prepare-appointment` responses.
- Confirmed the latest backend regression suite passes after tightening the snapshot ordering test to target the actual older/newer event pair.
- Added a stable `snapshot_version` contract so the frontend can distinguish tied snapshots even when `prepared_at` collides.
- Normalized the appointment-intent regression to assert the selected snapshot by semantic version parts instead of by fragile string formatting.
- Removed the guard that dropped the freshly created prepare response and decoupled the inbox read-side effect from the abortable detail refresh.

### File List

- `frontend/src/App.tsx`
- `backend/app/conversations/schemas.py`
- `backend/app/conversations/service.py`
- `backend/tests/test_inbox_realtime.py`
- `_bmad-output/implementation-artifacts/8-5-rehidratacion-de-agenda-desde-snapshot-persistido.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-07-15: Implemented snapshot-versioned appointment draft rehydration, added abortable stale-response handling, and strengthened the backend regression for latest-snapshot-wins.
- 2026-07-15: Addressed code review findings for inbox filter rehydration and stale appointment prepare responses; validated with frontend lint/build and backend regression tests.
- 2026-07-16: Added stable snapshot versioning to the appointment-intent contract and hardened the regression for tied `prepared_at` timestamps.
- 2026-07-16: Removed the fresh-prepare response discard path and kept inbox read marking independent from abortable detail reloads.
- 2026-07-16: Closed the story after review with no remaining actionable findings.
