---
baseline_commit: 34029c557dd621508aec915ae1b0fea012ce5436
---

# Story 1.9: Configurar calendario del tenant

Status: done

## Story

Como admin principal del tenant,
Quiero configurar una integracion de calendario por tenant y sincronizar citas cuando exista,
para que Swaflow mantenga la agenda interna aunque el calendario externo no exista o falle.

## Acceptance Criteria

1. Dado que el tenant quiere sincronizar citas, cuando el admin configura una integracion de calendario, entonces el sistema soporta Google Calendar y Microsoft Calendar como opciones V1, cifra las credenciales, guarda la configuracion por `company_id` y responde `404` para otro tenant o `403` si el usuario no tiene acceso al modulo.
2. Dado que una cita se crea o actualiza, cuando existe una integracion de calendario activa y valida, entonces el backend intenta sincronizar la cita con el calendario configurado, persiste el identificador externo en `external_calendar_event_id` cuando exista y no rompe el flujo interno de Swaflow si el proveedor falla.
3. Dado que el tenant no tiene calendario integrado o la integracion esta parcial o temporalmente indisponible, cuando se crean o consultan citas, entonces Swaflow conserva la cita interna, usa la disponibilidad local y el horario operativo definido en otras historias, y no bloquea la operacion comercial.
4. Dado que el usuario abre la superficie de integraciones, cuando revisa la tarjeta de calendario, entonces ve una configuracion honesta y reutilizada desde la pantalla existente de Integraciones, sin crear una segunda UI ni duplicar la configuracion operativa de horarios de IA/Citas.

**FR cubiertos:** FR112, FR113, FR148, FR149, FR150, FR151, FR152, FR158

## Tasks / Subtasks

- [x] Extender el contrato de integraciones para calendario usando la superficie existente de `CompanyIntegration`.
  - [x] Validar `type == "calendar"` en backend sin crear un modulo nuevo separado de integraciones.
  - [x] Definir y validar la carga minima de calendario antes de permitir activacion: proveedor, `calendar_id`, zona horaria y credenciales cifradas.
  - [x] Mantener el cifrado y redaccion de secretos en respuestas, logs y auditoria.
  - [x] Mantener `404` para accesos cross-tenant y `403` para usuarios sin permiso del modulo.
- [x] Conectar el flujo de citas al contrato de calendario canonico.
  - [x] Reusar `appointments` como fuente de verdad de la cita interna.
  - [x] Intentar sincronizar en create/update solo cuando exista integracion activa y valida.
  - [x] Guardar `external_calendar_event_id` cuando el proveedor devuelva un identificador util.
  - [x] Si la sincronizacion falla, conservar la cita interna y registrar el fallo para soporte/operacion.
- [x] Reusar la pantalla existente de Integraciones en el frontend.
  - [x] Mantener la tarjeta de calendario en `frontend/src/App.tsx` y alinear los labels V1 con Google Calendar y Microsoft Calendar.
  - [x] No crear una nueva pantalla de calendario ni mover el flujo fuera de Integraciones.
  - [x] Mantener el copy honesto: sin calendario externo la cita sigue operable dentro de Swaflow.
- [x] Agregar cobertura de regresion para configuracion y sincronizacion.
  - [x] Probar CRUD tenant-scoped de calendario y bloqueo `404` cross-tenant.
  - [x] Probar rechazo de configuracion incompleta o invalida cuando la integracion se activa.
  - [x] Probar create/update de citas con y sin calendario, incluyendo el caso de sincronizacion fallida.
  - [x] Probar que la UI compila y queda alineada con el contrato actualizado.

## Dev Notes

### Business Context

- Esta story cubre la integracion V1 de calendario del tenant, no la logica de disponibilidad de agenda. La validacion de horario operativo, franjas manana/tarde y propuesta de slots pertenece a las historias de Citas y a la IA.
- El calendario externo es best-effort: Swaflow debe seguir registrando y mostrando citas internas aunque el proveedor no exista, no responda o falle temporalmente.
- La arquitectura aprobada exige adaptadores por proveedor y contrato canonico en backend, con el backend como fuente de verdad.

### Current Code State

- `backend/app/integrations/service.py` ya centraliza `CompanyIntegration` y hoy solo aplica validacion especial para `payments`.
- `backend/app/integrations/schemas.py` expone `IntegrationCreate`, `IntegrationUpdate` e `IntegrationRead` genericos; no existe un esquema separado para calendario.
- `backend/app/integrations/routes.py` ya protege `/integrations` con `require_module_access("integrations")`.
- `backend/app/appointments/models.py` ya tiene `external_calendar_event_id`, asi que no hace falta una segunda tabla para rastrear el ID externo.
- `backend/app/appointments/service.py` hoy crea, actualiza y cancela citas internas sin integracion de calendario; el cambio debe preservar ese flujo.
- `frontend/src/App.tsx` ya tiene una tarjeta de calendario dentro de la pagina de Integraciones, con campos de proveedor, calendar_id, timezone, duracion y recordatorio. Reusar esa superficie y alinear copy y labels.

### Critical Guardrails

- No crear un modulo nuevo de negocio para calendario si `integrations` y `appointments` ya cubren la frontera correcta.
- No convertir el calendario externo en fuente de verdad; la cita interna en Swaflow sigue siendo la verdad.
- No romper la creacion, edicion, listado o cancelacion de citas si la integracion no existe o el proveedor falla.
- No duplicar configuracion de horario operativo aqui. El horario de IA/Citas vive en otras historias.
- No cambiar el default canonico de duracion de citas en esta story. Si hace falta ajustar la duracion por defecto, eso pertenece a la story de reglas de horario de Citas.
- No inventar credenciales en texto plano. Cualquier token o secreto debe ir cifrado y redacted.

### Implementation Guidance

- Reusar `CompanyIntegration.config` para guardar la configuracion de calendario y su metadata de proveedor.
- Si se necesita un helper o adaptador, mantenerlo dentro de `backend/app/integrations/` o `backend/app/appointments/`, no como un subsistema paralelo.
- El contrato de V1 debe contemplar Google Calendar y Microsoft Calendar. La opcion actual `outlook_calendar` en la UI debe mapearse a Microsoft Calendar si se conserva el valor interno.
- La sincronizacion debe ser tolerante a fallos: si el proveedor no responde, la cita interna no puede perderse ni quedar bloqueada.
- Si el sync requiere persistir mas metadata, preferir `config` de integration, `external_calendar_event_id` en appointment y eventos/auditoria ya existentes antes de agregar nuevas tablas.

### Suggested File Targets

- Backend likely to change:
  - `backend/app/integrations/models.py`
  - `backend/app/integrations/schemas.py`
  - `backend/app/integrations/service.py`
  - `backend/app/appointments/service.py`
  - `backend/app/appointments/schemas.py` only if the payload needs an explicit calendar sync field
  - `backend/app/appointments/models.py` only if a new persistence field is absolutely required
  - `backend/tests/test_tenant_and_orders.py` or a focused new test file for appointment/calendar regressions
- Frontend likely to change:
  - `frontend/src/App.tsx`

### Testing Requirements

- Cover tenant-scoped CRUD for calendar integrations and `404` for another tenant.
- Cover invalid or incomplete active calendar configs with `422`.
- Cover appointment create/update with active calendar integration and verify that the internal appointment still persists if sync fails.
- Cover that successful sync stores the external event ID when available.
- Cover that the current integrations UI still builds cleanly after any label or config changes.
- Maintain compatibility with the current SQLite-backed test setup while keeping MySQL-safe schema assumptions.

### Project Structure Notes

- Keep the integration contract in the existing domain boundary. Do not introduce a separate `calendar` product module unless the implementation truly needs a new bounded context.
- Preserve `appointments` as the canonical source of truth for internal scheduling data.
- Preserve `integrations` as the canonical place for tenant connection metadata and credentials.
- The frontend should continue using the existing `IntegrationsPage` and typed `api<T>()` helper instead of a one-off calendar settings view.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Story 1.9, FR112, FR113, FR148-FR152, FR158, FR161-FR166]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - integraciones V1, citas y calendar narratives]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - `CalendarAdapter`, backend canonical flow, resilience rules]
- [Source: `docs/adr/0004-integrations-events-audit-and-outbox.md` - adapters, tenant scoping, encrypted secrets, backend source of truth]
- [Source: `backend/app/integrations/service.py` - current integration contract and tenant-scoped CRUD]
- [Source: `backend/app/integrations/routes.py` - module permission gate for integrations]
- [Source: `backend/app/integrations/schemas.py` - generic integration payloads]
- [Source: `backend/app/appointments/models.py` - existing `external_calendar_event_id`]
- [Source: `backend/app/appointments/service.py` - current appointment lifecycle]
- [Source: `frontend/src/App.tsx` - existing integrations page and calendar card]
- [Source: `_bmad-output/implementation-artifacts/1-8-configurar-pasarela-de-pagos-y-contrato-de-integracion.md` - previous integration-story patterns and test expectations]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Story selected automatically as the first backlog item in `sprint-status.yaml`: `1-9-configurar-calendario-del-tenant`.
- Reviewed epic, PRD, architecture, previous story 1.8, appointments module, integrations module, and the current frontend integrations page before writing the story.
- Confirmed the repo already has `appointments` and `integrations` boundaries, so the story focuses on extending them instead of creating a new scheduling subsystem.
- Implemented a reusable HTTP calendar adapter in `backend/app/integrations/calendar.py` with provider defaults, configurable base URL and endpoint paths, and response ID extraction.
- Added calendar sync state tracking in `backend/app/appointments/models.py`, `backend/app/appointments/schemas.py`, and `backend/app/appointments/service.py` so failed resincronizations are marked `obsolete` instead of silently reusing stale evidence.
- Updated the frontend calendar provider labels to the V1 set (`Google Calendar`, `Microsoft Calendar`) and exposed the HTTP endpoint fields in `frontend/src/App.tsx`.
- Verified the relevant backend regression slice plus frontend `lint` and `build` successfully.

### Completion Notes List

- Implemented calendar integration validation and normalization for `CompanyIntegration` with tenant-scoped `404` handling and `422` config guards.
- Replaced the local sync stub with a real HTTP adapter that supports provider defaults and configurable calendar endpoints for Google Calendar and Microsoft Calendar.
- Added best-effort appointment calendar sync on create and update, persisting `external_calendar_event_id` on success and marking failed resincronizations as `obsolete` while keeping the prior external ID as evidence.
- Reused the existing Integrations page in the frontend and aligned the calendar provider options and config fields to the HTTP contract.
- Added regression coverage for provider validation, tenant scoping, successful sync, HTTP request wiring, and obsolete-state failure handling.
- Resolved the review finding by removing `external_calendar_event_id` from the writable appointment update payload so clients cannot tamper with provider-owned event IDs.
- Validation executed: `python3 -m py_compile backend/app/integrations/calendar.py backend/app/integrations/service.py backend/app/appointments/service.py backend/tests/test_tenant_and_orders.py`, `./backend/.venv/bin/pytest backend/tests/test_tenant_and_orders.py -q` (`76 passed`), `npm run lint`, `npm run build`.

### File List

- `backend/app/integrations/calendar.py`
- `backend/app/integrations/service.py`
- `backend/app/appointments/models.py`
- `backend/app/appointments/service.py`
- `backend/app/appointments/schemas.py`
- `backend/migrations/versions/20260629_0017_appointment_calendar_sync_tracking.py`
- `backend/tests/test_tenant_and_orders.py`
- `frontend/src/App.tsx`
- `_bmad-output/implementation-artifacts/1-9-configurar-calendario-del-tenant.md`

## Change Log

- 2026-06-28: Implemented the V1 calendar integration contract, best-effort appointment sync, frontend provider alignment, and regression tests.
- 2026-06-29: Upgraded calendar sync to a configurable HTTP adapter and added obsolete-state tracking for failed resincronizations.
- 2026-06-29: Removed writable appointment access to `external_calendar_event_id` to protect provider-owned sync state.
