---
baseline_commit: ee0b2c761a0873ae7b8b682ce757a43546222c48
---

# Story 2.3: Desactivar, reactivar y continuar la IA en una conversacion

Status: Done

## Story

Como asesor o admin del tenant,
Quiero pausar y reactivar la IA por conversacion desde el Inbox,
Para que pueda tomar control humano cuando haga falta y luego continuar el hilo con contexto completo sin perder el historial.

## Acceptance Criteria

1. Dado que un usuario autorizado abre una conversacion con IA activa, cuando pausa la IA desde el Inbox, entonces el sistema persiste ese estado por conversacion, publica el cambio en realtime, registra evento/auditoria y evita que la siguiente respuesta entrante dispare auto-reply hasta que se reactive.
2. Dado que una conversacion tiene la IA pausada, cuando el mismo usuario autorizado la reactiva desde el mismo contexto del Inbox, entonces el sistema persiste la reactivacion, publica el cambio en realtime, registra evento/auditoria y la siguiente interaccion con el cliente vuelve a usar todo el historial de mensajes humanos y del cliente como contexto.
3. Dado que la IA esta pausada o activa, cuando el usuario envia mensajes manuales desde el Inbox, entonces el hilo debe seguir operativo, la seleccion de conversacion no debe perderse y la UI debe mostrar de forma explicita el estado real de IA separado del estado de asignacion humana.
4. Dado que un usuario sin permiso o de otro tenant intenta pausar o reactivar la IA, entonces el backend debe bloquear la accion con el error correcto y el frontend debe conservar el hilo, el draft y el estado visible sin inventar cambios locales.

**FR cubiertos:** FR012, FR013, FR014, FR018, FR019, FR020, FR025, NFR003, NFR010, NFR011, NFR015, NFR018, NFR019, NFR020, NFR021, NFR027, NFR029

## Tasks / Subtasks

- [x] Auditar el contrato actual de handoff y auto-reply para separar IA activa de asignacion humana.
  - [x] Revisar `frontend/src/App.tsx`, `backend/app/conversations/routes.py`, `backend/app/conversations/service.py`, `backend/app/ai/runtime.py` y `backend/app/whatsapp/service.py`.
  - [x] Confirmar que `assigned_user_id` y `waiting_human` no se usen como unico proxy del estado de IA.
  - [x] Identificar si la implementacion requiere un flag persistido nuevo por conversacion o una extension equivalente del modelo actual.
- [x] Implementar persistencia backend para pausar y reactivar IA por conversacion.
  - [x] Exponer endpoints o servicios explicitos para pausar y reactivar IA sin romper el flujo actual de asignacion manual.
  - [x] Hacer que el runtime de IA respete el estado persistido antes de generar auto-reply.
  - [x] Registrar evento interno y auditoria para cada transicion de estado.
- [x] Actualizar el Inbox para mostrar y controlar el estado real de IA.
  - [x] Reemplazar el toggle local actual por un flujo que lea y modifique el estado persistido.
  - [x] Mostrar labels claros en espanol para `IA activa`, `IA pausada` y `Handoff humano`.
  - [x] Mantener el composer, la seleccion del hilo y el refresh realtime cuando la accion falle o tarde.
- [x] Agregar regresion automatizada.
  - [x] Cubrir pausa y reactivacion en backend con aislamiento por tenant.
  - [x] Cubrir que la auto-respuesta no se dispare cuando la IA esta pausada.
- [x] Cubrir que la reactivacion recupere el flujo normal usando el historial existente.
  - [x] Cubrir que la UI no pierda draft ni seleccion cuando la mutacion falla.

### Review Findings

- [x] [Review][Patch] Falta exigir permisos de modulo en pausar/reanudar IA [backend/app/conversations/routes.py:127]
- [x] [Review][Patch] `get_or_create_contact` hace un escaneo completo del tenant en la ruta caliente de WhatsApp [backend/app/contacts/service.py:44]
- [x] [Review][Patch] La normalizacion de telefonos sigue siendo inconsistente entre runtime, fallback y migracion [backend/app/contacts/service.py:12] / [backend/migrations/versions/20260702_0019_normalize_contact_phones.py:18]

## Dev Notes

### Business Context

- Esta historia completa el control operativo del Inbox: el equipo debe poder tomar una conversacion, pausar la IA, responder manualmente y luego devolver la IA al flujo normal sin perder contexto.
- El alcance no es crear un nuevo flujo de mensajeria. El objetivo es hacer real y persistente el handoff humano/IA que hoy solo esta parcialmente simulado en la UI.
- La historia debe preservar el historial completo de la conversacion; reactivar la IA no crea una nueva conversacion ni reinicia contexto.

### Current Code State

- `frontend/src/App.tsx` tiene un boton local `Pasar a humano` en `InboxPage`, pero hoy solo cambia estado en memoria con `requestHuman()`; no persiste nada en backend.
- `frontend/src/App.tsx` mapea `assigned_user_id` como `Equipo comercial` o `IA`, lo que mezcla asignacion humana con estado de IA y no es suficiente para esta historia.
- `frontend/src/App.tsx` ya refresca Inbox por realtime y mantiene draft cuando falla el envio manual, asi que el flujo de pausa/reactivacion debe conservar esas propiedades.
- `backend/app/ai/runtime.py` solo genera auto-reply cuando la conversacion esta en `open` o `waiting_customer`; si la IA se pausa, el runtime debe consultar el estado persistido antes de intentar responder.
- `backend/app/conversations/service.py` ya publica eventos para `conversation.assigned`, `conversation.funnel_assigned`, `conversation.closed` y `conversation.read`; la nueva transicion debe seguir ese patron y no quedarse solo en UI.
- `backend/app/conversations/routes.py` expone acciones de conversacion, pero no existe hoy un endpoint explicito para pausar o reactivar IA por conversacion.
- `backend/app/whatsapp/service.py` activa auto-reply despues de procesar mensajes entrantes; la historia debe impedir que ese flujo dispare respuestas mientras la IA este pausada.
- `backend/tests/test_inbox_realtime.py` ya cubre realtime, asignacion, lectura, mensajes manuales y metadata interactiva; es el mejor punto para agregar cobertura de pausa/reactivacion.

### Critical Guardrails

- No usar `assigned_user_id` como sustituto del estado de IA.
- No perder el historial ni crear una conversacion nueva al reactivar la IA.
- No romper el envio manual ni el refresh realtime del Inbox.
- No permitir cambios cross-tenant; lo ajeno debe seguir respondiendo `404`.
- Mantener los errores visibles en espanol y el comportamiento de permisos en backend, no solo en UI.
- Si se agrega un flag nuevo, debe estar en el modelo, migracion, API y mapeo del frontend antes de considerarse listo.

### Implementation Guidance

- Si se introduce un flag persistido por conversacion, debe ser la fuente de verdad para `generate_auto_reply` y para la UI del Inbox.
- Si se decide reutilizar un estado existente, documentar claramente por que no rompe la semantica de asignacion humana y probar ambos caminos.
- La UI debe exponer acciones separadas para pausar y reactivar IA, con textos cortos y claros en espanol.
- El frontend no debe “optimizar” el estado local de IA sin confirmacion del backend; la verdad queda en la API y en realtime.
- Cualquier cambio de estado debe dejar evento trazable y, si aplica, audit log con usuario, conversacion y transicion anterior/nueva.

### Suggested File Targets

- Backend likely to change:
  - `backend/app/conversations/models.py`
  - `backend/app/conversations/schemas.py`
  - `backend/app/conversations/routes.py`
  - `backend/app/conversations/service.py`
  - `backend/app/ai/runtime.py`
  - `backend/app/whatsapp/service.py`
  - `backend/app/events/service.py` si se introduce un nuevo tipo de evento o se ajusta el timeline
- Frontend likely to change:
  - `frontend/src/App.tsx`
- Tests likely to change:
  - `backend/tests/test_inbox_realtime.py`
  - `backend/tests/test_tenant_and_orders.py` si hace falta cubrir el runtime de IA y la pausa/reactivacion

### Testing Requirements

- Probar que pausar IA impide auto-reply para mensajes entrantes posteriores.
- Probar que reactivar IA vuelve a habilitar auto-reply usando el historial existente.
- Probar que la accion respeta tenant isolation y permisos.
- Probar que el Inbox conserva seleccionado el hilo, el draft y el estado visible cuando la mutacion falla.
- Probar que el timeline/eventos refleja la transicion de estado.

### Project Structure Notes

- Mantener la logica de estado de IA dentro de los dominios existentes de conversacion/AI/WhatsApp; no crear un modulo paralelo solo para este toggle.
- Preservar el shell del Inbox en `frontend/src/App.tsx`; extraer componentes solo si reduce complejidad real.
- No introducir dependencias nuevas para resolver esta historia.
- Si se requiere migracion, debe ser compatible con MySQL y con la estructura actual de modelos tenant-scoped.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 2, historia 2.3 y FR012, FR013, FR014, FR018, FR019, FR020, FR025]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - seccion Inbox, IA y UJ-001/UJ-004; tambien NFR003, NFR010, NFR011, NFR015, NFR018, NFR019, NFR020, NFR021, NFR027 y NFR029]
- [Source: `_bmad-output/project-context.md` - reglas criticas sobre multi-tenancy, 404 cross-tenant, backend como fuente de verdad y uso de `api<T>()`]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - Inbox como workspace de lista, hilo y rail contextual; separacion entre estado de dominio y estado de UI]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - patrones de handoff, estados de IA activa/pausada y preservation de draft]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/DESIGN.md` - estados visuales, tono operacional y sistema de marca Swa Tech]
- [Source: `frontend/src/App.tsx` - `requestHuman()`, `mapApiConversation()`, `InboxPage` y el estado actual de IA en UI]
- [Source: `backend/app/ai/runtime.py` - condiciones de auto-reply y uso del historial para generar respuestas]
- [Source: `backend/app/conversations/service.py` - transiciones de conversacion, eventos y realtime]
- [Source: `backend/app/whatsapp/service.py` - flujo de mensajes entrantes y disparo de auto-reply]
- [Source: `backend/tests/test_inbox_realtime.py` - patrones de prueba para realtime, handoff y tenant isolation]

## Change Log

- 2026-07-03: Se resolvieron los hallazgos de revision sobre el control de IA por conversacion, la revalidacion del estado persistido antes de auto-reply y la preservacion de eventos de status para backfill.
- 2026-07-04: Se resolvieron los hallazgos de takeover privilegiado, lock de autoasignacion por tenant y uso de timestamp de base de datos para eventos.
- 2026-07-04: Se resolvieron los hallazgos de carrera final de auto-reply, atomicidad de autoasignacion y dedupe del timeline de eventos.

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- `backend/.venv/bin/python -m pytest tests/test_inbox_realtime.py::test_ai_pause_and_resume_controls_auto_reply_and_realtime -q`
- `backend/.venv/bin/python -m pytest tests/test_inbox_realtime.py -q`
- `backend/.venv/bin/python -m pytest tests/test_tenant_and_orders.py -k 'generate_auto_reply or interactive_after_capture_trigger' -q`
- `backend/.venv/bin/python -m pytest tests/test_whatsapp_setup.py -q`
- `npm run build` en `frontend/`
- `backend/.venv/bin/python -m pytest backend/tests/test_inbox_realtime.py backend/tests/test_tenant_and_orders.py -q`
- `backend/.venv/bin/python -m pytest backend/tests/test_user_permissions.py -q`
- `backend/.venv/bin/python -m pytest backend/tests/test_user_permissions.py backend/tests/test_tenant_and_orders.py backend/tests/test_inbox_realtime.py -q`
- `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py -q`

### Completion Notes List

- Se agrego `ai_enabled` persistido por conversacion con migracion, modelo y schemas actualizados.
- El backend expone `POST /conversations/{conversation_id}/ai/pause` y `POST /conversations/{conversation_id}/ai/resume`, emite eventos `conversation.ai_paused` y `conversation.ai_resumed`, y registra auditoria.
- `backend/app/ai/runtime.py` y `backend/app/whatsapp/service.py` respetan el estado persistido antes de disparar auto-reply.
- El Inbox muestra el estado de IA separado del estado de asignacion, permite pausar o reactivar desde la UI y refresca la vista tras la mutacion.
- Se corrigio la normalizacion de telefonos en contactos para que los webhooks de WhatsApp reutilicen el mismo hilo aunque el telefono llegue con o sin `+`.
- Las acciones de pausar y reactivar IA ahora requieren permiso del modulo `inbox`, alineadas con el resto de protecciones por modulo.
- Los telefonos de contacto quedan normalizados y existe un fallback de compatibilidad para registros legacy sin volver a cargar todo el tenant en memoria.
- Se agrego cobertura de regresion para pausa/reanudacion, bloqueo de auto-reply y eventos realtime asociados.
- Se corrigieron los hallazgos de revision: `waiting_human` ahora permite auto-reply tras reactivar la IA, el runtime revalida el estado persistido antes de generar respuesta, y los eventos `message.status` se conservan aunque el `conversation_id` aun no exista localmente.
- Se ajusto el orden temporal de eventos internos para estabilizar el backfill y la seleccion del ultimo `message.sent` en pruebas y restauracion de estado.
- Se corrigio el takeover privilegiado para permitir que owner/admin/superadmin reasignen un chat tomado por otro asesor.
- Se aseguro la lectura del toggle de autoasignacion con lock de fila del tenant para evitar asignaciones sobre una configuracion ya desactivada.
- Se devolvio `create_event()` al timestamp gestionado por la base de datos para evitar desorden entre workers.
- Se dejo cobertura regresiva para takeover privilegiado, orden de eventos `message.sent` con timestamps de BD y el flujo de autoasignacion bajo lock.
- Se agrego un guard final antes del envio de auto-reply para evitar respuestas si la IA se pausa despues de generar el mensaje.
- `list_conversation_events()` ahora deduplica correctamente los `message.status` al combinar timeline y backfill.
- La autoasignacion por conversacion usa una lectura bloqueada del conjunto de usuarios activos para que el conteo y la seleccion sean atomicos.

### File List

- `_bmad-output/implementation-artifacts/2-3-desactivar-reactivar-y-continuar-la-ia-en-una-conversacion.md`
- `backend/app/ai/runtime.py`
- `backend/app/contacts/service.py`
- `backend/app/conversations/models.py`
- `backend/app/conversations/routes.py`
- `backend/app/conversations/schemas.py`
- `backend/app/conversations/service.py`
- `backend/app/events/service.py`
- `backend/app/whatsapp/service.py`
- `backend/migrations/versions/20260702_0018_conversation_ai_enabled.py`
- `backend/migrations/versions/20260702_0019_normalize_contact_phones.py`
- `backend/tests/test_inbox_realtime.py`
- `backend/tests/test_tenant_and_orders.py`
- `backend/tests/test_user_permissions.py`
- `frontend/src/App.tsx`
