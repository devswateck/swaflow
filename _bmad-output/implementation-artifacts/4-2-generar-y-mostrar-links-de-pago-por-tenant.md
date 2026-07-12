---
baseline_commit: ee0b2c761a0873ae7b8b682ce757a43546222c48
---

# Story 4.2: Generar y mostrar links de pago por tenant

Status: done

## Story

Como usuario autorizado del tenant,
quiero generar links de pago con una expiracion controlada,
para que el cliente pueda completar el pago con la pasarela configurada.

## Acceptance Criteria

1. Dado que existe una orden lista para pago, cuando el sistema solicita el link a la pasarela configurada del tenant, entonces crea el enlace usando el adaptador autorizado para ese tenant y conserva referencia de pago, link, estado, total, moneda y fecha de vencimiento cuando aplique.
2. Dado que el tenant tiene configurada una expiracion de links, cuando se genera un nuevo link de pago, entonces el sistema aplica la expiracion definida por el admin y usa 120 minutos por defecto si no existe configuracion personalizada.
3. Dado que el usuario revisa la orden, cuando observa la informacion de pago, entonces el sistema muestra el estado y la referencia de forma entendible y no expone secretos ni credenciales de la pasarela.
4. Dado que la orden ya tiene link generado, cuando el usuario vuelve a abrirla o refresca la vista, entonces el frontend muestra el mismo `payment_link`, `payment_reference` y `payment_expires_at` persistidos por backend, sin recalcular vencimientos localmente.
5. Dado que la pasarela configurada no esta activa o no tiene credenciales validas, cuando se intenta generar el link desde backend, entonces el sistema responde con un error explicito y no inventa un link operativo.

## Tasks / Subtasks

- [x] Auditar y preservar el contrato canonico de generacion de links. (AC: 1, 2, 5)
  - [x] Revisar `backend/app/orders/service.py` para mantener `generate_payment_link()` como unica entrada de negocio para este flujo.
  - [x] Verificar `backend/app/payments/contract.py` y `backend/app/payments/providers/wompi.py` para que el link siga saliendo con referencia, `link_id` y `expires_at` persistibles.
  - [x] Confirmar que la expiracion por defecto siga siendo 120 minutos y que la configuracion personalizada del tenant se respete antes de publicar el link.
  - [x] Asegurar que el flujo no introduzca confirmacion de pago, consumo de inventario ni logica de webhook; eso pertenece a la historia 4.3.
- [x] Validar la superficie de Ordenes e Integraciones. (AC: 1, 2, 3, 4)
  - [x] Revisar `frontend/src/App.tsx` para mantener la lectura de `payment_link`, `payment_reference`, `payment_status` y `paymentExpiresAt` desde backend.
  - [x] Confirmar que `OrdersPage` muestre el link y el vencimiento persistidos, y que el copy/estado en espanol siga siendo honesto.
  - [x] Mantener `IntegrationsPage` como fuente de configuracion del TTL de links (`payment_link_ttl_minutes`) sin duplicar reglas en frontend.
  - [x] Evitar introducir calculos de vencimiento en UI: la fecha de expiracion debe venir del backend o de la metadata persistida.
- [x] Cubrir regresion y contrato de expiracion. (AC: 1, 2, 3, 5)
  - [x] Agregar o ajustar pruebas para TTL personalizado y TTL por defecto.
  - [x] Probar que una orden con link generado cambia a `waiting_payment` y mantiene la referencia/link persistidos.
  - [x] Probar que un tenant cross-company no puede generar ni leer el link de otra empresa.
  - [x] Probar que la UI no expone credenciales ni secretos de pasarela.

## Dev Notes

### Contexto de negocio

- Esta historia hace visible el paso comercial entre una orden creada y el pago del cliente.
- El valor de negocio es operacion real, no simulacion: el tenant necesita link, referencia y vencimiento para cobrar con la pasarela configurada.
- El epic 4 separa claramente esta historia de la confirmacion por webhook y del seguimiento de links vencidos.
- La experiencia de usuario debe ser honesta: si no hay pasarela activa o configuracion valida, no se debe presentar un link como si existiera.

### Estado actual del codigo

- `backend/app/orders/service.py` ya implementa `generate_payment_link()` y persiste `payment_provider`, `payment_reference`, `payment_link`, `payment_status`, metadata de expiracion y el evento `order.waiting_payment`.
- `backend/app/orders/routes.py` ya expone `POST /orders/{order_id}/payment-link` y devuelve `PaymentLinkRead`.
- `backend/app/payments/contract.py` ya centraliza el contrato del adaptador, la TTL por defecto de 120 minutos y la validacion de integracion de pagos.
- `backend/app/payments/providers/wompi.py` ya construye el link real de Wompi con `single_use`, `amount_in_cents` y `expires_at`.
- `frontend/src/App.tsx` ya tiene `OrdersPage` con accion de generar link, copia del link y lectura de vencimiento desde `order.metadata_json.payment.expires_at`.
- `frontend/src/App.tsx` ya expone la configuracion de pasarela en `IntegrationsPage`, incluyendo `payment_link_ttl_minutes`.
- `backend/tests/test_tenant_and_orders.py` ya contiene regresiones de TTL personalizado y TTL por defecto para links de pago.

### Que debe cambiar

- Si aparece un hueco de comportamiento, debe cerrarse en el contrato actual, no con un flujo paralelo.
- La validacion de expiracion y proveedor activo debe seguir siendo backend-first.
- La UI debe reflejar el estado persistido y no recalcular ni inventar fechas.
- No se debe mezclar esta historia con la confirmacion de pago por webhook ni con el seguimiento de links vencidos.

### Que debe preservarse

- `POST /orders/{order_id}/payment-link` como contrato unico para generar links desde frontend o automatizaciones autorizadas.
- El uso de `api<T>()` en frontend y el estado `swaflow_token` en Zustand.
- El aislamiento multi-tenant por `company_id` y el `404` para recursos de otra empresa.
- Los secretos cifrados en `CompanyIntegration.credentials_encrypted`; no exponer `credentials`, `secret_token` ni llaves privadas en UI, logs o respuestas.
- Los eventos de negocio `order.waiting_payment` y `order.payment_status` ya definidos por backend.

### Guardrails de arquitectura

- No introducir un segundo generador de links.
- No mover la fuente de verdad de vencimiento al frontend.
- No crear un endpoint nuevo si `POST /orders/{order_id}/payment-link` ya cubre el caso.
- No confirmar pagos, liberar inventario ni marcar ventas como cerradas desde esta historia.
- No usar mocks operativos en producción; `mock` solo sirve como fallback local o de pruebas cuando el flujo lo permita.

### Testing requirements

- Probar expiracion por defecto de 120 minutos y expiracion personalizada desde integracion activa.
- Probar que el link persiste en la orden con referencia, provider y `expires_at` sin perder el estado `waiting_payment`.
- Probar que el backend rechaza estados no validos para generar link y que no filtra credenciales.
- Probar aislamiento cross-tenant para lectura y generacion de links.
- Si se ajusta UI, verificar `npm run lint` y `npm run build`.

### Project Structure Notes

- Backend: el dominio principal sigue siendo `backend/app/orders/` con apoyo de `backend/app/payments/` e `backend/app/integrations/`.
- Frontend: la superficie afectada debe seguir concentrada en `frontend/src/App.tsx` y utilidades relacionadas; no abrir un router nuevo.
- Tests: extender `backend/tests/test_tenant_and_orders.py`; no duplicar fixtures ni crear una suite aislada para este caso.
- La historia no necesita nuevos modelos ni nuevas migraciones.

## Change Log

- 2026-07-06: Se endurecio `generate_payment_link()` para exigir integracion de pagos activa y validada antes de crear el link, eliminando el fallback inventado.
- 2026-07-06: Se agregaron regresiones para rechazo sin integracion activa y se alinearon las pruebas existentes a una integracion de pagos explicita.
- 2026-07-06: Se cerro el hallazgo de review que permitia proveedores locales operativos en produccion; el contrato ahora rechaza la creacion y generacion de links con `mock`, `mercado_pago` y `stripe` cuando `app_env=production`.
- 2026-07-06: Se valido frontend build/lint y la suite backend relevante de `tenant_and_orders` y `inbox_realtime`.
- 2026-07-06: Se ajusto el contrato para que solo `wompi` y `mock` queden como proveedores de integracion soportados; `mercado_pago` y `stripe` quedaron fuera de la superficie de tenant y de la UI de pagos.
- 2026-07-06: Se valido `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py -q`, `npm run lint` y `npm run build`.
- 2026-07-06: Se cerro la ruta publica de webhook legado de Mercado Pago y la UI de integraciones quedo apuntando solo a Wompi y Mock.
- 2026-07-06: Se valido nuevamente `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py -q`, `npm run lint` y `npm run build` tras el cierre del webhook legado.

## References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/sprint-status.yaml` - `development_status`, epic-4 backlog order]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Epic 4, Historia 4.2, FR153-FR154 y Epic 4 scope]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - secciones de Ordenes, Pagos e Integraciones]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - backend source of truth, no inventar datos, patrones de modulos]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - patrones de Ordenes, pago pendiente y copy operacional]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/orders/service.py` - `generate_payment_link()`, `cancel_order()`, `update_payment_status()`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/orders/routes.py` - `POST /orders/{order_id}/payment-link`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/payments/contract.py` - TTL por defecto, contrato de adaptador y validacion de integracion]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/payments/providers/wompi.py` - construccion del link, `expires_at`, `single_use`, `amount_in_cents`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx` - `OrdersPage`, `IntegrationsPage`, `PaymentLinkRead`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py` - cobertura de TTL personalizado y default para links de pago]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- 2026-07-06: Se identifico como primera story backlog del sprint la 4.2 `generar-y-mostrar-links-de-pago-por-tenant`.
- 2026-07-06: Se revisaron `sprint-status.yaml`, `epics.md`, PRD, arquitectura frontend, UX spine, `orders/service.py`, `orders/routes.py`, `payments/contract.py`, `payments/providers/wompi.py`, `IntegrationsPage` y `OrdersPage`.
- 2026-07-06: Se confirmo que el backend ya tiene el contrato canonico de generacion de links y que la story debe preservar ese flujo, no duplicarlo.
- 2026-07-06: Se confirmo que la UI ya lee `payment_link`, `payment_reference` y `expires_at`, pero la story debe blindar que la expiracion y el estado provengan del backend.
- 2026-07-06: Se implemento la validacion estricta de integracion activa en `generate_payment_link()` y se elimino el fallback de link inventado.
- 2026-07-06: Se ejecuto `npm run build`, `npm run lint`, `python3 -m py_compile backend/app/orders/service.py backend/tests/test_tenant_and_orders.py`, `UV_CACHE_DIR=/private/tmp/uv-cache uv sync --extra dev` en `backend/`, `UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest tests/test_tenant_and_orders.py -q` y `UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest tests/test_inbox_realtime.py -q`.
- 2026-07-06: Se corrigio el hallazgo de review que permitia proveedores locales operativos en produccion y se agregaron regresiones para `mock`, `mercado_pago` y `stripe`.
- 2026-07-06: Se valido `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py -q` con la cobertura de pagos actualizada.
- 2026-07-06: Se valido nuevamente `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py -q` con 107 pruebas aprobadas.
- 2026-07-07: Se alineo el alcance de proveedores activos a `mercado_pago`, `wompi` y `aval_pay`, dejando `mock` solo para local o pruebas.
- 2026-07-07: Se ajustaron backend, frontend y pruebas para exponer sandbox de Mercado Pago y Aval Pay, y se valido `backend/tests/test_tenant_and_orders.py`, `npm run lint` y `npm run build`.
- 2026-07-07: Se cerraron los hallazgos de review sobre la superficie de pagos y la historia quedo lista para cierre.
- 2026-07-08: Se corrigieron los hallazgos de review pendientes: los webhooks de Mercado Pago y Aval Pay ahora aceptan estados reales y la activacion de integracion valida credenciales parseables y completas.
- 2026-07-08: Se valido `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py -q` con 110 pruebas aprobadas.

### Completion Notes List

- Story implementada y preparada para review.
- `generate_payment_link()` ahora exige una integracion de pagos activa y valida antes de crear un link.
- `mercado_pago`, `wompi` y `aval_pay` quedaron como proveedores soportados para integraciones de tenant; `mock` sigue limitado a local o pruebas y `stripe` permanece fuera de la superficie soportada.
- `mock` quedo restringido a entornos locales o de prueba; en produccion la integracion y la generacion de links responden `422`.
- Se agrego cobertura para rechazo sin integracion activa y se ajustaron los tests existentes a una integracion explicita.
- Se agregaron regresiones para bloquear `mock` en produccion y para rechazar `mercado_pago` y `stripe` como proveedores no soportados.
- La UI de Integraciones ahora expone `Mercado Pago`, `Wompi` y `Aval Pay` y muestra sus endpoints de sandbox junto con el webhook de `mock` solo en entornos no productivos.
- Los webhooks de Mercado Pago y Aval Pay ahora procesan estados reales del proveedor, y la activacion de integraciones rechaza credenciales incompletas o no parseables.

### File List

- `_bmad-output/implementation-artifacts/4-2-generar-y-mostrar-links-de-pago-por-tenant.md`
- `backend/app/payments/contract.py`
- `backend/app/payments/routes.py`
- `backend/app/payments/schemas.py`
- `backend/app/orders/service.py`
- `backend/tests/test_tenant_and_orders.py`
- `frontend/src/App.tsx`
