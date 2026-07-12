---
baseline_commit: ee0b2c7
---

# Story 2.2: Responder manualmente desde el Inbox

Status: done

## Story

Como asesor o admin del tenant,
Quiero enviar mensajes manuales y ver respuestas interactivas dentro del Inbox,
Para que pueda continuar una conversacion sin depender de la IA.

## Acceptance Criteria

1. Dado que el usuario tiene permiso para responder conversaciones, cuando escribe y envia un mensaje manual desde el Inbox, entonces el sistema usa la cuenta WhatsApp conectada del tenant para enviarlo y registra el mensaje como parte del historial de la conversacion.
2. Dado que la conversacion contiene botones, listas o respuestas interactivas, cuando el cliente responde por un medio interactivo, entonces el sistema conserva la metadata necesaria para que Inbox e IA entiendan el contexto y el evento queda visible en el historial.
3. Dado que el envio manual falla por una condicion tecnica, cuando la operacion no se completa, entonces el sistema no pierde el borrador ni el contexto de la respuesta y deja la conversacion disponible para reintento o gestion humana.

**FR cubiertos:** FR011, FR033, FR034, FR019, FR020, FR025, NFR003, NFR010, NFR011, NFR015, NFR018, NFR020, NFR021, NFR024

## Tasks / Subtasks

- [x] Auditar el flujo real de respuesta manual y preservar lo que ya funciona.
  - [x] Revisar `frontend/src/App.tsx`, `backend/app/whatsapp/routes.py`, `backend/app/whatsapp/service.py` y `backend/app/conversations/routes.py` para evitar confundir el envio real por WhatsApp con el registro local de historial.
  - [x] Confirmar que toda mutacion siga filtrada por `company_id` y que los recursos cross-tenant sigan respondiendo `404`.
- [x] Mantener el envio manual usando la cuenta WhatsApp del tenant.
  - [x] Reusar el flujo de `POST /whatsapp/messages` para el envio real al canal, porque ese camino ya usa la cuenta conectada, crea o reusa la conversacion correcta y persiste `message.sent` en la misma transaccion.
  - [x] No sustituir ese camino por `POST /conversations/{conversation_id}/send-message`, porque esa ruta solo agrega mensaje al historial local y no entrega el mensaje a WhatsApp.
  - [x] Garantizar que el mensaje enviado quede visible al recargar el Inbox y al reabrir el hilo.
- [x] Conservar la metadata de respuestas interactivas.
  - [x] Mantener intacto el almacenamiento de `metadata_json` de mensajes entrantes, especialmente `interactive_reply`, `raw` y `message_type`.
  - [x] Asegurar que los mensajes interactivos sigan apareciendo en el historial con el contexto necesario para que Inbox e IA los interpreten correctamente.
  - [x] No introducir una segunda fuente de verdad para interactivos; reutilizar el modelo de mensajes existente.
- [x] Endurecer la experiencia de composer ante fallas.
  - [x] Preservar el draft cuando falle el envio.
  - [x] Mostrar un error inline util en espanol y mantener la conversacion seleccionada para reintento.
  - [x] Evitar limpiar el contenido del composer hasta que el backend confirme el envio.
- [x] Agregar cobertura de regresion.
  - [x] Probar que el envio manual registra el mensaje en WhatsApp y en el historial del hilo correcto.
  - [x] Probar que un fallo de envio no borra el draft ni rompe la seleccion de la conversacion.
  - [x] Probar que una respuesta interactiva entrante conserva metadata suficiente para el detail del Inbox y para la IA.
- [x] Probar que el flujo respeta aislamiento por tenant y rechaza accesos cruzados.

### Review Findings

- [x] [Review][Patch] `list_conversation_events` omite `limit`/`offset` cuando no hay `message.status` [backend/app/events/service.py:85]
- [x] [Review][Patch] `sendInboxMessage` puede deseleccionar el hilo correcto si `refreshInbox()` corre antes de que React aplique el nuevo `conversation_id` [frontend/src/App.tsx:2010]

## Dev Notes

### Business Context

- Esta historia cierra el handoff humano dentro del Epic 2: el operador debe poder seguir la conversacion sin depender de la IA y sin perder el contexto de respuestas interactivas.
- El objetivo no es crear un nuevo flujo de mensajeria. Ya existe un camino de envio manual por WhatsApp y un historial de mensajes del hilo; esta historia debe consolidarlo y evitar regresiones.
- La operacion comercial necesita que los mensajes salientes, las respuestas tipo boton/lista y los fallos de envio queden visibles y trazables en el mismo hilo.

### Current Code State

- `frontend/src/App.tsx` ya tiene composer del Inbox con draft local, estado `sending`, error inline y refresco posterior al envio.
- `frontend/src/App.tsx` actualmente llama a `POST /whatsapp/messages` con `to = selectedConversation.phone`, lo que mantiene el envio real por el canal WhatsApp y luego vuelve a cargar Inbox + detail.
- `frontend/src/App.tsx` ya mapea mensajes a burbujas segun `sender_type` y muestra la linea de tiempo de eventos relevantes debajo del hilo.
- `backend/app/whatsapp/routes.py` expone `POST /whatsapp/messages`, `POST /whatsapp/messages/buttons`, `POST /whatsapp/messages/product-cards` y el resto de la superficie de envio por canal.
- `backend/app/whatsapp/service.py` persiste mensajes salientes como `message.sent`, publica realtime, y al recibir mensajes entrantes guarda `metadata_json` con `raw` y `interactive_reply` cuando aplica.
- `backend/app/conversations/routes.py` expone `POST /conversations/{conversation_id}/send-message`, pero ese handler solo agrega mensaje al historial local; no debe confundirse con envio real al canal.
- `backend/app/events/service.py` ya reconoce `message.received`, `message.sent` y `message.status` como eventos de conversacion.
- `backend/tests/test_inbox_realtime.py` ya cubre parte del Inbox realtime y es un buen punto para agregar regresion sobre envio manual y metadata de interactividad.

### Critical Guardrails

- No crear un flujo paralelo de mensajeria ni un nuevo router solo para esta historia.
- No reemplazar el envio real por el handler local de conversaciones.
- No inventar mensajes, estados o metadata que no venga del backend.
- No perder el draft en errores de red, validacion o respuesta del proveedor.
- No romper el refresh realtime del Inbox ni la seleccion actual del hilo.
- Mantener errores visibles en espanol y seguir devolviendo `404` para recursos de otro tenant.
- Si se tocan mensajes interactivos, preservar `message_type="interactive"` y el payload original; no reducirlo a texto plano.

### Implementation Guidance

- Si el composer sigue usando `POST /whatsapp/messages`, la garantia clave es que el backend devuelva la respuesta normalizada y que el frontend solo limpie el draft despues del `await` exitoso.
- Si se ajusta el backend, reutilizar `app.whatsapp.service._send_text_with_account()` para mantener una sola fuente de verdad para envio, persistencia, evento y realtime.
- Para mensajes interactivos, confiar en que el backend ya escribe `metadata_json.interactive_reply`; la historia solo debe asegurar que ese dato no se pierda ni se oculte por un mapeo pobre del frontend.
- Si se expone el contenido en el Inbox, el mensaje debe seguir mostrando la vista honesta del hilo: texto visible, tipo de emisor y estado de envio cuando aplique.
- Cualquier mejora de UI debe conservar el layout actual de Inbox y no introducir un router nuevo ni una reestructuracion amplia del shell.

### Suggested File Targets

- Backend likely to change:
  - `backend/app/whatsapp/routes.py`
  - `backend/app/whatsapp/service.py`
  - `backend/app/conversations/routes.py` si se decide endurecer o documentar el handler local
- Frontend likely to change:
  - `frontend/src/App.tsx`
- Tests likely to change:
  - `backend/tests/test_inbox_realtime.py`
  - `backend/tests/test_whatsapp_setup.py` si hace falta cubrir el contrato de envio manual
  - `backend/tests/test_tenant_and_orders.py` solo si se necesita una regresion compartida de metadata/interactivos

### Testing Requirements

- Probar envio exitoso desde Inbox y persistencia en el historial correcto.
- Probar que el mensaje saliente genera `message.sent` y refresca el hilo sin recarga manual.
- Probar que el fallo de envio conserva draft, error inline y seleccion de conversacion.
- Probar que las respuestas interactivas entrantes mantienen `interactive_reply` y metadata util para reconstruir contexto.
- Probar tenant isolation: usuario autenticado solo ve y modifica su propio `company_id`.
- Probar que el flujo funciona con la suite SQLite de tests y sin depender de SQL especifico de MySQL.

### Project Structure Notes

- La logica de envio debe quedarse en `backend/app/whatsapp/`; no moverla a una capa nueva.
- El Inbox sigue viviendo dentro de `frontend/src/App.tsx`; extraer componentes solo si realmente reduce complejidad.
- Los mensajes interactivos ya se guardan como metadatos del mensaje, no como una entidad aparte.
- No introducir datos falsos ni mocks para simular respuestas del cliente o del proveedor.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 2, Historia 2.2 y criterios de aceptacion FR011, FR033 y FR034]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - seccion Inbox y NFR003, NFR010, NFR011, NFR015, NFR018, NFR020, NFR021 y NFR024]
- [Source: `_bmad-output/project-context.md` - reglas criticas sobre multi-tenant, backend como fuente de verdad, errores 404 y uso de `api<T>()`]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - Inbox como workspace de lista, hilo y rail contextual; composer con borrador preservado]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - patrones de Inbox, composer, handoff y estados de error]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/DESIGN.md` - sistema visual, tono operacional, dark mode por defecto y reglas de estados]
- [Source: `frontend/src/App.tsx` - composer actual del Inbox, refresco realtime y mapeo de mensajes]
- [Source: `backend/app/whatsapp/routes.py` - endpoints de envio real por WhatsApp]
- [Source: `backend/app/whatsapp/service.py` - envio real, persistencia de `message.sent` y metadata de mensajes entrantes interactivos]
- [Source: `backend/app/conversations/routes.py` - handler local de historial que no envia al canal]
- [Source: `backend/app/events/service.py` - eventos de conversacion relevantes para Inbox]
- [Source: `backend/tests/test_inbox_realtime.py` - cobertura existente para Inbox/realtime]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- `backend/.venv/bin/python -m pytest backend/tests/test_inbox_realtime.py backend/tests/test_whatsapp_setup.py -q`
- `backend/.venv/bin/python -m pytest backend/tests -q`
- `npm run build` en `frontend/`
- `npm run lint` en `frontend/`
- `backend/.venv/bin/python -m pytest backend/tests/test_inbox_realtime.py -q`
- `npm run build` en `frontend/`
- `npm run lint` en `frontend/`

### Completion Notes List

- Se agregaron tests de regresion para el envio manual real por WhatsApp, el handler local de historial y la preservacion de `interactive_reply` en mensajes entrantes.
- El flujo productivo existente ya usaba `POST /whatsapp/messages` para el envio real y `POST /conversations/{conversation_id}/send-message` como append local; la historia quedo reforzada con pruebas que fijan esa diferencia.
- La suite backend completa y la validacion del frontend quedaron verdes.
- Se corrigio el composer del Inbox para usar `conversation_id` devuelto por el backend, limpiar el draft tras el ACK de envio y mantener una copia local del mensaje enviado mientras se refresca el inbox en segundo plano.
- Se preservo `metadata_json` al mapear mensajes del Inbox para no perder contexto de respuestas interactivas.
- Se ajusto `loadConversationDetail` para marcar como leida la conversacion sin dejar el contador de no leidos desincronizado si falla el fetch del detail.
- Se corrijio la union de eventos de conversacion para aplicar `limit`/`offset` despues de fusionar los `message.status` asociados.
- Se mostro la metadata de `interactive_reply` en la burbuja del Inbox para no ocultar el contexto de respuestas interactivas.

### File List

- `README.md`
- `_bmad-output/implementation-artifacts/2-2-responder-manualmente-desde-el-inbox.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/README.md`
- `backend/app/appointments/service.py`
- `backend/app/conversations/routes.py`
- `backend/app/conversations/schemas.py`
- `backend/app/conversations/service.py`
- `backend/app/events/service.py`
- `backend/app/orders/service.py`
- `backend/app/whatsapp/routes.py`
- `backend/app/whatsapp/service.py`
- `backend/tests/test_inbox_realtime.py`
- `backend/tests/test_whatsapp_setup.py`
- `frontend/.env.example`
- `frontend/nginx.conf`
- `frontend/src/App.tsx`

### Change Log

- 2026-07-01: Agregada cobertura de regresion para envio manual real, append local del inbox y preservacion de metadata interactiva.
- 2026-07-01: Story marcada como `review` tras validar backend completo, build y lint del frontend.
- 2026-07-01: Resueltos hallazgos de review en Inbox: uso del `conversation_id` normalizado, preservacion de metadata de mensajes, actualizacion inmediata de no leidos y paginacion correcta de eventos fusionados.
