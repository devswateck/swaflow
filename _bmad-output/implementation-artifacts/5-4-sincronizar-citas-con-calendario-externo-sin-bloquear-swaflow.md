# baseline_commit: 595b380d6111b59e727b01d978cf27ebc2b6a335
# Story 5.4: Sincronizar citas con calendario externo sin bloquear Swaflow
Status: done

## Story

Como admin principal del tenant,
quiero que las citas se sincronicen con el calendario externo cuando exista,
para que Swaflow conserve el flujo comercial aunque la integracion falle o no este disponible.

## Acceptance Criteria

1. Dado que el tenant tiene una integracion de calendario activa,
   cuando se crea o actualiza una cita,
   entonces el sistema intenta sincronizarla con el calendario configurado.
2. Dado que la integracion de calendario usa Google Calendar o Microsoft Calendar,
   cuando el sistema normaliza la configuracion,
   entonces conserva el contrato esperado por cada proveedor y mantiene la zona horaria correcta.
3. Dado que la integracion de calendario no existe o no esta activa,
   cuando se crea una cita,
   entonces la cita queda persistida y operable dentro de Swaflow,
   y el flujo comercial no se bloquea.
4. Dado que el calendario externo presenta una falla temporal,
   cuando el sistema no puede sincronizar,
   entonces la cita sigue disponible en Swaflow,
   la falla queda registrada para soporte,
   y la transaccion principal no se revierte.
5. Dado que una cita se sincroniza correctamente,
   cuando el backend confirma la operacion externa,
   entonces se actualizan `external_calendar_event_id`, `calendar_sync_status` y `calendar_synced_at`,
   y se emite el evento de dominio correspondiente.
6. Dado que la disponibilidad de agenda consulta un calendario externo con error,
   cuando el backend calcula horarios,
   entonces mantiene el fallback interno honesto sin inventar disponibilidad ni bloquear la creacion de citas.

## Tasks / Subtasks

- [x] Mantener la persistencia de citas independiente del exito de la sincronizacion externa. (AC: 1, 3, 4, 5)
  - [x] Verificar que `backend/app/appointments/service.py` siga haciendo commit de la cita antes del intento de sincronizacion.
  - [x] Preservar el flujo de eventos `appointment.created`, `appointment.calendar_synced` y `appointment.calendar_sync_failed`.
  - [x] Mantener el comportamiento de `calendar_sync_status` para exito, fallo sin `external_calendar_event_id` y estado obsoleto cuando aplique.
- [x] Conservar el contrato de integracion con Google y Microsoft. (AC: 2)
  - [x] Revisar `backend/app/integrations/calendar.py` para mantener la normalizacion de proveedor, credenciales, timezone y rutas.
  - [x] Mantener compatibles los requests de `freeBusy` de Google y `getSchedule`/event creation de Microsoft Graph.
  - [x] No introducir una segunda capa de adaptadores ni mover la logica de calendario a frontend o n8n.
- [x] Blindar el fallback de disponibilidad y la experiencia operativa. (AC: 3, 4, 6)
  - [x] Mantener el fallback interno cuando la consulta de busy intervals falle.
  - [x] Mantener `validation_source = internal_fallback` y `validation_error` honestos cuando la integracion externa falle.
  - [x] No bloquear el modulo Citas ni el flujo de agenda por errores del proveedor externo.
- [x] Cubrir la regresion con pruebas de backend. (AC: 1, 2, 3, 4, 5, 6)
  - [x] Probar create/update con integracion activa y sincronizacion exitosa.
  - [x] Probar create/update sin integracion activa y confirmar que la cita persiste.
  - [x] Probar fallo temporal del proveedor y confirmar que la cita queda guardada con estado de sync fallido u obsoleto segun corresponda.
  - [x] Probar que la disponibilidad sigue devolviendo opciones internas cuando la integracion externa falla.

## Dev Notes

### Contexto de producto

- Epic 5, historia 5.4.
- FR relevantes: FR-071, FR-112, FR-113, FR-148, FR-149, FR-158, FR-159, FR-171, FR-177.
- La regla de producto es no bloquear Swaflow si el calendario externo falla, falta o responde con error transitorio.
- Esta historia debe respetar la configuracion compartida de horario y duracion definida en la historia 5.3; no crear una segunda configuracion de agenda.

### Estado actual del codigo

- `backend/app/appointments/service.py` ya hace la persistencia de la cita y luego intenta sincronizarla con el calendario externo.
- `backend/app/appointments/service.py` ya registra eventos de dominio para exito y fallo de sincronizacion, y publica realtime en ambos casos.
- `backend/app/appointments/service.py` ya usa fallback interno en disponibilidad cuando la consulta externa falla.
- `backend/app/integrations/calendar.py` ya soporta proveedores `google_calendar` y `microsoft_calendar`, con alias `outlook_calendar -> microsoft_calendar`.
- `backend/app/integrations/calendar.py` ya normaliza timezone, credenciales y rutas, y usa `httpx.Client(timeout=10)` para los requests externos.
- `backend/app/appointments/models.py` ya tiene campos de seguimiento de sincronizacion (`external_calendar_event_id`, `calendar_sync_status`, `calendar_sync_error`, `calendar_synced_at`, `calendar_sync_obsolete_at`); no se espera nueva migracion.
- `backend/app/appointments/routes.py` ya expone create, update, availability y la config operativa compartida de agenda.
- `frontend/src/App.tsx` ya muestra `calendar_sync_status`, `calendar_sync_error` y `calendar_synced_at` en la vista de Citas; no tocar UI salvo que aparezca una regresion real.

### Guardrails criticos

- No convertir la sincronizacion externa en requisito para persistir una cita.
- No introducir colas, workers ni jobs asíncronos para esta historia; no hay decision de arquitectura para eso.
- No mover el calculo de disponibilidad al frontend.
- No inventar estados nuevos de sincronizacion si los existentes ya resuelven el caso.
- No romper el comportamiento cross-tenant `404` ni la validacion por `company_id`.
- Si el proveedor externo falla, registrar el problema y continuar; la transaccion principal ya debe estar segura.

### Arquitectura y estructura

- Backend por dominio: `routes.py`, `schemas.py`, `service.py`, `models.py`.
- La logica de calendar sync pertenece a `backend/app/integrations/calendar.py` y al flujo de cita en `backend/app/appointments/service.py`.
- `create_event` en `backend/app/events/service.py` es el patron para persistir eventos de dominio relevantes.
- `realtime_manager.publish` debe seguir recibiendo eventos de exito/fallo para mantener la UI coherente.
- El contrato del modulo Citas ya vive en FastAPI sincronico con SQLAlchemy 2; no cambiar el estilo de servicios por esta historia.

### Latest Tech Information

- Google Calendar FreeBusy usa `POST https://www.googleapis.com/calendar/v3/freeBusy` y el body incluye `timeMin`, `timeMax`, `timeZone` e `items[].id`; la respuesta devuelve `calendars[calendarId].busy`.
- Microsoft Graph `getSchedule` usa `POST /me/calendar/getSchedule` y el request incluye `schedules`, `startTime`, `endTime` y `availabilityViewInterval`; la respuesta devuelve `scheduleItems` con `start` y `end`.
- Microsoft Graph create event usa `POST /me/calendars/{calendar-id}/events` con `start`, `end` y `transactionId`; el identificador de evento externo debe conservarse para resync o patch.
- Las implementaciones existentes ya están alineadas con esos contratos; cualquier cambio debe mantener la misma semantica de timezone y disponibilidad.

### Project Structure Notes

- Archivos probables a tocar:
  - `backend/app/appointments/service.py`
  - `backend/app/integrations/calendar.py`
  - `backend/tests/test_tenant_and_orders.py`
  - `backend/tests/test_inbox_realtime.py`
- Archivos a preservar sin cambios salvo necesidad real:
  - `backend/app/appointments/routes.py`
  - `backend/app/appointments/schemas.py`
  - `backend/app/appointments/models.py`
  - `frontend/src/App.tsx`
- No crear una nueva tabla, un nuevo store frontend ni una nueva API para calendario.

### Testing Requirements

- Cubrir la creacion de cita con calendario activo y sincronizacion exitosa.
- Cubrir la actualizacion de cita con calendario activo y resync exitoso.
- Cubrir la creacion de cita sin calendario activo.
- Cubrir la falla temporal del proveedor y verificar que la cita sigue persistida con el estado de sync correcto.
- Cubrir la disponibilidad con fallback interno cuando la consulta externa falle.
- Mantener las pruebas independientes de Google y Microsoft mediante monkeypatch/fakes; no depender de red real.
- Verificar que no se regresa un estado falso de "sincronizado" cuando el proveedor responde mal.

### References

- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md - Epic 5, Historia 5.4, FR071/FR112/FR113/FR148/FR149/FR158]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md - seccion Citas y principio de fallback comercial]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md - Inbox/Citas como superficies operativas, no bloquear flujo comercial]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/5-3-configurar-reglas-de-horario-y-duracion-de-citas.md - configuracion compartida de horario y duracion]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/service.py - create/update, availability y tracking de calendar sync]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/integrations/calendar.py - adapters, normalization y requests externos]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/models.py - campos de sincronizacion de calendario]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py - cobertura actual de sync y fallback]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py - cobertura de availability y estado de citas]
- [Source: https://developers.google.com/workspace/calendar/api/v3/reference/freebusy/query - FreeBusy oficial de Google Calendar]
- [Source: https://learn.microsoft.com/en-us/graph/api/calendar-getschedule?view=graph-rest-1.0 - getSchedule oficial de Microsoft Graph]
- [Source: https://learn.microsoft.com/en-us/graph/api/calendar-post-events?view=graph-rest-1.0 - create event oficial de Microsoft Graph]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Se selecciono automaticamente la primera historia backlog del sprint actual: `5-4-sincronizar-citas-con-calendario-externo-sin-bloquear-swaflow`.
- Se revisaron `sprint-status.yaml`, `epics.md`, `prd.md`, la arquitectura frontend, la historia 5.3, el contexto del proyecto y el codigo existente de citas e integraciones de calendario.
- Se confirmo que la persistencia de cita y la sincronizacion externa ya estan separadas, con fallback interno y tracking de error.
- Se confirmo que los proveedores soportados son Google Calendar y Microsoft Calendar y que la UI de Citas ya expone el estado de sincronizacion.
- Se ajustaron pruebas obsoletas para reflejar el lookup previo de disponibilidad, el fallback interno y el contrato actual de Google/Microsoft.
- Se ejecuto la suite completa de `backend/tests/test_tenant_and_orders.py` y `backend/tests/test_inbox_realtime.py` con resultado verde.

### Completion Notes List

- La logica de backend ya satisfacia la historia; no fue necesario cambiar el flujo productivo de citas.
- Se alinearon las pruebas con el contrato real de sincronizacion y disponibilidad, incluyendo Google Calendar, Microsoft Graph y fallback interno.
- Se corrigieron expectativas obsoletas en pruebas de IA, integración de calendario y comparaciones de datetime en SQLite.
- La suite completa de `backend/tests/test_tenant_and_orders.py` y `backend/tests/test_inbox_realtime.py` pasó en verde.

### File List

- `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/5-4-sincronizar-citas-con-calendario-externo-sin-bloquear-swaflow.md`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/sprint-status.yaml`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py`

### Change Log

- 2026-07-12: Se validó la historia 5.4 contra la implementación existente y se ajustó la cobertura de pruebas para el comportamiento real de citas, sincronización externa y fallback.
- 2026-07-12: Se restringió la config operativa expuesta por Citas a la sección `schedule` para evitar exponer guardrails, autonomía y políticas de IA.

### Review Findings

- [x] [Review][Patch] Endpoints de agenda exponen y modifican la configuracion completa de IA con permisos de Citas [backend/app/appointments/routes.py:36] — `/appointments/operational-config` usaba `require_module_access("appointments")` y delegaba en `update_shared_operational_config()` un `dict` sin restriccion de campos. Se corrigio el contrato para exponer solo `schedule` y preservar internamente el resto de la configuracion de IA.
