---
baseline_commit: 8204f3fb988f24b54d9e93636c2fa0a38c181e0d
---

# Story 8.4: Separacion de estados humano, IA y clasificacion

Status: done

## Story

Como usuario del Inbox,
Quiero ver separados el responsable humano, el estado de la IA y la clasificacion comercial,
Para que la operacion sea clara y no mezcle conceptos distintos en la UI.

## Acceptance Criteria

1. Dado que una conversacion tiene responsable humano, estado de IA y clasificacion comercial, cuando el usuario la revisa en Inbox, entonces cada estado aparece con su propio contrato, etiqueta y accion visible, sin un badge o texto unico que los mezcle.
2. Dado que el usuario toma o reasigna un chat, pausa o reanuda la IA, o ajusta el funnel o paso comercial, cuando ejecuta cada accion, entonces solo cambia ese contrato y los demas se mantienen intactos.
3. Dado que una mutacion falla por permisos o validacion, cuando el backend responde error, entonces la UI no inventa estados locales ni transforma el error en otra mutacion distinta.
4. Dado que llegan eventos realtime de asignacion, IA o clasificacion, cuando Inbox refresca el detalle o la lista, entonces cada seccion se actualiza segun su propio evento y no hereda el texto de otra seccion.
5. Dado que se prepara contexto de agenda o una orden desde Inbox, cuando se construye el contexto derivado, entonces `assigned_user_id`, `ai_enabled`, `funnel_id`, `funnel_step_id` y `current_step` siguen siendo campos independientes y no se usan como proxies unos de otros.

## Tasks / Subtasks

- [x] Separate the Inbox surface into explicit human ownership, AI state and commercial classification blocks. (AC: 1, 2, 4)
  - [x] Keep the conversation lifecycle badge visible, but do not use it as a proxy for responsible owner, AI state or classification.
  - [x] Split the current combined header/actions in `frontend/src/App.tsx` into clearly named sections with dedicated labels for ownership, AI enablement and funnel classification.
  - [x] Reuse the existing conversation fields and helpers; do not invent new derived state that conflates `assigned_user_id`, `ai_enabled` and `funnel_*`.

- [x] Tighten the local label helpers so each state has one meaning. (AC: 1, 4, 5)
  - [x] Preserve `getConversationAssignmentLabel()` for human ownership only.
  - [x] Introduce or refactor small helpers for AI state and commercial classification labels so the UI stops reusing one block for multiple concepts.
  - [x] Keep event labels aligned with their event types: assignment, AI pause/resume, and funnel assignment must stay distinct in the timeline.

- [x] Protect the backend contract with focused regressions. (AC: 2, 3, 5)
  - [x] Add or update backend tests proving `assign_conversation()` does not mutate AI or funnel fields.
  - [x] Add or update backend tests proving `set_conversation_ai_enabled()` does not mutate assignment or classification fields.
  - [x] Add or update backend tests proving `assign_conversation_funnel()` does not mutate assignment or AI fields.
  - [x] Keep permission-denied paths intact for non-privileged users and ensure the frontend does not assume success when the backend rejects a change.

- [x] Verify the Inbox UX after the refactor. (AC: 1, 2, 4)
  - [x] Confirm the Inbox still shows the active thread, the owner, the AI state and the funnel in a way that is readable on desktop and mobile.
  - [x] Confirm a failed mutacion leaves the previous on-screen state honest instead of applying a fake local change.
  - [x] Run the smallest useful backend test slice plus frontend validation before handoff.

## Dev Notes

### Business Context

- This is a clarity and contract story, not a new business capability.
- The user must be able to distinguish three different concerns in the Inbox:
  - who owns the conversation,
  - whether the IA is active or paused,
  - how the conversation is classified commercially.
- The risk is semantic confusion: a UI that presents these as one merged "estado" invites wrong operational decisions.
- The backend already models these as separate concepts. The work should preserve that separation and improve the surface the operator sees.

### Current Code State

- `frontend/src/App.tsx:1843-1862` maps the API conversation into a client view model that already carries separate `assignedUserId`, `aiEnabled`, `funnelId`, `funnelStepId`, `funnelName` and `funnelStepName` values.
- `frontend/src/App.tsx:1969-2030` already gives distinct event labels for `conversation.assigned`, `conversation.ai_paused`, `conversation.ai_resumed` and `conversation.funnel_assigned`, but the Inbox surface still shows them close together and easy to confuse.
- `frontend/src/App.tsx:4678-4985` renders the Inbox with a shared lifecycle badge, a shared AI badge, a combined assignment block and a combined funnel block. The controls are separate, but the presentation still reads like one merged operational state.
- `frontend/src/App.tsx:3420-3539` sends assignment, funnel and AI mutations through distinct API routes. Do not collapse them into one mutation path.
- `frontend/src/App.tsx:5874-6291` appointment drafting also carries `assignedUserId` and funnel context independently. Preserve that separation when refactoring the Inbox surface.
- `backend/app/conversations/service.py:233-414` already mutates assignment, AI state and funnel classification through separate service functions and event types.
- `backend/app/conversations/schemas.py:37-86` already exposes separate fields for assignment, AI, funnel and current step in the read models.
- `backend/tests/test_inbox_realtime.py` and `backend/tests/test_user_permissions.py` already cover parts of the assignment, AI pause/resume and funnel flows. Extend those tests instead of inventing new contracts.

### Hidden Failure Modes

- A UI refactor turns "estado" into a single badge that hides whether the chat is assigned, the IA is paused or the funnel changed.
- A helper starts using `funnel_name` or `current_step` as a proxy for ownership.
- A failed AI pause or funnel change still updates the local UI, making the operator think the backend accepted the change.
- Event labels remain correct, but the visible layout still makes assignment look like an AI state or a classification state.
- Appointment or order context accidentally reads a combined operational summary instead of the discrete backend fields it needs.

### Implementation Guidance

- Prefer a narrow UI refactor inside `frontend/src/App.tsx` unless you discover a real reuse boundary worth extracting.
- Keep backend route shapes and payloads stable unless a test proves the current contract is insufficient.
- Preserve the existing `ConversationRead` / `ConversationDetailRead` field names; the story is about semantic separation, not renaming the API.
- Do not create a second source of truth in frontend state to "simplify" the screen. Use the API fields already present.
- Keep failure behavior honest: if the backend rejects a change, the UI should keep showing the previous real state.
- If you extract helpers, keep them tiny and local so the inbox shell does not become another abstraction layer.

### Project Structure Notes

- Primary target:
  - `frontend/src/App.tsx`
- Backend guardrail targets:
  - `backend/app/conversations/service.py`
  - `backend/app/conversations/schemas.py`
- Regression targets:
  - `backend/tests/test_inbox_realtime.py`
  - `backend/tests/test_user_permissions.py`
- Keep the single-surface React/Vite shell intact. Do not introduce a router or a new state container for this story.
- Preserve the current tenant-aware data flow and the existing `api<T>()` usage pattern.

### Testing Standards Summary

- Add deterministic backend regressions for contract isolation between assignment, AI state and funnel classification.
- Prefer direct assertions on model fields and event payloads over brittle string checks.
- Verify permission failures stay permission failures; do not let the frontend reinterpret them as another state change.
- If no frontend test harness is available, validate the Inbox surface with `npm run lint`, `npm run build`, and a manual review of the Inbox header/cards after the change.

### Latest Tech Information

- No dependency upgrade is required for this story.
- Use the existing React 18 / Vite 8 / TypeScript 5.6 / FastAPI / SQLAlchemy 2 stack already pinned in project context.
- The important constraint here is semantic correctness, not library churn.

## Change Log

- 2026-07-15: Separated Inbox ownership, IA state and commercial classification into distinct UI blocks; added backend regression coverage for mutation isolation; validated with frontend lint/build and the full backend test suite.

## References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Epic 8, Historia 8.4 and the acceptance criteria around separating human ownership, IA state and commercial classification]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/backlog.md` - priority order and the operational framing of the epic 8 hardening items]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/backlog-por-historias.md` - Historia 4 and its scope for separating human state, IA state and commercial state]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/project-context.md` - React/Vite stack, single-surface frontend, `api<T>()`, Zustand and no-new-router rules]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - Inbox workspace structure, no router, preserve shell and state patterns]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx` - conversation mapping, event labels, Inbox surface, assignment controls and funnel controls]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/conversations/service.py` - separate service functions for assignment, AI state and funnel classification]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/conversations/schemas.py` - read models exposing separate assignment, AI and funnel fields]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py` - existing regressions for AI pause/resume and conversation events]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_user_permissions.py` - existing permission coverage for inbox actions]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Story target resolved from sprint status as `8-4-separacion-de-estados-humano-ia-y-clasificacion`.
- The active codebase already separates the underlying backend concepts; the work is mainly to make the Inbox surface and its labels stop collapsing them into one operational bucket.
- The most relevant UI blocks are the conversation mapping, the Inbox header/action area and the event label helpers in `frontend/src/App.tsx`.
- The backend guardrails to preserve are the separate assignment, AI state and funnel mutators in `backend/app/conversations/service.py`.

### Completion Notes List

- Reworked the Inbox detail and list surfaces to show human ownership, IA state and commercial classification as distinct, labeled blocks instead of a merged operational badge.
- Added `getConversationAiLabel()` and `getConversationClassificationLabel()` helpers so the UI labels stay semantically separate from assignment.
- Added a backend regression proving `assign_conversation()`, `set_conversation_ai_enabled()` and `assign_conversation_funnel()` do not mutate each other's fields.
- Verified the frontend with `npm run lint` and `npm run build`.
- Verified the backend with `backend/.venv/bin/python -m pytest backend/tests/test_inbox_realtime.py backend/tests/test_user_permissions.py -q` and `backend/.venv/bin/python -m pytest backend/tests -q`.
- Story status moved to `review`.

### File List

- `frontend/src/App.tsx`
- `backend/tests/test_inbox_realtime.py`
- `_bmad-output/implementation-artifacts/8-4-separacion-de-estados-humano-ia-y-clasificacion.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
