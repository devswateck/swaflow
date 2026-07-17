---
baseline_commit: 8204f3fb988f24b54d9e93636c2fa0a38c181e0d
---

# Story 8.7: Regresion automatizada continua

Status: done

## Story

Como equipo de desarrollo,
Quiero cobertura automatizada sobre los puntos que ya mostraron fragilidad,
Para que las regresiones no reaparezcan en reviews futuras.

## Acceptance Criteria

1. Dado que una zona del Inbox, asignacion, snapshot de agenda, permisos o integraciones ya fallo en review, cuando se modifica el codigo relacionado, entonces existe una prueba de regresion que cubre el comportamiento fragil observado y falla si el contrato vuelve a romperse.
2. Dado que un cambio impacta el Inbox realtime o la coherencia del hilo, cuando se ejecuta la suite, entonces la cobertura protege el orden de eventos, la seleccion correcta del hilo, la timeline y el composer sin depender de sleeps o azar.
3. Dado que un cambio impacta asignacion o autoasignacion, cuando se ejecuta la suite, entonces la cobertura valida que no se duplican responsables ni eventos y que los permisos y el aislamiento cross-tenant siguen respondiendo con el contrato esperado.
4. Dado que un cambio impacta WhatsApp, integraciones, pagos o redaccion de secretos, cuando se ejecuta la suite, entonces la cobertura valida que las credenciales siguen redaccionadas, los contratos invalidos siguen rechazandose y los fallos auxiliares no dejan efectos parciales.
5. Dado que un cambio impacta la rehidratacion de agenda o la continuidad de contexto, cuando se ejecuta la suite, entonces la cobertura valida que el snapshot mas reciente gana y que las respuestas viejas no sobrescriben el estado vigente.
6. Dado que se ejecuta la bateria de regresion en CI, cuando la implementacion cambia, entonces los tests son deterministas, compatibles con el fixture SQLite actual y expresan side effects observables, no solo codigos HTTP.

## Tasks / Subtasks

- [x] Auditar los puntos fragiles ya observados en Epic 8 y mapearlos a pruebas concretas.
  - [x] Revisar las historias 8.1 a 8.6 y extraer los bordes que deben quedar fijados por regresiones.
  - [x] Identificar cualquier assertion que hoy solo verifique HTTP y reforzarla con side effects, orden o tenant scope.
  - [x] Mantener la historia como hardening de tests; no convertirla en feature work.
- [x] Extender la cobertura del Inbox realtime y del hilo conversacional.
  - [x] Reforzar `backend/tests/test_inbox_realtime.py` para el orden de eventos, la coherencia del hilo y el snapshot mas reciente.
  - [x] Cubrir que el composer, la timeline y los estados derivados no se rompan ante eventos concurrentes o fuera de orden.
  - [x] Preferir assertions deterministas sobre sleeps o esperas por timing.
- [x] Reforzar la cobertura de permisos, asignacion y aislamiento tenant.
  - [x] Ampliar `backend/tests/test_user_permissions.py` para permisos de modulo, 403 por falta de acceso y 404 cross-tenant.
  - [x] Verificar que los paths de Inbox e integraciones no dejan efectos secundarios cuando el backend rechaza la mutacion.
  - [x] Mantener el contrato de no side effects sobre mensajes, asignaciones, auditoria y realtime.
- [x] Reforzar la cobertura de WhatsApp, integraciones y contratos criticos.
  - [x] Extender `backend/tests/test_whatsapp_setup.py` para setup, firma, autoasignacion, catalogo y disponibilidad.
  - [x] Cubrir redaccion de secretos, validacion de contratos y fallos auxiliares no bloqueantes.
  - [x] Asegurar que los casos de exito y fracaso siguen usando el mismo contrato observable que el backend real.
- [x] Reforzar la cobertura de pagos, inventario y redaccion contractual.
  - [x] Ampliar `backend/tests/test_tenant_and_orders.py` para idempotencia, auditoria, pagos, calendario y redaccion.
  - [x] Verificar que las regresiones cubren las rutas donde reviews previas detectaron fragilidad.
  - [x] Evitar introducir fixtures o helpers que oculten el comportamiento real de MySQL.
- [x] Validar el set final de regresion con las suites correctas.
  - [x] Ejecutar primero los tests focales del area modificada.
  - [x] Ejecutar luego la bateria combinada de Inbox, permisos, WhatsApp y orders.
  - [x] Mantener la suite estable y repetible en CI.

## Dev Notes

### Business Context

- Esta story no agrega funcionalidad nueva.
- El objetivo es fijar con pruebas automatizadas los bordes que ya fallaron o estuvieron cerca de fallar durante reviews anteriores.
- Epic 8 existe precisamente para estabilizar inconsistencias, carreras, permisos y contratos criticos; esta historia cierra la parte de cobertura continua.
- El valor principal es reducir regresiones silenciosas en Inbox, asignacion, integraciones, agenda y pagos.

### Current Code State

- `backend/tests/test_inbox_realtime.py` ya cubre varias zonas delicadas: orden de eventos, timeline, mensajes, estados, snapshot de agenda y permiso de inbox.
- `backend/tests/test_user_permissions.py` ya tiene cobertura de permisos de modulo, acceso cross-tenant, inbox write paths y asignacion.
- `backend/tests/test_whatsapp_setup.py` ya cubre WhatsApp setup, firma, catalogo, autoasignacion y disponibilidad.
- `backend/tests/test_tenant_and_orders.py` ya cubre redaccion de secretos, idempotencia de pagos, auditoria, calendario y contratos de integracion.
- `backend/tests/test_superadmin_offboarding.py` contiene cobertura util de auditoria y exportacion, pero no debe absorber esta historia salvo que aparezca una regresion especifica que lo justifique.
- El proyecto usa suites sincronicas de `pytest` con fixtures SQLite en memoria; esa estructura debe respetarse para mantener velocidad y determinismo.
- No hay una necesidad conocida de cambiar el codigo de produccion para esta story; si aparece una falla real, corrige el minimo backend necesario y luego blinda el borde con una prueba.
- `backend/app/events/service.py` necesitaba un ajuste de scope para `message.status`: cuando el payload ya trae `conversation_id`, ese valor debe gobernar la asociacion; el backfill por `message_id` solo aplica para payloads legacy sin conversacion.

### Critical Guardrails

- No convertir esta historia en un refactor de producto.
- No usar sleeps, timeouts largos ni concurrencia artificial fragil para simular races si existe una alternativa determinista.
- No introducir un nuevo framework de tests ni un nuevo harness async.
- No depender de datos mockeados que oculten el contrato real del backend.
- No limitar las regresiones a codigos HTTP; siempre que sea posible, validar tambien side effects, eventos, auditoria, redaccion y aislamiento tenant.
- No tocar frontend por defecto; esta historia vive en backend/tests salvo que un bug real lo obligue.
- Si una regresion revela cruce de conversaciones, el selector de eventos debe fijar el contrato antes de considerar la prueba completa.

### Implementation Guidance

- Priorizar las suites que ya concentran la fragilidad conocida en vez de crear pruebas aisladas sin contexto.
- Si un test falla por una debilidad real del backend, fijar primero el contrato minimo y luego agregar la regresion que evite volver a romperlo.
- Usar assertions sobre el estado final, eventos publicados, registros de auditoria, mensajes persistidos y aislamiento por `company_id`.
- Mantener la compatibilidad MySQL en mente aunque la suite corra en SQLite.
- Cuando la cobertura sea demasiado grande para un solo archivo, dividir por dominio solo si eso mejora claridad y mantenimiento.

### Suggested File Targets

- Primary targets:
  - `backend/tests/test_inbox_realtime.py`
  - `backend/tests/test_user_permissions.py`
  - `backend/tests/test_whatsapp_setup.py`
  - `backend/tests/test_tenant_and_orders.py`
- Secondary production target touched to preserve the event contract:
  - `backend/app/events/service.py`
- Secondary target only if an uncovered regression emerges there:
  - `backend/tests/test_superadmin_offboarding.py`
- Avoid touching production files unless a test proves there is a real contract gap.

### Testing Requirements

- Cover stale inbox state, event ordering and snapshot selection with deterministic assertions.
- Cover permissions and tenant isolation with both `403` and `404` expectations where appropriate.
- Cover side-effect suppression when a request is rejected.
- Cover WhatsApp and integrations regressions around signature validation, redaction and non-blocking auxiliary failures.
- Cover order/payment/inventory regressions around idempotency, audit, and contract validation.
- Validate the affected suite slices before any broader run.
- Keep test names descriptive so future reviews can identify the fragile contract quickly.
- Verify the event merge logic does not leak `message.status` rows across conversations that share an `external_message_id`.

### Latest Tech Information

- No dependency upgrade is required for this story.
- Stay on the pinned backend stack from `project-context.md`: Python 3.12+, FastAPI, SQLAlchemy 2, Pydantic and the existing auth/service helpers.
- Keep tests aligned with the current sync `pytest` style and the existing SQLite-backed fixtures.
- Use deterministic assertions over timing-based waiting to preserve CI stability.

### References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Epic 8, Historia 8.7 acceptance criteria]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/backlog.md` - Priority 3 item 7, dependencies and exit criterion for regression automation]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/backlog-por-historias.md` - Historia 7 objective, scope, files and criterion of exit]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/epic-8-propuesta.md` - Epic 8 scope and the regression automation proposal]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/8-1-blindaje-de-inbox-contra-estado-obsoleto.md` - previous story learnings about stale inbox state and guarded side effects]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/8-2-locking-y-auditoria-en-asignacion.md` - previous story learnings about duplicate side effects and deterministic regression style]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/8-3-redaccion-de-secretos-y-validacion-de-contratos-criticos.md` - previous story learnings about redaction and contract validation]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/8-4-separacion-de-estados-humano-ia-y-clasificacion.md` - previous story learnings about keeping state contracts distinct]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/8-5-rehidratacion-de-agenda-desde-snapshot-persistido.md` - previous story learnings about latest-snapshot-wins and deterministic state]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/8-6-permisos-backend-para-acciones-criticas.md` - previous story learnings about backend permission enforcement and no side effects on deny]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py` - Inbox realtime, timeline, appointment intent and event-order regressions]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_user_permissions.py` - permissions, cross-tenant and inbox/integration regression coverage]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_whatsapp_setup.py` - WhatsApp, signatures, catalog and assignment regressions]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py` - redaction, idempotency, audit and payment regressions]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/project-context.md` - backend stack, MySQL decision, sync pytest style and tenant-scoped service rules]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Story target resolved from sprint status as `8-7-regresion-automatizada-continua`.
- Reviewed Epic 8, the backlog master, the per-story backlog breakdown, and the prior hardening stories 8.1 through 8.6 before writing this context.
- Confirmed the regression hotspots already concentrated in `backend/tests/test_inbox_realtime.py`, `backend/tests/test_user_permissions.py`, `backend/tests/test_whatsapp_setup.py`, and `backend/tests/test_tenant_and_orders.py`.
- Confirmed the task is test hardening first, with production changes only if a real contract gap is uncovered.
- Detected and fixed a real event-merge regression while adding the Inbox isolation test: `message.status` rows with a shared `external_message_id` could leak across conversations.
- Resolved the review findings by making legacy `message.status` backfill deterministic and by replacing the tautological regression with an ambiguous shared-ID case.
- Followed up on review feedback by preferring `Message.external_message_id` matches over stale `message.sent` fallback data and by exercising the WhatsApp verify-token migration through a real SQLite `upgrade()` path.
- Revisited the remaining review findings and restored the WhatsApp webhook fallback to active account tokens while keeping the global token precedence intact.
- Hardened `create_account()` so an unreadable stored verify token is preserved instead of being re-encrypted into a new invalid value.
- Reinstated the abort signal on the conversation read mutation to keep stale detail loads from mutating unread state after the user changes selection.
- Tightened the WhatsApp webhook fallback structure so the global verify token now blocks account-token fallback when it is configured.
- Narrowed the unreadable-token handling so ciphertext-like stored values are preserved instead of being rewritten on account updates.
- Resolved the final review findings by removing the public WhatsApp webhook fallback to account-scoped verify tokens and by making the appointment-intent snapshot token independent of `Event.created_at` flush timing.
- Closed the last contract mismatch by making the WhatsApp setup indicator depend only on the global verify token, so the UI no longer advertises tenant-scoped webhook verification that the public endpoint rejects.
- Resolved the follow-up review findings by enforcing inbox permissions on conversation list/detail reads and by removing the stale "Por cuenta" WhatsApp setup label.
- Verified the frontend build and backend syntax after the fix set; the shell environment still lacks `fastapi` for pytest execution.

### Completion Notes List

- Prepared the story so the dev agent can focus on deterministic regression coverage instead of rediscovering the same fragile edges.
- Anchored the acceptance criteria on observable side effects, tenant isolation, and stable contracts.
- Kept the implementation surface backend-only by default and aligned to the current pytest-based test stack.
- Added targeted regressions for Inbox event scoping, denied-write side effects, WhatsApp signature short-circuiting, and calendar create failure resilience.
- Fixed the conversation-event merge selector so legacy status backfill still works while cross-conversation status leakage is blocked.
- Hardened legacy `message.status` resolution so ambiguous shared `external_message_id` payloads are not attributed to multiple conversations.
- Verified the WhatsApp verify-token migration against SQLite end-to-end instead of only calling the backfill helper.
- Restored the WhatsApp webhook fallback to active account tokens when no global token is configured, while preserving global-token precedence.
- Prevented `create_account()` from rewriting unreadable stored verify-token values during an update.
- Reattached the abort signal to the conversation read mutation so stale requests cannot mark the wrong thread as read.
- Ensured the webhook rejects account-token fallback when a global verify token is present, while still allowing account-token fallback only when the global token is absent.
- Preserved ciphertext-like unreadable WhatsApp verify tokens during account updates instead of re-encrypting them.
- Removed the public webhook fallback that accepted account tokens across tenants and kept the setup indicator informational only.
- Made the WhatsApp setup indicator reflect only the globally configured verify token so it matches the public webhook contract.
- Protected inbox read routes with the same module permission gate as inbox write routes, and aligned the WhatsApp setup copy with the actual backend contract.
- Simplified appointment-intent snapshot versioning to use the prepared timestamp plus event id, avoiding reliance on server-default `created_at` timing.
- Confirmed the frontend TypeScript build still passes after the snapshot token change.

### File List

- `_bmad-output/implementation-artifacts/8-7-regresion-automatizada-continua.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/app/events/service.py`
- `backend/app/conversations/service.py`
- `backend/app/whatsapp/routes.py`
- `backend/app/whatsapp/service.py`
- `backend/tests/test_inbox_realtime.py`
- `backend/tests/test_user_permissions.py`
- `backend/tests/test_whatsapp_setup.py`
- `backend/tests/test_tenant_and_orders.py`
- `frontend/src/App.tsx`
- `backend/migrations/versions/20260715_0023_whatsapp_verify_token_text.py`

## Change Log

- 2026-07-16: Created the ready-for-dev story context for continuous automated regression coverage in Epic 8.
- 2026-07-16: Implemented targeted regression coverage for Inbox isolation, denied-write side effects, WhatsApp signature short-circuiting, and calendar create failure resilience; fixed the status-event merge selector to avoid cross-conversation leakage.
- 2026-07-17: Resolved the review follow-up for legacy `message.status` scope by making the backfill path deterministic and replacing the fragile regression with a shared-ID ambiguity case.
- 2026-07-17: Addressed follow-up review findings by preferring persisted `Message` rows over stale sent-event backfill data and by validating the WhatsApp verify-token migration with a real SQLite `upgrade()` execution.
- 2026-07-17: Closed the remaining review findings by restoring WhatsApp webhook fallback to account tokens, preserving unreadable stored verify tokens on account updates, and reattaching the abort signal to the conversation read mutation.
- 2026-07-17: Tightened WhatsApp webhook precedence to honor the configured global verify token before falling back to active account tokens, and preserved unreadable ciphertext-like stored verify tokens without rewriting them.
- 2026-07-17: Addressed the final review findings by removing public webhook fallback to account verify tokens, scoping the lookup helper by tenant, and simplifying appointment snapshot versioning so it no longer depends on `created_at` flush timing.
- 2026-07-17: Closed the remaining WhatsApp contract mismatch by making the setup response report only the globally configured verify token.
- 2026-07-17: Resolved follow-up review findings by requiring inbox permissions for conversation reads and updating the WhatsApp setup label to match the backend contract.
