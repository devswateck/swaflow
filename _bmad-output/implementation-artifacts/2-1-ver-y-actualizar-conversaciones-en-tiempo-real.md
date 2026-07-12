---
baseline_commit: 16c7aad
---

# Story 2.1: Ver y actualizar conversaciones en tiempo real

Status: done

## Story

Como usuario autorizado del tenant,
Quiero ver la lista y el detalle de las conversaciones con actualizacion en tiempo real,
Para que pueda atender el inbox con contexto completo y sin perder actividad reciente.

## Acceptance Criteria

1. Dado que el usuario tiene acceso al Inbox, cuando abre la bandeja de conversaciones, entonces el sistema muestra contacto, ultimo mensaje, fecha y hora de ultima actividad, estado, no leidos y funnel cuando exista, y la lista prioriza la actividad reciente.
2. Dado que el usuario abre una conversacion, cuando revisa el detalle, entonces el sistema muestra el historial de mensajes entrantes, respuestas de IA, mensajes de asesores, mensajes interactivos y eventos relevantes, y el contexto respeta el tenant y los permisos del usuario autenticado.
3. Dado que entra un mensaje nuevo o cambia un estado relevante, cuando el backend procesa el evento, entonces el Inbox refleja el cambio en tiempo real o de forma equivalente perceptible, y el conteo de no leidos se actualiza sin recargar toda la vista.
4. Dado que llega un mensaje desde WhatsApp, cuando el webhook lo entrega al backend, entonces el sistema lo asocia al tenant, contacto y conversacion correctos, y preserva metadata suficiente para entender el contexto del hilo.

**FR cubiertos:** FR009, FR010, FR018, FR019, FR031, FR033, NFR002, NFR003, NFR010, NFR011, NFR015

## Tasks / Subtasks

- [x] Auditar el contrato actual del Inbox y preservar lo que ya funciona.
  - [x] Revisar `backend/app/conversations/service.py`, `backend/app/conversations/routes.py`, `backend/app/realtime.py`, `backend/app/whatsapp/service.py` y `frontend/src/App.tsx` para no romper la lista, el detalle, el marcado de leido ni el refresco realtime ya existente.
  - [x] Confirmar que toda lectura y mutacion siga filtrada por `company_id` y que los recursos cross-tenant sigan respondiendo `404`.
- [x] Exponer eventos relevantes en el detalle de la conversacion.
  - [x] Extender el contrato de `ConversationDetailRead` para incluir la linea de tiempo de eventos relevantes de esa conversacion.
  - [x] Reusar el almacenamiento de `events` existente y filtrar por el `conversation_id` presente en el payload, sin crear una fuente nueva de verdad.
  - [x] Mantener orden deterministico y contexto honesto: mensajes en orden cronologico ascendente, eventos en un orden claro para lectura humana.
- [x] Ajustar el flujo realtime del Inbox.
  - [x] Mantener la conexion WebSocket existente en `/realtime/ws` y sus eventos `message.received`, `message.sent`, `message.status` y `conversation.read`.
  - [x] Hacer que la llegada de eventos refresque la lista, el hilo seleccionado y el conteo de no leidos sin recargar toda la pagina.
  - [x] Conservar el seleccionado actual cuando la conversacion siga existiendo tras el refresco.
- [x] Endurecer la UX del Inbox para estados vacios y errores.
  - [x] Mostrar labels y errores en espanol, sin contadores ni mensajes inventados.
  - [x] Mantener el orden por actividad reciente y el comportamiento responsive del workspace de Inbox.
- [x] Agregar cobertura de regresion.
  - [x] Probar que la lista de conversaciones respeta tenant, orden por actividad reciente y metadatos de ultimo mensaje/no leidos.
  - [x] Probar que el detalle de conversacion incluye mensajes y eventos relevantes para el tenant correcto.
  - [x] Probar que `message.received`, `message.sent`, `message.status` y `conversation.read` actualizan el estado visible del Inbox.
  - [x] Probar que el websocket rechaza tokens invalidos y preserva la conexion del tenant autenticado.

## Dev Notes

### Business Context

- Esta historia es el centro operativo del Epic 2: el Inbox debe permitir leer conversaciones activas con contexto completo y reflejar actividad reciente sin polling pesado ni recargas manuales.
- El objetivo no es rehacer el Inbox desde cero. Ya existe una base funcional que lista conversaciones, abre detalles, marca leidos y escucha realtime; esta historia debe cerrar la brecha entre esa base y el contrato del PRD.
- El detalle debe mostrar mensajes y eventos relevantes porque la operacion comercial necesita ver el hilo completo, no solo el texto del chat.

### Current Code State

- `backend/app/conversations/service.py` ya implementa `list_conversations()`, `conversation_to_inbox_item()`, `get_conversation()`, `get_conversation_messages()`, `mark_conversation_read()` y `append_message()`.
- `backend/app/conversations/routes.py` ya expone `GET /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/read`, `POST /conversations/{id}/send-message` y rutas de asignacion/funnel.
- `backend/app/realtime.py` ya implementa autenticacion por token, registro de conexiones por `company_id` y broadcast por tipo de evento.
- `backend/app/whatsapp/service.py` ya publica eventos realtime para mensajes entrantes, mensajes salientes y cambios de estado de mensajes, y tambien actualiza `unread_count` en conversaciones.
- `backend/app/events/routes.py` y `backend/app/events/service.py` ya existen, pero `GET /conversations/{id}` todavia no incluye eventos relevantes en la respuesta.
- `frontend/src/App.tsx` ya conecta el websocket, recarga el Inbox al recibir eventos y vuelve a cargar el detalle cuando el evento afecta la conversacion seleccionada.
- `frontend/src/App.tsx` tambien ya mapea `contact_name`, `last_message`, `last_sender_type`, `unread_count` y `funnel` para la lista del Inbox.

### Critical Guardrails

- No introducir polling artificial si el websocket ya puede cubrir el caso.
- No romper el contrato actual de tenant isolation: `404` para recursos de otro tenant y queries siempre filtradas por `company_id`.
- No agregar un router nuevo ni una libreria de estado paralela; el frontend debe seguir usando `api<T>()`, `realtimeUrl()` y `useAuthStore`.
- No inventar eventos ni mensajes de sistema: todo lo mostrado debe venir del backend o de metadatos ya persistidos.
- No alterar el orden natural de la lista: el Inbox debe seguir priorizando la actividad reciente.
- No dejar de manejar desconexiones y reconexiones del websocket; el Inbox tiene que degradar de forma perceptible, no romperse.

### Implementation Guidance

- La forma mas segura de cumplir el contrato de detalle es extender la respuesta de `GET /conversations/{conversation_id}` con una coleccion de eventos relevantes para esa conversacion, reusando el modelo `Event`.
- Si se necesita un helper nuevo para eventos de conversacion, debe ser tenant-scoped y deterministico, con orden claro para lectura humana.
- Reusar el websocket existente para actualizar la vista visible y el contador de no leidos; no crear otro canal para el Inbox.
- Mantener el `selectedConversationId` vivo durante refreshes cuando la conversacion siga presente en la lista.
- En frontend, el detalle debe permanecer honesto: si no hay eventos, mostrar estado vacio claro; si el backend no puede leer algo, mostrar error util en espanol.

### Suggested File Targets

- Backend likely to change:
  - `backend/app/conversations/schemas.py`
  - `backend/app/conversations/routes.py`
  - `backend/app/conversations/service.py`
  - `backend/app/events/service.py`
  - `backend/app/realtime.py`
  - `backend/app/whatsapp/service.py`
- Frontend likely to change:
  - `frontend/src/App.tsx`
- Tests likely to change:
  - `backend/tests/test_tenant_and_orders.py`
  - `backend/tests/test_whatsapp_setup.py`
  - o un archivo nuevo enfocado en realtime/inbox si la cobertura crece demasiado

### Testing Requirements

- Probar que la lista de conversaciones se ordena por actividad reciente y conserva los metadatos visibles del hilo.
- Probar que el detalle de conversacion queda filtrado por tenant y devuelve mensajes y eventos del hilo correcto.
- Probar que el websocket de realtime refresca la UI cuando llegan `message.received`, `message.sent`, `message.status` y `conversation.read`.
- Probar que el conteo de no leidos baja al marcar la conversacion como leida y que el refresh no rompe el hilo seleccionado.
- Probar que el flujo sigue funcionando con la suite SQLite de tests y sin depender de SQL especifico de MySQL para esta historia.

### Project Structure Notes

- Mantener la logica de dominio en `backend/app/conversations/` y reutilizar `backend/app/events/` para la linea de tiempo.
- El Inbox ya vive dentro del shell unico de `frontend/src/App.tsx`; no introducir un router solo para esta historia.
- El detalle debe seguir representando conversaciones reales, no mocks ni datos sintéticos.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 2, Historia 2.1, criterios de aceptacion FR009, FR010, FR018, FR019, FR031 y FR033]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - seccion Inbox, NFR002, NFR003, NFR010, NFR011 y NFR015]
- [Source: `_bmad-output/project-context.md` - reglas criticas de multi-tenant, errores 404, backend como fuente de verdad y uso de `api<T>()`]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - estructura del Inbox como workspace de lista, hilo y rail contextual]
- [Source: `backend/app/conversations/routes.py` - contrato actual de lista, detalle, lectura y envio de mensajes]
- [Source: `backend/app/conversations/service.py` - orden de lista, mapeo de Inbox y actualizacion de unread_count]
- [Source: `backend/app/realtime.py` - autentificacion y broadcast websocket por `company_id`]
- [Source: `backend/app/whatsapp/service.py` - eventos realtime para mensajes recibidos/enviados y estados]
- [Source: `backend/app/events/routes.py` - API existente de eventos del tenant]
- [Source: `frontend/src/App.tsx` - carga del Inbox, websocket y render actual del detalle]
- [Source: `docs/adr/0001-security-and-multi-tenant-enforcement.md` - `404` cross-tenant, `403` por permisos y secretos redacted]
- [Source: `docs/adr/0004-integrations-events-audit-and-outbox.md` - eventos durables, outbox y delivery periferico]
- [Source: `https://fastapi.tiangolo.com/advanced/websockets/` - contrato de WebSocket con `accept`, `receive_json`, `send_json` y manejo de desconexiones]
- [Source: `https://docs.sqlalchemy.org/en/20/orm/session_basics.html` - uso de `Session`/`sessionmaker`, `commit()` y `flush()` para unidades de trabajo consistentes]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Implementacion basada en el estado existente del Inbox, reutilizando `GET /conversations`, `GET /conversations/{id}`, `realtime/ws` y los eventos durables del backend.
- Se agrego `events` al detalle de conversacion usando el almacenamiento ya existente en `events`.
- Se propago `conversation_id` a los eventos realtime de `message.status` para refrescar el hilo correcto en la UI.
- Se agrego cobertura de regresion para orden del Inbox, detalle con eventos, autenticacion invalida y publicaciones realtime.
- Se corrigio la linea de tiempo para incluir eventos de negocio del hilo (`order.*` y `appointment.*`) con `conversation_id` persistido en sus payloads.
- Se corrigio la linea de tiempo para incluir tambien eventos de asignacion, funnel y cierre de conversacion.
- Se movio el filtrado de eventos por conversacion a SQL para evitar cargar todos los eventos del tenant en memoria.
- Se acoto la consulta a eventos relevantes del Inbox usando `event_type` indexado para reducir el costo de busqueda.
- Se aseguro que los eventos de conversacion se escriban dentro de la misma transaccion que la mutacion principal.
- Se resolvieron los hallazgos de code review pendientes: `conversation.read` ya persiste en la linea de tiempo, los cambios de estado del hilo publican realtime, los eventos de orden/cita tambien refrescan la vista, la timeline ya no se trunca a 100 eventos y el frontend mantiene etiquetas honestas en espanol.
- Se resolvieron los hallazgos de code review de la ultima iteracion: los cambios de estado ahora actualizan la recencia del inbox, `message.status` se descarta si no hay conversacion local y el detalle no marca leido de forma optimista cuando falla el POST.
- Se resolvieron los hallazgos de code review mas recientes: `conversation.read` se volvio idempotente para no duplicar eventos, el refresco realtime del hilo seleccionado ya no vuelve a marcar leido y los `message.status` que llegan antes de la fila local se preservan para la linea de tiempo.
- Se resolvieron los hallazgos de code review siguientes: el hilo abierto vuelve a marcarse leido cuando entra un `message.received` y la linea de tiempo recupera `message.status` retrasados sin barrer todo el tenant.
- Validaciones ejecutadas:
  - `python3 -m py_compile backend/app/events/service.py backend/app/conversations/schemas.py backend/app/conversations/service.py backend/app/conversations/routes.py backend/app/whatsapp/service.py backend/tests/test_inbox_realtime.py`
  - `./backend/.venv/bin/python -m pytest backend/tests/test_inbox_realtime.py -q`
  - `./backend/.venv/bin/python -m pytest backend/tests/test_whatsapp_setup.py -q`
  - `./backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py -k "inbox_conversations_can_filter_by_funnel or conversation_service_returns_spanish_errors_for_missing_resources or generate_auto_reply_uses_welcome_funnel_context" -q`
  - `npm run build`
  - `npm run lint`

### Completion Notes List

- `ConversationDetailRead` ahora incluye `events` ademas de `messages`.
- `GET /conversations/{id}` devuelve la linea de tiempo de eventos relevantes del hilo usando el storage existente de `events`.
- `message.status` ahora publica `conversation_id` cuando puede asociarse a una conversacion local.
- Los eventos de orden y cita ahora incluyen `conversation_id`, permitiendo que el detalle del Inbox muestre contexto de negocio relevante.
- Los eventos de asignacion, funnel y cierre de conversacion ahora tambien quedan registrados en la linea de tiempo del hilo.
- `conversation.read` ahora queda persistido y visible en el detalle del hilo.
- La consulta de eventos de conversacion ahora filtra en base de datos por `payload.conversation_id`.
- La consulta de eventos de conversacion ya no trunca la linea de tiempo a 100 filas y sigue usando tipos relevantes del Inbox con el indice existente de `event_type`.
- Los eventos de conversacion ahora se persisten de forma transaccional junto con la mutacion que los origina.
- El Inbox del frontend renderiza una linea de tiempo de eventos relevantes debajo del historial de mensajes.
- El inbox ahora refresca la linea de tiempo despues de enviar mensajes desde la UI y marca leidos antes de cargar el detalle para mostrar `conversation.read` de inmediato.
- `conversation.assigned`, `conversation.funnel_assigned`, `conversation.closed`, `order.*` y `appointment.*` publican realtime para reflejar cambios de negocio sin recarga manual.
- La timeline usa etiquetas en espanol para todos los tipos emitidos por esta historia.
- La configuracion de nginx del frontend vuelve a proxyar `/docs`, `/redoc` y OpenAPI hacia FastAPI.
- El inbox reordena hilos por actividad de estado ademas de mensaje y conserva el estado de leido real cuando la mutacion falla.
- `conversation.read` ahora es idempotente y el websocket evita reprocesar la misma lectura cuando refresca el hilo seleccionado.
- Los `message.status` que llegan antes de la fila local del mensaje se guardan y aparecen en la timeline cuando la conversacion puede resolver el hilo.
- Se agrego cobertura de regresion para la idempotencia de lectura y para preservar estados retrasados de mensajes.
- El hilo seleccionado vuelve a marcarse leido cuando entra un `message.received` y el detalle recupera `message.status` asociados por `external_message_id` sin recorrer todo el tenant.
- El build del frontend y la regresion focalizada de backend quedaron verdes.

### File List

- `_bmad-output/implementation-artifacts/2-1-ver-y-actualizar-conversaciones-en-tiempo-real.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/app/appointments/service.py`
- `backend/app/conversations/routes.py`
- `backend/app/conversations/schemas.py`
- `backend/app/conversations/service.py`
- `backend/app/events/service.py`
- `backend/app/orders/service.py`
- `backend/app/whatsapp/service.py`
- `backend/app/whatsapp/routes.py`
- `backend/tests/test_inbox_realtime.py`
- `backend/tests/test_whatsapp_setup.py`
- `backend/README.md`
- `README.md`
- `frontend/.env.example`
- `frontend/nginx.conf`
- `frontend/src/App.tsx`
- `frontend/src/lib/api.ts`

## Change Log

- 2026-06-29: Implementado detalle de Inbox con eventos relevantes, refresco realtime del hilo seleccionado y estado de mensaje asociado a `conversation_id`.
- 2026-06-29: Agregada cobertura de regresion para orden del Inbox, detalle con eventos, realtime broadcast y rechazo de tokens invalidos.
- 2026-06-29: Corregido el timeline del Inbox para incluir eventos de orden y cita asociados a la conversacion y mover el filtrado a SQL.
- 2026-06-29: Corregido el timeline del Inbox para incluir eventos de asignacion, funnel y cierre, y para limitar la busqueda por tipos indexados.
- 2026-06-29: Addressed code review findings - 2 items resolved (Date: 2026-06-29)
- 2026-06-29: Ajustada la persistencia para escribir los eventos de conversacion en la misma transaccion que la mutacion origen.
- 2026-06-29: Validacion ejecutada con `pytest`, `tsc/vite build` y `eslint`.
- 2026-07-01: Resueltos hallazgos de code review sobre timeline completa, realtime de cambios de negocio, etiquetas en espanol y refresh del inbox.
- 2026-07-01: Addressed code review findings - 2 items resolved (Date: 2026-07-01)
- 2026-07-01: Story marcada como done despues de cerrar los hallazgos de review y validar la regresion focalizada.
- 2026-07-01: Addressed code review findings - 2 items resolved (Date: 2026-07-01)
