baseline_commit: ee0b2c761a0873ae7b8b682ce757a43546222c48

# Story 4.5: Hacer seguimiento de links vencidos sin romper la verdad del backend

Status: done

## Story

Como usuario autorizado del tenant,
quiero que la IA pueda seguir una orden vencida sin confirmar pagos falsos,
para que pueda recuperar ventas sin comprometer inventario ni estados criticos.

El contrato de esta historia es estricto: la IA puede reabrir el dialogo comercial, pero la verdad de negocio sigue viviendo en backend. No se agrega un endpoint paralelo ni una segunda maquina de estados para pagos. Si hace falta generar un nuevo flujo de pago o agregar otro producto, debe hacerse con los servicios backend ya existentes y con trazabilidad persistente.

## Acceptance Criteria

1. Dado que un link de pago expira sin confirmacion y la conversacion sigue activa, cuando el backend detecta el estado `expired`, entonces el sistema permite un unico seguimiento comercial por IA para preguntar si el cliente desea continuar, y si corresponde puede generar un nuevo flujo de pago o agregar otro producto mediante backend.
2. Dado que se ejecuta el seguimiento de un link vencido, cuando la IA responde, entonces no puede confirmar pagos, extender vencimientos ni retener inventario por su cuenta, y solo puede continuar el flujo si el backend y las reglas del agente lo permiten.
3. Dado que el link expirado ya tuvo un seguimiento automatico, cuando llegan mas eventos o mas mensajes sin respuesta del cliente, entonces la IA no insiste nuevamente de forma automatica en V1 y como maximo ejecuta un unico seguimiento automatico por expiracion.
4. Dado que el cliente responde despues de la expiracion, cuando el sistema retoma la conversacion, entonces la IA conserva el contexto comercial del chat y puede seguir el flujo usando los servicios backend ya autorizados, sin inventar pago, stock o vencimiento.
5. Dado que la orden ya paso a `expired`, cuando el sistema reevalua el estado, entonces la reserva de inventario ya liberada no se vuelve a retener por el seguimiento, y cualquier nuevo pago solo puede nacer de un flujo nuevo generado por backend.

## Tasks / Subtasks

- [x] Definir y persistir el control de un solo seguimiento por expiracion. (AC: 1, 2, 3, 5)
  - [x] Revisar `backend/app/orders/service.py` y `backend/app/payments/service.py` para identificar el punto unico donde una orden entra en `expired` y donde debe quedar marcada la elegibilidad o consumo del seguimiento.
  - [x] Persistir el estado de seguimiento en backend, preferiblemente junto a la metadata de pago de la orden, para no depender de memoria local ni del frontend.
  - [x] Mantener la liberacion de inventario ya implementada en `expired`; este story no debe volver a tocar stock salvo para validar que no se retenga otra vez.
  - [x] Evitar crear una segunda maquina de estados: el seguimiento debe colgar del contrato de pagos/ordenes existente.
- [x] Habilitar el follow-up comercial en la ruta canonica de auto-respuesta. (AC: 1, 2, 4)
  - [x] Revisar `backend/app/whatsapp/service.py` para decidir donde inyectar el contexto de link vencido en el flujo de auto-reply ya existente.
  - [x] Revisar `backend/app/ai/runtime.py` para reforzar la regla de no invencion y permitir que el modelo reconozca el contexto de expiracion sin cambiar la verdad de negocio.
  - [x] Reusar `backend/app/ai/tools.py:create_order_tool()` y `backend/app/ai/tools.py:generate_payment_link_tool()` como las unicas vias para crear una nueva orden o regenerar un link, si el seguimiento comercial lo requiere.
  - [x] No agregar una accion de pago manual ni una confirmacion desde IA; la IA solo puede continuar el flujo, pedir aclaracion o disparar el backend autorizado.
- [x] Cubrir el comportamiento con regresiones de backend. (AC: 1, 2, 3, 4, 5)
  - [x] Agregar pruebas para el primer follow-up automatico despues de `expired`.
  - [x] Agregar pruebas para garantizar que un segundo evento o mensaje no dispare insistencia automatica.
  - [x] Probar que el seguimiento no confirma pago, no retiene inventario y no modifica el estado terminal de la orden.
  - [x] Probar que, despues de la expiracion, la IA puede continuar el flujo comercial solo a traves de los servicios backend permitidos.

## Dev Notes

### Business Context

- Esta historia existe para recuperar conversion sin romper la verdad del backend.
- El sistema debe poder seguir vendiendo despues de una expiracion, pero sin mentir sobre pagos, stock o vigencias.
- El epic 4 separa claramente la expiracion del link, la confirmacion por webhook y este seguimiento comercial posterior.
- La regla de negocio clave es simple: un link expirado puede generar un unico seguimiento automatico; no hay insistencia repetida en V1.

### Current Code State

- `backend/app/orders/service.py:update_payment_status()` ya marca `expired` y libera la reserva de inventario.
- `backend/app/payments/service.py:process_payment_webhook()` ya ignora ordenes terminales y no reabre estados cerrados.
- `backend/app/payments/contract.py` ya centraliza la deduplicacion de eventos de pago y el mapeo de estados.
- `backend/app/whatsapp/service.py:process_webhook_payload()` es el punto canonico donde una llegada de WhatsApp puede disparar `generate_auto_reply()`.
- `backend/app/ai/runtime.py:generate_auto_reply()` ya contiene reglas de no invencion, contexto comercial y control general de acciones, pero no tiene una rama explicita para links vencidos.
- `backend/app/ai/tools.py` ya expone `create_order_tool()` y `generate_payment_link_tool()`, asi que esta historia no necesita inventar un nuevo canal para crear pagos.
- `backend/tests/test_tenant_and_orders.py` ya cubre expiracion, cancelacion e idempotencia de pagos; esta historia debe extender esa cobertura con el follow-up automatico.

### What Must Change

- La deteccion de expiracion debe dejar una marca persistente que permita saber si el follow-up automatico ya ocurrio.
- El flujo de auto-reply debe reconocer ese estado persistido y, si corresponde, generar un mensaje comercial breve para continuar la venta.
- Si el cliente responde despues de la expiracion, la IA puede continuar el flujo, pero la decision de crear una nueva orden o un nuevo link debe pasar por backend.
- Cualquier accion derivada del seguimiento debe respetar la regla de no confirmacion manual de pagos.

### What Must Be Preserved

- `expired` sigue siendo un estado terminal del flujo de pago actual.
- La reserva de inventario ya liberada no debe volver a reservarse por el simple hecho de seguir conversando.
- El aislamiento por `company_id` sigue siendo obligatorio en todas las consultas.
- La IA no debe inventar confirmaciones de pago, extensiones de vigencia ni stock disponible.
- No se agrega una pantalla nueva ni un endpoint paralelo solo para este seguimiento.

### Architecture Guardrails

- No crear una nueva maquina de estados para pagos o seguimientos.
- No mover la verdad del seguimiento al frontend.
- No usar memoria local o flags efimeros para decidir si ya se insistio al cliente.
- No permitir que la IA marque un pago como confirmado por interpretacion del mensaje del cliente.
- Si se necesita un nuevo flujo de pago, este debe nacer desde backend con los servicios existentes.

### Suggested File Targets

- `backend/app/orders/service.py`
- `backend/app/payments/service.py`
- `backend/app/whatsapp/service.py`
- `backend/app/ai/runtime.py`
- `backend/app/ai/tools.py`
- `backend/tests/test_tenant_and_orders.py`
- `backend/tests/test_inbox_realtime.py`

### Testing Requirements

- Probar que la primera expiracion genera un unico seguimiento automatico.
- Probar que eventos o mensajes posteriores no disparan una nueva insistencia automatica.
- Probar que el seguimiento no cambia inventario, no confirma pago y no reabre la orden.
- Probar que la IA puede continuar el flujo comercial solo con backend autorizado cuando el cliente responde.
- Probar aislamiento cross-tenant para cualquier consulta usada por el seguimiento.

### Project Structure Notes

- Backend: el trabajo debe quedarse en `backend/app/orders/`, `backend/app/payments/`, `backend/app/whatsapp/` y `backend/app/ai/`.
- Tests: la suite base ya vive en `backend/tests/test_tenant_and_orders.py`; si hace falta un ajuste de flujo realtime, complementar con `backend/tests/test_inbox_realtime.py`.
- Frontend: no se espera cambio de UI para esta historia; la accion relevante ocurre en backend y se refleja por eventos y mensajes existentes.
- Si se agrega una nueva marca de seguimiento en metadata, debe seguir el patron ya usado por pagos e idempotencia: persistida, serializable y tenant-scoped.

## References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/sprint-status.yaml` - `development_status`, epic-4 backlog order]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Epic 4, Historia 4.5 y FR145-FR146, FR178-FR180]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - secciones de Ordenes, Pagos e IA, incluyendo expiracion y seguimiento comercial]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - backend source of truth, integraciones normalizadas y eventos durables]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/orders/service.py` - `update_payment_status()`, liberacion de inventario y estados terminales]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/payments/service.py` - `process_payment_webhook()` y rechazo de estados terminales]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/whatsapp/service.py` - `process_webhook_payload()`, `generate_auto_reply()` y flujo de auto-respuesta]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/ai/runtime.py` - contrato de salida de la IA, reglas de no invencion y uso de herramientas]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/ai/tools.py` - `create_order_tool()` y `generate_payment_link_tool()`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py` - regresiones de expiracion e idempotencia de pagos]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Se selecciono automaticamente la primera historia backlog pendiente de Epic 4: `4-5-hacer-seguimiento-de-links-vencidos-sin-romper-la-verdad-del-backend`.
- Se revisaron `sprint-status.yaml`, el epic 4, el PRD, la arquitectura frontend, el codigo actual de ordenes, pagos, WhatsApp e IA, y la historia previa 4.4 para mantener el mismo contrato de backend.
- Se confirmo que `expired` ya libera inventario y que el flujo de pagos terminales no debe reabrirse; este story se enfoca en el seguimiento comercial posterior, no en repetir la logica de estados.
- Se verifico que el punto canonico de auto-reply ya existe en `backend/app/whatsapp/service.py`, por lo que el nuevo comportamiento debe integrarse ahi y no como un flujo paralelo.
- Se implemento un follow-up automatico unico cuando la orden entra en `expired`, persistido en `Order.metadata_json.payment.expired_followup`.
- Se alineo `generate_auto_reply()` con contexto de pago vencido para que las respuestas posteriores no repitan el aviso ni inventen pagos.
- Se resolvieron los hallazgos de revision: se reserva el follow-up antes del envio para evitar duplicados y se agrego una ruta real de backend para clonar la orden expirada y emitir un link nuevo cuando el cliente quiere continuar.
- Se resolvieron los hallazgos de revision: si falla la generacion del nuevo link, la orden de recuperacion se mantiene reutilizable en estado pendiente para permitir un reintento posterior sin quedar atrapada en una orden cancelada.
- Se unifico la provenance del contexto de pago para leer la cadena expirado -> recuperacion desde la misma metadata en backend/IA, manteniendo el hilo comercial despues del recovery.
- Se resolvieron los hallazgos de revision restantes: el follow-up expirado ahora se consume tambien cuando la conversacion no puede responder, las respuestas afirmativas simples como `si`/`dale`/`ok` continúan el flujo y el branch de recovery permite llegar a productos adicionales cuando la IA los sugiere.
- Se resolvieron los hallazgos de revision finales: el detector de continuidad acepta frases naturales con puntuacion y el recovery fallido ya no emite un `ai_auto_reply` generico que prometa un link inexistente.
- Se valido la suite focal de `backend/tests/test_tenant_and_orders.py` y `backend/tests/test_inbox_realtime.py` con `146 passed`.

### Completion Notes List

- Se agrego persistencia de follow-up automatico en `Order.metadata_json.payment.expired_followup`.
- `update_payment_status()` ahora dispara un seguimiento comercial unico cuando una orden entra en `expired`.
- El follow-up usa el runtime de IA con contexto de pago vencido y cae a un texto seguro si la generacion no esta disponible.
- `generate_auto_reply()` ahora recibe contexto de pago vencido y evita repetir el aviso cuando el follow-up ya se envio.
- Se agregaron regresiones para expiracion, persistencia de metadata, unicidad del seguimiento y contexto de IA para respuestas posteriores.
- Se agrego una regresion para el flujo de recuperacion que clona la orden expirada, genera un nuevo link de pago y evita crear una segunda orden duplicada en reintentos.
- Se agrego cobertura para reintento del follow-up expirado cuando falla el envio y para recuperar el mismo flujo de pago cuando la generacion del link falla de forma transitoria.
- Se unifico la lectura de provenance del recovery para que el contexto comercial persista despues de crear una nueva orden de pago.
- Se agrego cobertura para que el follow-up expirado quede consumido incluso si la conversacion no es elegible para respuesta.
- Se agrego cobertura para respuestas afirmativas simples y para permitir que el flujo de recovery siga hacia tarjetas de producto cuando la IA propone mas opciones.
- Se ajusto el detector de continuidad para aceptar frases naturales como `si, por favor` y `necesito ayuda para seguir pagando` sin bloquearlas como soporte humano.
- Se elimino el reply generico en los casos donde el recovery no puede generar un nuevo link, evitando promesas falsas al cliente.
- Validacion ejecutada despues del ultimo ajuste: `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py backend/tests/test_inbox_realtime.py -q` con `146 passed`.

### File List

- `backend/app/orders/service.py`
- `backend/app/payments/contract.py`
- `backend/app/ai/runtime.py`
- `backend/app/whatsapp/service.py`
- `backend/tests/test_tenant_and_orders.py`
- `_bmad-output/implementation-artifacts/4-5-hacer-seguimiento-de-links-vencidos-sin-romper-la-verdad-del-backend.md`

## Change Log

- 2026-07-10: Se implemento el seguimiento automatico unico para links de pago vencidos, con persistencia en metadata de orden, contexto de IA para respuestas posteriores y cobertura de regresion.
- 2026-07-10: Se resolvieron los hallazgos de revision, endureciendo la reserva persistida del follow-up y agregando una ruta backend real para regenerar un flujo de pago desde una orden expirada.
- 2026-07-10: Se cerraron los ultimos hallazgos de revision, manteniendo la orden de recuperacion reutilizable ante fallos transitorios y unificando la provenance del contexto de pago para el hilo vencido.
- 2026-07-10: Se cerraron los ultimos hallazgos de revision restantes, consumiendo el follow-up aun en conversaciones ineligibles, aceptando afirmaciones simples para continuar y permitiendo derivacion a productos adicionales desde el recovery.
- 2026-07-10: Se cerraron los hallazgos finales de revision, reforzando la deteccion de continuidad para frases naturales y suprimiendo el reply generico cuando el recovery no logra crear un nuevo link.
- 2026-07-11: Se corrigio el conteo de mensajes procesados y se neutralizo el texto reutilizado en ramas secundarias del recovery para evitar promesas falsas.
