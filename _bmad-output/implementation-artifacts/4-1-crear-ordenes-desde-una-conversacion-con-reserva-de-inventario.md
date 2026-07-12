baseline_commit: ee0b2c761a0873ae7b8b682ce757a43546222c48

# Story 4.1: Crear ordenes desde una conversacion con reserva de inventario

Status: done

## Story

Como usuario autorizado del tenant,
quiero convertir una conversacion en una orden valida con reserva de stock,
para que pueda formalizar una compra sin sobreventa operativa.

El contrato de implementacion es unico: el flujo desde Inbox o IA usa `POST /orders`, que a su vez reutiliza `create_order()`; no se introduce un endpoint paralelo. La IA actua como contexto del tenant actual y la auditoria debe conservar ese origen sin inventar un actor nuevo de negocio.

## Acceptance Criteria

1. Dado que existe una intencion de compra en una conversacion, cuando el usuario o la IA inicia la creacion de una orden, entonces el backend valida tenant, contacto, conversacion activa, productos sincronizados desde Meta, disponibilidad operativa, cantidades, moneda e idempotencia, y no permite crear la orden si falta informacion critica o si existe inconsistencia de negocio.
2. Dado que la orden se crea como pendiente de pago, cuando el sistema confirma la creacion, entonces reserva la cantidad correspondiente de inventario de forma atomica en la misma transaccion y evita que otro flujo comercial consuma ese stock mientras la orden permanezca pendiente.
3. Dado que la orden queda creada, cuando el usuario revisa el historial comercial, entonces la orden queda asociada a la conversacion correspondiente y puede rastrearse desde el chat y desde el modulo de ordenes.
4. Dado que la creacion se dispara desde Inbox o desde la IA, cuando el backend publica el evento correspondiente, entonces el estado queda visible en Inbox y en Ordenes sin inventar datos, sin depender de memoria local y sin romper los flujos de mensajes, pagos o inventario.
5. Dado que la orden cambia a cancelada, pagada o expirada, cuando el backend procesa esa transicion, entonces libera o consume la reserva de inventario segun corresponda y mantiene el stock operativo consistente.

## Tasks / Subtasks

- [x] Auditar el flujo canonico de creacion de orden y reservar el punto correcto de integracion. (AC: 1, 2, 3)
  - [x] Revisar `backend/app/orders/service.py` para preservar la unica logica de validacion, reserva y persistencia.
  - [x] Confirmar que el contrato de creacion de orden desde Inbox e IA usa solo `POST /orders` y `create_order()`, sin endpoint paralelo ni segundo flujo de negocio.
  - [x] Revisar `backend/app/ai/tools.py` para no duplicar la creacion de orden desde la IA y mantener el mismo contrato de `OrderCreate`.
  - [x] Revisar `backend/app/conversations/service.py` para reutilizar el contexto de conversacion y los eventos ya emitidos sin inventar un segundo origen de verdad.
- [x] Alinear la superficie de Inbox y Ordenes con el flujo de conversion de conversacion a orden. (AC: 3, 4)
  - [x] Revisar `frontend/src/App.tsx` para exponer la accion de crear orden desde la conversacion seleccionada sin romper el layout actual de Inbox.
  - [x] Extender `ApiOrder` y `mapApiOrder()` para mostrar `conversation_id` y permitir trazabilidad directa desde la lista o detalle de ordenes.
  - [x] Reusar `OrdersPage` para reflejar la trazabilidad desde conversacion y mantener el flujo de links de pago ya existente.
  - [x] Mantener microcopy en espanol operativo y claro, sin estados ficticios.
- [x] Agregar o ajustar cobertura de regresion. (AC: 1, 2, 3, 4)
  - [x] Cubrir que la creacion de orden valida tenant, contacto, conversacion, productos, stock, cantidades y moneda.
  - [x] Cubrir que una orden valida reserva inventario y que el stock no se consume dos veces.
  - [x] Cubrir que la orden queda ligada a la conversacion y aparece en el historial de negocio.
  - [x] Cubrir que el evento `order.created` y la actualizacion de Inbox/Ordenes no rompen el flujo existente.
  - [x] Cubrir idempotencia de creacion para evitar ordenes duplicadas por reintentos o doble submit.
  - [x] Cubrir liberacion o consumo de reserva de inventario al cancelar, pagar o expirar la orden.
  - [x] Cubrir que `OrdersPage` se refresca cuando entra `order.created` para no depender de recarga manual.

## Dev Notes

### Business Context

- Esta historia cierra la conversion comercial minima del Epic 4: una conversacion con intencion de compra debe convertirse en una orden real, no en un simple registro visual.
- El backend sigue siendo la fuente de verdad para ordenes, stock e inventario reservado.
- El origen de la orden puede ser humano o IA, pero el contrato de negocio debe ser el mismo.
- La trazabilidad importa: el tenant debe poder ver la orden desde el chat y desde el modulo de ordenes sin reconstruir el contexto a mano.

### Current Code State

- `backend/app/orders/service.py` ya implementa `create_order()`, valida contacto y conversacion, exige productos activos, verifica stock con `available_units()`, bloquea moneda mixta, reserva inventario y emite `order.created`.
- `backend/app/orders/service.py` debe seguir siendo la unica entrada de negocio para crear ordenes desde Inbox o IA; el contrato de transporte sigue siendo `POST /orders`.
- `backend/app/orders/service.py` ya usa `record_audit_best_effort()` despues del commit, por lo que la auditoria no debe volver a acoplarse a la transaccion principal.
- `backend/app/orders/routes.py` ya expone `POST /orders`, `GET /orders`, `GET /orders/{order_id}`, `POST /orders/{order_id}/payment-link` y `POST /orders/{order_id}/cancel`.
- `backend/app/ai/tools.py` ya expone `create_order_tool()` y `generate_payment_link_tool()`, asi que la historia no debe introducir una segunda logica de orden para la IA.
- `backend/app/conversations/service.py` ya construye contexto comercial del hilo, registra eventos y expone `conversation_to_inbox_item()` con conteo de productos disponibles y preview de productos.
- `frontend/src/App.tsx` ya tiene `InboxPage` con acciones de IA, asignacion y agenda, y `OrdersPage` con listado y generacion de links de pago, pero no existe una accion clara para crear orden desde la conversacion seleccionada.
- `frontend/src/App.tsx` ya mapea `ApiOrder` sin `conversation_id`, aunque `OrderRead` en backend si lo expone; si la UI necesita trazabilidad visible, ese contrato debe alinearse.
- `backend/tests/test_tenant_and_orders.py` ya contiene regresiones de ordenes, inventario y pagos; esta historia debe ampliar esa cobertura, no reemplazarla.

### Critical Guardrails

- No duplicar la regla de reserva de inventario ni crear una segunda maquina de estados para ordenes.
- No crear un endpoint paralelo si `POST /orders` ya cubre el flujo; el contrato de este story es reutilizar `POST /orders` para Inbox e IA.
- No permitir que la UI confirme stock, moneda, pago o trazabilidad si el backend no lo valida.
- No romper el flujo actual de links de pago, cancelacion ni listado de ordenes.
- No introducir datos falsos en Inbox u Ordenes para "simular" la conversion.
- No relajar el aislamiento multi-tenant: `404` para recursos de otro tenant, `403` para permisos faltantes dentro del mismo tenant.

### Implementation Guidance

- Si la historia requiere accion de usuario en Inbox, ubicarla en la superficie de conversacion ya existente y mantener el layout estable.
- Reusar `OrderCreate` y el contrato de `create_order()` para cualquier flujo de usuario o de IA.
- Si se agrega trazabilidad visible, `conversation_id` debe estar presente en el listado o detalle de Ordenes para permitir salto directo al hilo.
- El contexto comercial de la conversacion debe seguir viniendo de backend; la UI solo selecciona y ejecuta.
- Si hace falta un resumen de productos para la orden, usar la data ya disponible en el backend y no un calculo propio del frontend.

### Suggested File Targets

- `backend/app/orders/service.py`
- `backend/app/orders/routes.py`
- `backend/app/ai/tools.py`
- `backend/app/conversations/service.py`
- `frontend/src/App.tsx`
- `backend/tests/test_tenant_and_orders.py`
- `backend/tests/test_inbox_realtime.py`

### Testing Requirements

- Probar creacion de orden con tenant, contacto, conversacion, items y moneda validos.
- Probar que stock insuficiente, moneda mixta, producto inactivo o recursos cross-tenant fallan con el status correcto y sin reserva parcial.
- Probar que la orden queda asociada a la conversacion y que el detalle o listado la puede rastrear.
- Probar que la reserva de inventario queda consistente y no se duplica al pasar por el flujo de orden.
- Probar que `order.created` sigue propagando el estado que Inbox y Ordenes deben reflejar.
- Si cambia la UI, validar `npm run lint` y `npm run build` en frontend.

### Project Structure Notes

- El dominio sigue siendo `backend/app/orders/` con apoyo de `inventory`, `conversations`, `ai` y `payments`.
- No mover la verdad de negocio a `frontend/src/App.tsx`.
- Si se agrega un elemento de UI nuevo, debe encajar dentro de la superficie ya existente de Inbox u Ordenes, no como una pantalla aparte.
- La trazabilidad entre chat y orden debe salir de los datos persistidos por backend, no de estado local.

### References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Epic 4, Historia 4.1 y FR053-FR065]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - secciones de Ordenes, Pagos, Inventario e Inbox]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - backend source of truth, no inventar datos, modulos de Inbox y Ordenes]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - flujo de seguimiento de pago desde el chat y trazabilidad operacional]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/frontend-implementation-brief.md` - layout de Inbox y acciones operativas]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/orders/service.py` - `create_order()`, reserva y eventos]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/orders/routes.py` - contrato HTTP actual de ordenes]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/ai/tools.py` - herramienta de creacion de orden para IA]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/conversations/service.py` - contexto de conversacion y disponibilidad operativa]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx` - `InboxPage`, `OrdersPage`, `ApiOrder`, `mapApiOrder()`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py` - regresiones de ordenes, stock y pagos]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py` - eventos y refresco de Inbox]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- 2026-07-04: Historia seleccionada automaticamente como el primer backlog en `sprint-status.yaml`: `4-1-crear-ordenes-desde-una-conversacion-con-reserva-de-inventario`.
- 2026-07-04: Se revisaron el epic 4, el PRD, la arquitectura frontend, UX de Swaflow, el servicio actual de ordenes, la ruta HTTP de ordenes, el helper de IA y la superficie actual de Inbox y Ordenes.
- 2026-07-04: Se confirmo que `create_order()` ya existe y que la historia debe centrarse en el flujo conversacional y la trazabilidad, no en reinventar la reserva de inventario.
- 2026-07-04: Se detecto que `ApiOrder` en frontend no expone `conversation_id`, aunque el backend ya lo serializa, por lo que la trazabilidad visible puede requerir ajuste de tipos/UI.
- 2026-07-04: Se implemento idempotencia por `metadata.idempotency_key`, guard de conversacion activa, accion de crear orden desde Inbox y trazabilidad de `conversation_id` en Ordenes.
- 2026-07-04: `npm run lint` y `npm run build` del frontend completaron sin errores.
- 2026-07-04: La validacion de backend quedo bloqueada por entorno sin acceso a PyPI para instalar `pytest` con `uv sync`.
- 2026-07-04: Se endurecio la idempotencia con restriccion unica por `company_id` + `idempotency_key`, validacion de productos sincronizados con Meta y liberacion de reserva al expirar una orden.
- 2026-07-04: Se ajusto la UI para que use la referencia de inventario sin filtrar stock en el cliente y se corrigio el refresco de Inbox/Ordenes al recibir eventos `order.*`.
- 2026-07-04: Se valido sintaxis del backend con `python3 -m py_compile` y se reejecuto `npm run lint`/`npm run build` con resultado correcto.
- 2026-07-04: Se levanto el entorno backend con `uv sync --extra dev` y se ejecuto `uv run pytest tests/test_tenant_and_orders.py tests/test_inbox_realtime.py -q` con 108 pruebas aprobadas.
- 2026-07-04: Se agrego migracion para `orders.idempotency_key`, bloqueo de inventario con `FOR UPDATE` y estrategia de idempotencia explicita via `metadata.idempotency_key`.
- 2026-07-04: Se elimino la deduplicacion automatica por huella del carrito para evitar que ordenes legitimas repetidas queden colapsadas.
- 2026-07-04: Se reejecuto la suite backend objetivo tras el ajuste y se mantuvieron 108 pruebas pasando.
- 2026-07-04: Se bloqueo tambien la lectura-escritura de inventario en ajustes manuales y provisiones, cerrando la ventana de carrera reportada en la revision.
- 2026-07-04: Se ejecuto la suite ampliada de backend con `tests/test_tenant_and_orders.py`, `tests/test_inbox_realtime.py` y `tests/test_superadmin_offboarding.py`: 112 pruebas aprobadas.
- 2026-07-04: Se corrigio la idempotencia de webhooks de pago para estados terminales, evitando liberar reserva de inventario dos veces en eventos `expired`.
- 2026-07-04: Se alineo el catalogo de IA y el selector de Inbox para mostrar solo productos Meta sincronizados y realmente ordenables.
- 2026-07-04: Se agregaron regresiones para el catalogo IA, el selector de Inbox y la repeticion de webhooks `expired` con `transaction_id` distinto.
- 2026-07-04: Se revalido la suite afectada con 116 pruebas aprobadas, mas `npm run lint` y `npm run build`.
- 2026-07-06: Se corrigio la validacion de conversacion cross-tenant para devolver `404`, se blindaron webhooks terminales contra estados ya cancelados, y se alinearon los helpers de IA e Inbox al subconjunto Meta-sincronizado.
- 2026-07-06: Se agregaron regresiones para conversacion cross-tenant, webhook `expired` tardio tras cancelacion, busqueda de productos Meta antes de paginar, rechazo de stock para productos no Meta y conteo de Inbox solo sobre productos ordenables.
- 2026-07-06: Se revalido la suite backend afectada con `117` pruebas aprobadas.
- 2026-07-06: Se revalido la suite ampliada de backend con `121` pruebas aprobadas, incluyendo `tests/test_superadmin_offboarding.py`.

### Completion Notes

- Se preservo el contrato unico `POST /orders` y la logica central `create_order()`.
- La UI de Inbox ahora permite crear orden con producto, cantidad e idempotencia desde la conversacion seleccionada.
- La vista de Ordenes ahora expone trazabilidad hacia la conversacion y refresca al recibir `order.created`.
- La cobertura de backend agrego idempotencia, rechazo de conversaciones cerradas, validacion de productos Meta-sincronizados y liberacion de stock al expirar.
- La UI dejo de imponer una validacion local de stock y delega la decision final al backend.
- La suite backend objetivo quedo validada con 117 tests pasando y sin regresiones en Inbox/Ordenes.
- La migracion de `orders.idempotency_key` y el bloqueo de inventario cierran los hallazgos de despliegue y concurrencia.
- El bloqueo de inventario ahora aplica tanto a ordenes como a ajustes manuales, evitando perdidas de actualizacion.
- La idempotencia de orden quedo restringida a `metadata.idempotency_key`; no se infiere automaticamente a partir del contenido del carrito.
- Se agrego cobertura para reintentos con clave explicita y para repeticion legitima sin clave, con 113 pruebas aprobadas en la suite ampliada de backend.
- El catalogo de IA y el selector de Inbox quedaron alineados al mismo subconjunto de productos Meta sincronizados que acepta `POST /orders`.
- Se reforzo la idempotencia de pagos para eventos terminales, incluyendo `expired`, evitando doble liberacion de inventario en retries con otro `transaction_id`.
- La suite ampliada quedo en 121 pruebas aprobadas tras los nuevos fixes.

### Review Findings

- [x] [Review][Decision] Clarify the order-creation contract for Inbox/IA — Resuelto: el flujo usa solo `POST /orders` y `create_order()`, sin endpoint paralelo. [lines 22-26]
- [x] [Review][Decision] Define the actor model for AI-initiated orders — Resuelto: la IA actua como contexto del tenant actual y la auditoria conserva ese origen. [line 15]
- [x] [Review][Patch] Make traceability mandatory in the frontend, not conditional — Resuelto: `conversation_id` pasa a ser obligatorio en el listado o detalle de Ordenes. [lines 17, 29-30, 55, 71]
- [x] [Review][Patch] Specify idempotency and atomic reservation behavior for duplicate submits — Resuelto: AC1 y AC2 ahora exigen idempotencia y reserva atomica. [lines 15-16, 87-90]
- [x] [Review][Patch] Specify how reserved inventory is released or finalized — Resuelto: AC5 cubre cancelacion, pago y expirada. [lines 16, 51, 63, 87-91]
- [x] [Review][Patch] Tighten Meta-sync validation wording — Resuelto: AC1 exige productos sincronizados desde Meta y validacion operativa explicita. [lines 15, 23, 49]
- [x] [Review][Patch] Explicitly require the Orders view to refresh on `order.created` — Resuelto: AC4 exige visibilidad en Inbox y Ordenes, y Testing Requirements obliga refresh de Orders. [lines 18, 36, 91]

### File List

- `backend/app/orders/service.py`
- `backend/app/orders/models.py`
- `backend/app/inventory/service.py`
- `backend/app/products/service.py`
- `backend/app/ai/runtime.py`
- `backend/app/ai/tools.py`
- `backend/app/payments/service.py`
- `backend/tests/test_tenant_and_orders.py`
- `backend/tests/test_inbox_realtime.py`
- `backend/migrations/versions/20260704_0021_orders_idempotency_key.py`
- `frontend/src/App.tsx`
- `_bmad-output/implementation-artifacts/4-1-crear-ordenes-desde-una-conversacion-con-reserva-de-inventario.md`

### Change Log

- 2026-07-04: Se implemento idempotencia de creacion de orden, guard de conversacion activa y reuso de `POST /orders` para Inbox/IA.
- 2026-07-04: Se agrego UI de creacion de orden desde Inbox y trazabilidad de conversacion en Ordenes.
- 2026-07-04: Se agregaron pruebas de idempotencia, conversacion cerrada y validacion de inventario en backend.
- 2026-07-04: Se agrego restriccion unica para idempotencia concurrente, validacion de productos Meta-sincronizados, liberacion de inventario al expirar y limpieza de validacion local de stock en frontend.
- 2026-07-04: Se agrego migracion para `idempotency_key`, bloqueo transaccional de inventario y estrategia de idempotencia explicita.
- 2026-07-04: Se resolvio el hallazgo de code review eliminando la deduplicacion automatica por carrito y reforzando la cobertura de backend.
- 2026-07-04: Se resolvieron 3 hallazgos adicionales de code review: idempotencia de `expired`, alineacion del catalogo IA y filtro del selector de Inbox.
- 2026-07-06: Se resolvieron 5 hallazgos de review adicionales: `404` para conversaciones cross-tenant, blindaje de terminales de pago, busqueda Meta antes de paginar, validacion Meta en `check_stock_tool()` y filtro Meta en el conteo de Inbox.
