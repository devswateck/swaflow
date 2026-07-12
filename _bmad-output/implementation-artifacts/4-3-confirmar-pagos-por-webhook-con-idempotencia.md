---
baseline_commit: ee0b2c761a0873ae7b8b682ce757a43546222c48
---

# Story 4.3: Confirmar pagos por webhook con idempotencia

Status: done

## Story

Como sistema backend del tenant,
quiero confirmar pagos unicamente con webhooks validos e idempotentes,
para que la orden cambie de estado solo cuando exista evidencia real de la pasarela.

## Acceptance Criteria

1. Dado que llega un webhook de pago valido, cuando el backend lo valida con la firma, token o secreto del proveedor, entonces actualiza el estado de la orden sin requerir confirmacion manual de IA o frontend y refleja el cambio en menos de 5 segundos bajo condiciones normales.
2. Dado que el webhook ya fue procesado, cuando llega una repeticion con la misma referencia o transaccion, entonces el sistema evita el doble procesamiento y mantiene el estado consistente.
3. Dado que una orden pasa a pagada, cuando el backend confirma el evento, entonces consume o confirma la reserva de inventario y registra el evento de venta para dashboard y auditoria.
4. Dado que una orden se cancela o expira, cuando el estado terminal se confirma, entonces libera las reservas correspondientes y registra el evento de cancelacion o expiracion.

## Tasks / Subtasks

- [x] Auditar y preservar el flujo canonico de webhook de pago. (AC: 1, 2)
  - [x] Revisar `backend/app/payments/service.py` para mantener `process_payment_webhook()` como unica entrada de negocio para confirmaciones externas.
  - [x] Revisar `backend/app/payments/contract.py` para preservar la logica de `find_order_for_payment_event()`, `payment_event_already_processed()` y `record_payment_transaction()`.
  - [x] Revisar `backend/app/orders/service.py` para mantener `update_payment_status()` como el unico punto que cambia inventario y estado de orden.
  - [x] Verificar `backend/app/payments/routes.py` para conservar las rutas actuales por proveedor y no crear un endpoint paralelo.

- [x] Blindar los estados terminales y la idempotencia operativa. (AC: 2, 3, 4)
  - [x] Confirmar que eventos repetidos con la misma `transaction_id`, referencia o `payment_link_id` queden ignorados sin volver a mutar inventario.
  - [x] Confirmar que `paid` consuma o confirme reserva una sola vez y que `expired` o `cancelled` liberen stock sin doble liberacion.
  - [x] Mantener la regla de que webhooks tardios o de proveedor equivocado no reabran ordenes terminales ni inventen estados nuevos.
  - [x] Preservar la emision de eventos `order.paid`, `order.payment_status` y `order.cancelled` para Dashboard, auditoria y realtime.

- [x] Extender o ajustar la cobertura de regresion. (AC: 1, 2, 3, 4)
  - [x] Probar webhook aprobado con `transaction_id` y `payment_reference` validos.
  - [x] Probar duplicado exacto por `transaction_id` y duplicado por referencia sin `transaction_id`.
  - [x] Probar que `paid` consume inventario y deja la reserva en cero.
  - [x] Probar que `expired` libera la reserva y que un webhook tardio despues de `cancelled` se ignora.
  - [x] Probar rechazo por proveedor no coincidente para la misma referencia.
  - [x] Si aparece un gap en validacion de firma/secreto, cubrirlo en el mismo contrato de pagos, no con logica paralela.

## Dev Notes

### Contexto de negocio

- Esta historia cierra la verdad del backend para pagos: la orden solo cambia a pagada, expirada o cancelada cuando una evidencia valida lo confirma.
- El riesgo principal no es solo marcar mal una orden, sino consumir inventario dos veces o dejar reservas vivas despues de un estado terminal.
- El webhook es la fuente de entrada para la confirmacion real; IA y frontend no pueden confirmar pagos por su cuenta.
- El epic 4 separa esta historia de la generacion de links de pago y del seguimiento comercial de links vencidos.

### Estado actual del codigo

- `backend/app/payments/service.py` ya centraliza `process_payment_webhook()`, resuelve la orden por `payment_reference` o `payment_link_id`, valida firma cuando el proveedor lo soporta y descarta eventos sin identificadores utiles.
- `backend/app/payments/contract.py` ya conserva el contrato comun de proveedores, el TTL por defecto, el tracking de transacciones procesadas y la busqueda de orden por evento.
- `backend/app/orders/service.py` ya concentra `update_payment_status()`, `_mark_order_paid()`, cancelacion y liberacion de inventario para los estados terminales.
- `backend/app/orders/service.py` ya emite `order.paid`, `order.payment_status`, `order.cancelled` y publica realtime para que Inbox y Ordenes reflejen el cambio sin estado local inventado.
- `backend/app/payments/routes.py` ya expone las rutas de webhook por proveedor actuales y delega toda la logica a `process_payment_webhook()`.
- `backend/tests/test_tenant_and_orders.py` ya contiene regresiones de idempotencia por `transaction_id`, por referencia, por proveedor equivocado y por expiracion/cancelacion tardia.
- No se espera nueva migracion ni nuevo modelo: el estado de pago y la metadata de procesados ya viven en `Order.metadata_json` y en campos existentes de `Order`.

### Que debe cambiar

- Si aparece un hueco de comportamiento, debe cerrarse en el contrato actual de pagos y ordenes, no con un segundo procesador de webhooks.
- La confirmacion debe seguir siendo backend-first: nada de confirmacion manual desde IA, frontend o automatizaciones perifericas.
- La logica debe seguir siendo idempotente por referencia y transaccion, con proteccion contra eventos repetidos y eventos tardios.
- Los estados terminales no deben reabrirse ni modificar stock si el pedido ya quedo cerrado.

### Que debe preservarse

- `process_payment_webhook()` como entrada unica de negocio para webhooks de pago.
- `update_payment_status()` como unica via para mutar inventario y estado final de la orden.
- Los eventos de negocio `order.paid`, `order.payment_status`, `order.cancelled` y `order.waiting_payment`.
- El aislamiento por `company_id` y el `404` para recursos de otro tenant.
- El manejo de secretos y firmas dentro del contrato de pagos, sin exponer credenciales en API, logs o UI.
- La consistencia de inventario: `quantity_reserved` baja al cancelar/expirar y `quantity_available` baja al pagar.

### Guardrails de arquitectura

- No crear un webhook handler nuevo si el contrato actual ya cubre el proveedor.
- No confirmar pagos desde UI, IA o n8n.
- No recalcular estados terminales en frontend.
- No introducir una segunda maquina de estados para ordenes o pagos.
- No romper la compatibilidad con los proveedores soportados por el contrato actual.

### Testing requirements

- Probar que un webhook aprobado con `transaction_id` valido procesa una sola vez.
- Probar que un webhook repetido con la misma `transaction_id` o la misma referencia no vuelve a mutar la orden.
- Probar que un `paid` consume inventario una sola vez y deja la reserva en cero.
- Probar que `expired` o `cancelled` liberan la reserva y que un evento tardio no reabre la orden.
- Probar que un webhook con proveedor no coincidente se ignora para la misma referencia.
- Probar validacion de firma o secreto cuando el proveedor y la integracion lo exijan.
- Si se toca frontend por efecto colateral, verificar `npm run lint` y `npm run build`.

### Project Structure Notes

- Backend: el foco debe quedarse en `backend/app/payments/`, `backend/app/orders/` y `backend/tests/`.
- `backend/app/payments/service.py` es el punto de orquestacion; `backend/app/orders/service.py` es el punto de mutacion de estado de negocio.
- `backend/app/payments/contract.py` contiene la deduplicacion, resolucion de orden y contrato de adaptadores.
- No se espera nueva pantalla ni nuevo router de frontend para esta historia; la UI ya debe reaccionar a los eventos que emite backend.

### Review Findings

- [x] [Review][Patch] Missing webhook authentication for `mercado_pago` and `aval_pay` [backend/app/payments/routes.py:45-69] — Resuelto con validacion de firma `X-SwaFlow-Signature` y verificacion HMAC contra el secreto de la integracion antes de mutar la orden.

### References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/sprint-status.yaml` - `development_status`, epic-4 backlog order]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Epic 4, Historia 4.3 y FR058-FR065, FR145-FR146, FR153-FR154, FR167-FR169, FR174, FR178-FR180]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - secciones de Ordenes, Pagos e Integraciones, NFR-008, NFR-017, NFR-020, NFR-022, NFR-023, NFR-025, NFR-036]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - backend source of truth, eventos realtime y no inventar datos]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - copy operacional de pago pendiente, expiracion y seguimiento]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/payments/service.py` - `process_payment_webhook()` y flujo de validacion/idempotencia]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/payments/contract.py` - contrato de proveedor, deduplicacion y busqueda por evento]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/orders/service.py` - `update_payment_status()`, `_mark_order_paid()`, `cancel_order()`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/payments/routes.py` - rutas publicas de webhook por proveedor]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py` - regresiones de webhook, idempotencia y estados terminales]

## Change Log

- 2026-07-08: Se agrego soporte de estado terminal `cancelled` para webhooks de pago, con liberacion de reservas, evento `order.cancelled` y auditoria.
- 2026-07-08: Se agregaron regresiones para firma invalida de Wompi, cancelacion/voided por webhook y cierre de duplicados de expiracion/cancelacion.
- 2026-07-08: Se agrego autenticacion HMAC para webhooks de `mercado_pago` y `aval_pay` con validacion de firma antes de procesar la orden.
- 2026-07-08: Se valido `APP_ENV=development ./.venv/bin/python -m pytest tests/test_tenant_and_orders.py -q` y `APP_ENV=development ./.venv/bin/python -m pytest tests/test_inbox_realtime.py -q`.
- 2026-07-08: Se valido `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py -q` y `backend/.venv/bin/python -m pytest backend/tests/test_inbox_realtime.py -q`.

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Se selecciono automaticamente la primera historia backlog del sprint: `4-3-confirmar-pagos-por-webhook-con-idempotencia`.
- Se releyeron el sprint status, el epic 4, la historia 4.2, la historia 4.1, el PRD, la arquitectura frontend, el spine UX y el codigo actual de pagos/ordenes.
- Se confirmo que la mayor parte del contrato de webhook e idempotencia ya existe en backend; el foco de esta historia debe ser preservarlo, endurecerlo y cubrirlo con regresiones, no duplicarlo.
- Se verifico que `process_payment_webhook()` delega en `update_payment_status()` y que el estado terminal del pedido ya se concentra en `backend/app/orders/service.py`.
- Se ajusto `update_payment_status()` para que `cancelled` y `voided` liberen reservas y publiquen `order.cancelled`, manteniendo `expired` como estado separado.
- Se agregaron pruebas para rechazo de checksum invalido de Wompi y para cancelacion terminal por webhook.
- Se agregaron pruebas para firma ausente en `mercado_pago` y `aval_pay`, manteniendo el webhook sin mutacion cuando la autenticacion falla.
- Se valido la bateria focal de pagos y luego la suite completa de `tests/test_tenant_and_orders.py` y `tests/test_inbox_realtime.py` con `APP_ENV=development`.

### Completion Notes List

- Contexto de implementacion preparado para desarrollo.
- La historia se redacto para evitar reinvencion del flujo de webhooks y para mantener el backend como fuente de verdad.
- El alcance se concentro en idempotencia, estados terminales, inventario y pruebas de regresion.
- La implementacion quedo lista para review con estado terminal `cancelled` soportado por webhook, guardrails de firma y cobertura de regresion actualizada.

### File List

- `_bmad-output/implementation-artifacts/4-3-confirmar-pagos-por-webhook-con-idempotencia.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/app/orders/service.py`
- `backend/tests/test_tenant_and_orders.py`
