# Story 5.5: Filtrar y reflejar citas en el dashboard y el hilo de conversacion

baseline_commit: 595b380d6111b59e727b01d978cf27ebc2b6a335
Status: done

## Story

Como usuario autorizado del tenant,
quiero encontrar y seguir citas por estado, origen y responsable,
para que pueda entender el impacto comercial de la agenda en la operacion diaria.

## Acceptance Criteria

1. Dado que el usuario abre el modulo Citas,
   cuando aplica filtros por rango de fechas de `scheduled_at`, estado, usuario/asesor, cliente/contacto y origen,
   entonces el sistema devuelve solo las citas del tenant y mantiene la integridad de los datos entre vistas.
2. Dado que una cita se crea, actualiza o cancela,
   cuando el backend publica un evento `appointment.*` y la aplicacion lo recibe,
   entonces el Dashboard refresca su conteo de citas y la conversacion relacionada muestra el evento en su historial o contexto.
3. Dado que la IA no tiene datos suficientes para confirmar agenda,
   cuando debe responder al cliente,
   entonces pide aclaracion o deriva a humano segun las reglas del agente,
   y nunca confirma disponibilidad inventada.
4. Dado que el usuario limpia los filtros,
   cuando vuelve a la vista general de Citas,
   entonces el listado vuelve al estado base del tenant sin perder la capacidad de reabrir el contexto de agenda preparado.

## Tasks / Subtasks

- [x] Definir el contrato de filtros de Citas sin romper el listado actual. (AC: 1, 4)
  - [x] Revisar `GET /appointments` y decidir si los filtros se resuelven en backend o en la capa de pagina; en V1 no duplicar la logica en dos sitios.
  - [x] Mantener `limit`, `offset` y `focus_appointment_id` como parte del contrato existente.
  - [x] Si se expone filtro de origen, derivarlo de `conversation_id` (`inbox` si existe, `manual` si no) en lugar de agregar una nueva columna persistida.
- [x] Actualizar la superficie de Citas para filtrar y leer la lista con claridad. (AC: 1, 4)
  - [x] Agregar estado de filtros en `AppointmentsPage` con patrón similar al de `OrdersPage`.
  - [x] Conectar los filtros al cargado de citas y conservar el formulario de alta manual/inbox.
  - [x] Mostrar labels claros para estado, responsable y origen sin inventar metadatos no disponibles.
- [x] Preservar la reflexion operativa en Dashboard e Inbox. (AC: 2)
  - [x] Mantener intacto el refresh por websocket sobre eventos `appointment.*`.
  - [x] No tocar el flujo que llena `conversation.events` desde `list_conversation_events`.
  - [x] Verificar que el Dashboard siga leyendo el conteo de citas desde la fuente actual sin dejar de actualizarse cuando cambien las citas.
- [x] Cubrir la regresion con pruebas. (AC: 1, 2, 3, 4)
  - [x] Agregar o extender pruebas de backend para filtros por fecha, estado, responsable, contacto y origen.
  - [x] Verificar que `focus_appointment_id` siga funcionando cuando el listado esta filtrado.
  - [x] Verificar que crear/actualizar/cancelar una cita siga emitiendo eventos visibles en la conversacion y que el refresh realtime siga siendo coherente.

## Dev Notes

### Contexto de producto

- Epic 5, historia 5.5.
- FR relevantes: FR-070, FR-073, FR-074, FR-118, FR-159, FR-165, FR-166, FR-178, FR-179, FR-180.
- La historia es principalmente de visibilidad operativa. No debe romper la experiencia ya existente de agenda, disponibilidad o creacion de citas.

### Estado actual del codigo

- `frontend/src/App.tsx` ya carga citas con `loadAppointments()` usando `GET /appointments?limit=200&offset=0` y `focus_appointment_id`, pero no expone filtros operativos en `AppointmentsPage`.
- `frontend/src/App.tsx` ya muestra `appointments.length` en `DashboardPage`; el KPI de citas existe, pero no hay un panel dedicado de filtros ni una nueva fuente de verdad para el conteo.
- `frontend/src/App.tsx` ya refresca citas en tiempo real cuando llegan eventos `appointment.*` por websocket.
- `frontend/src/App.tsx` ya carga `conversation.events` desde `loadConversationDetail()` y el UI del Inbox ya renderiza esos eventos.
- `backend/app/events/service.py` ya considera `appointment.created`, `appointment.calendar_synced`, `appointment.calendar_sync_failed` y `appointment.cancelled` como eventos visibles en conversaciones.
- `backend/app/appointments/routes.py` hoy solo expone `limit`, `offset` y `focus_appointment_id` para el listado de citas.
- `backend/app/appointments/service.py` lista citas ordenadas por `scheduled_at` ascendente y mantiene aislamiento por `company_id`.
- `backend/app/appointments/models.py` no tiene un campo de origen persistido; el origen de V1 debe inferirse si hace falta.

### Guardrails criticos

- No introducir un router nuevo ni una segunda capa de estado global.
- Mantener `api<T>()`, `Zustand`, `swaflow_theme` y `swaflow_active_page`.
- No crear una columna nueva de `source` para citas si el origen puede derivarse de `conversation_id`.
- Mantener `company_id` en toda consulta o mutacion. El acceso cross-tenant sigue siendo `404`, no `403`.
- No romper el flujo de disponibilidad y creacion de citas ya validado en la historia 5.4.
- No inventar citas, origen, responsables o estados que el backend no provea.

### Arquitectura y estructura

- La pagina de Citas vive en `frontend/src/App.tsx`; no hace falta extraer componentes nuevos salvo que realmente reduzcan complejidad.
- Si el contrato de filtros se resuelve en backend, ampliar `backend/app/appointments/routes.py` y `backend/app/appointments/service.py`; no crear un endpoint paralelo.
- Si el contrato de filtros se resuelve en frontend, centralizar la logica en `AppointmentsPage` y evitar duplicar filtros en otras superficies.
- Reusar el patron de filtros de `OrdersPage` como referencia visual y de comportamiento.
- Preservar el path realtime que refresca citas e Inbox cuando llegan eventos de agenda.

### File Structure Notes

- Archivos probablemente a tocar:
  - `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx`
  - `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/routes.py`
  - `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/service.py`
  - `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py`
- Archivos a preservar salvo necesidad real:
  - `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/events/service.py`
  - `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/conversations/service.py`
  - `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/models.py`
- No mover el Dashboard o el Inbox a otra arquitectura; solo mantener su reflejo operativo coherente.

### Testing Requirements

- Probar filtros por:
  - rango de fechas de `scheduled_at`
  - estado
  - responsable
  - cliente/contacto
  - origen derivado de `conversation_id`
- Probar que `focus_appointment_id` sigue funcionando aunque el listado tenga filtros activos.
- Probar que crear, actualizar y cancelar una cita sigue reflejando eventos en la conversacion relacionada.
- Probar que el refresh realtime de `appointment.*` no se pierde al introducir filtros.
- Si se agrega contrato backend, las pruebas deben permanecer tenant-scoped y cubrir `404` o lista vacia para recursos fuera del tenant.

### Previous Story Intelligence

- La historia 5.4 ya separo correctamente persistencia de cita y sincronizacion de calendario.
- No mezclar este trabajo con logica de sincronizacion externa ni con el fallback de disponibilidad.
- La UI ya expone estados de `calendar_sync_status`, `calendar_sync_error` y `calendar_synced_at`; esta historia no debe romper esa lectura.
- El caso de agenda desde Inbox ya deja preparado contexto de cita; esa preparacion debe seguir funcionando aunque se agreguen filtros en la vista de Citas.

### Latest Tech Information

- No hay cambio de dependencia ni version para esta historia; usar el stack vigente del proyecto definido en `project-context.md`.
- Mantener la implementacion dentro del patron actual de React/Vite/TypeScript/Tailwind y del backend FastAPI/SQLAlchemy 2 ya establecido.

### References

- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md#Historia-5.5-Filtrar-y-reflejar-citas-en-el-dashboard-y-el-hilo-de-conversacion]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md#Requisitos-funcionales]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md#Estructura-del-Inbox]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx:2517-2532]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx:2692-2790]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx:3479-3499]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx:4838-5577]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/routes.py:59-72]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/service.py:347-375]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/events/service.py:1-24]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/conversations/service.py:407-437]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py:1432-1640]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py:3467-3733]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Instale dependencias del backend en `/private/tmp/swaflow-venv` con `pip install -e 'backend[dev]'` para poder ejecutar pruebas reales del servicio de citas.
- Ejecute `pytest backend/tests/test_inbox_realtime.py -q` y la suite paso completa.
- Ejecute `npm run build` en `frontend/` y la compilacion paso completa.

### Completion Notes List

- Se agregaron filtros de listado de citas por rango de fechas, estado, contacto, responsable y origen derivado de `conversation_id`.
- Se mantuvo `focus_appointment_id` aun cuando el listado esta filtrado.
- La pagina de Citas ahora separa la vista global del dashboard del listado filtrado de la pantalla, y refresca ambas segun corresponda.
- El refresh realtime por eventos `appointment.*` sigue activo y el Inbox conserva la reflexion de eventos de conversacion.
- Se agregaron pruebas de backend para filtrado y foco en listado filtrado.
- Se resolvio el hallazgo de revision: `appointment.updated` ahora se publica y queda visible en el hilo de conversacion.

### File List

- `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/routes.py`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/service.py`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/events/service.py`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/5-5-filtrar-y-reflejar-citas-en-el-dashboard-y-el-hilo-de-conversacion.md`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/sprint-status.yaml`

## Change Log

- 2026-07-12: Implementacion completada para filtros de citas, origen derivado, refresh de dashboard/inbox y cobertura de pruebas.
- 2026-07-12: Addressed code review finding - appointment.updated ahora se publica y se refleja en la conversacion.
