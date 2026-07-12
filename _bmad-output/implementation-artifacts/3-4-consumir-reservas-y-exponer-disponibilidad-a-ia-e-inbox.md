# Story 3.4: Consumir reservas y exponer disponibilidad a IA e Inbox

Status: done

## Story

Como usuario del tenant,
quiero que la disponibilidad real controle lo que la IA y el Inbox pueden ofrecer,
para que no se generen ventas ni recomendaciones sobre stock inexistente.

## Acceptance Criteria

1. Dado que una orden reserva inventario, cuando la reserva queda activa, entonces la disponibilidad operativa se reduce en consecuencia usando la fuente de verdad del backend, y el cambio queda visible para los consumidores que leen stock.
2. Dado que una orden se cancela, expira o pasa a un estado terminal que libera stock, cuando el backend libera la reserva, entonces la disponibilidad operativa vuelve a calcularse sin esa reserva y el estado queda consistente en backend.
3. Dado que una orden se confirma como pagada, cuando el backend consume o confirma la reserva, entonces el inventario refleja el consumo final y la disponibilidad operativa se actualiza sin duplicar la formula en otro modulo.
4. Dado que la IA o el Inbox quieren ofrecer un producto, cuando consultan la disponibilidad, entonces solo pueden usar la disponibilidad operativa validada y no pueden ofrecer productos no sincronizados o con disponibilidad incierta.
5. Dado que un producto no tiene stock operativo positivo, cuando la IA o WhatsApp intentan construir recomendaciones o cards, entonces el sistema lo trata como no disponible y devuelve un mensaje o fallback coherente, sin inventar disponibilidad.

## Tasks / Subtasks

- [x] Auditar y consolidar la lectura canonica de disponibilidad operativa. (AC: 1, 2, 3, 4)
  - [x] Revisar `backend/app/inventory/models.py`, `backend/app/inventory/service.py` y `backend/app/orders/service.py` para confirmar que `available_units` sigue siendo la formula unica de stock operativo.
  - [x] Verificar que ningun consumidor nuevo vuelva a calcular `quantity_available - quantity_reserved` por su cuenta si puede usar el helper o el hybrid property.
  - [x] Preservar el boundary Meta-only de la historia 3.3: la disponibilidad solo existe para inventario valido y sincronizado.
- [x] Alinear consumidores de IA y WhatsApp con la misma disponibilidad validada. (AC: 4, 5)
  - [x] Revisar `backend/app/ai/runtime.py` para que el contexto de catalogo siga filtrando por disponibilidad real y marque claramente productos no ofrecibles.
  - [x] Revisar `backend/app/ai/tools.py` para que `search_products_tool()` y `check_stock_tool()` sigan devolviendo solo disponibilidad validada y sin divergir en el conteo.
  - [x] Revisar `backend/app/whatsapp/service.py` para que tarjetas, fallback y resolucion de productos disponibles sigan usando la misma disponibilidad operativa.
- [x] Mantener consistencia del ciclo de reserva, liberacion y consumo. (AC: 1, 2, 3)
  - [x] Confirmar que `create_order`, `cancel_order` y `_mark_order_paid` mantienen la reserva y el consumo de inventario sin romper idempotencia ni estados terminales.
  - [x] Si se necesita exponer un mensaje explicito de stock insuficiente o incierto, hacerlo desde backend con mensajes operacionales en espanol, no desde calculos dispersos en frontend.
  - [x] Preservar errores HTTP precisos y el aislamiento cross-tenant `404` donde ya existe.
- [x] Agregar o ajustar regresion automatizada sobre disponibilidad consumible. (AC: 1, 2, 3, 4, 5)
  - [x] Cubrir que la reserva activa reduce la disponibilidad operativa y que la cancelacion/liberacion la restaura.
  - [x] Cubrir que el pago consume la reserva y deja el stock final consistente.
  - [x] Cubrir que IA y WhatsApp no ofrecen productos sin stock operativo positivo ni productos no sincronizados.
  - [x] Cubrir que el conteo expuesto por herramientas y contexto de catalogo no diverge del helper canonico.

## Dev Notes

### Business Context

- Esta historia cierra el lado consumidor del Epic 3: la historia 3.3 definio y expuso el stock operativo; aqui se asegura que IA, WhatsApp e Inbox solo operen sobre esa verdad validada.
- La regla de negocio es operativa, no cosmetica: un producto con reserva activa no debe ser ofrecido como disponible si la reserva ya consume su stock util.
- El backend sigue siendo la fuente de verdad para ordenes, pagos, inventario y estados criticos; la IA y el frontend solo leen y actuan sobre lo que backend autoriza.

### Current Code State

- `backend/app/inventory/models.py` ya expone `Inventory.available_units` como `hybrid_property` con expresion SQL, por lo que es apta para filtros y para evaluacion en instancia.
- `backend/app/inventory/service.py` ya centraliza `available_units(inventory)` y los flujos de lectura/mutacion de inventario.
- `backend/app/orders/service.py` ya usa inventario para reservar al crear orden, liberar al cancelar y consumir al marcar pagado; el punto de riesgo es no romper esa semantica ni duplicar reglas.
- `backend/app/ai/runtime.py` ya construye el contexto de catalogo con `available_units(inventory)` y marca los productos sin inventario como no ofrecibles.
- `backend/app/ai/tools.py` ya devuelve disponibilidad validada en `search_products_tool()` y `check_stock_tool()`.
- `backend/app/whatsapp/service.py` ya filtra cards, fallback y resolucion de productos por `Inventory.available_units > 0` y por `available_units(inventory) > 0`.
- `backend/tests/test_tenant_and_orders.py` ya contiene regresiones de inventario, ordenes, IA y WhatsApp; esta historia debe extenderlas, no reemplazarlas.
- `frontend/src/App.tsx` ya muestra disponibilidad real en Inventario y Productos; no introducir una segunda semantica visual de stock en la UI.

### Critical Guardrails

- No crear una segunda formula de disponibilidad.
- No persistir un contador derivado nuevo para stock operativo.
- No permitir que IA, WhatsApp o Inbox inventen stock disponible cuando el backend no lo valida.
- No romper las reservas al cancelar, expirar o cobrar una orden.
- No relajar el boundary Meta-only de inventario y productos sincronizados.
- No convertir el frontend en fuente de verdad de disponibilidad.

### Implementation Guidance

- Si se necesita reutilizar disponibilidad en consultas ORM, preferir `Inventory.available_units` sobre expresiones inline repetidas.
- Si se requiere un cambio en el contrato serializado, ajustar `schemas.py` y el `response_model` de la ruta correspondiente, no un dict manual disperso.
- Si el cambio afecta un campo derivado en SQLAlchemy, el patron correcto es `hybrid_property` con expresion de clase; la documentacion oficial de SQLAlchemy 2 soporta ese caso.
- Si un consumidor necesita texto de fallback, usar lenguaje operacional corto en espanol: "sin disponibilidad confirmada", "no ofrecer" o equivalente.
- Mantener la logica de no ofrecimiento en backend; la UI solo representa el resultado.

### Latest Technical Information

- SQLAlchemy 2.0.51 documenta `hybrid_property` como una forma de definir comportamiento distinto a nivel de instancia y de clase. Es el patron adecuado para una propiedad derivada como `available_units` cuando se necesita evaluacion Python y expresion SQL con la misma fuente de verdad. [Source](https://docs.sqlalchemy.org/en/20/orm/extensions/hybrid.html)
- FastAPI usa `response_model` para validar, documentar y filtrar la salida de un endpoint. Si esta historia toca algun contrato de lectura de stock, el cambio debe vivir en el modelo de respuesta y en la ruta, no solo en la logica de servicio. [Source](https://fastapi.tiangolo.com/tutorial/response-model/)
- Pydantic sigue siendo la capa de modelado y serializacion para los contratos de API del backend; cualquier campo derivado nuevo debe mantenerse tipado y serializable en `BaseModel` para evitar respuestas ambiguas. [Source](https://docs.pydantic.dev/latest/concepts/models/)

### Suggested File Targets

- `backend/app/inventory/models.py`
- `backend/app/inventory/service.py`
- `backend/app/orders/service.py`
- `backend/app/ai/runtime.py`
- `backend/app/ai/tools.py`
- `backend/app/whatsapp/service.py`
- `backend/tests/test_tenant_and_orders.py`
- `backend/tests/test_whatsapp_setup.py`
- `backend/tests/test_inbox_realtime.py`
- `frontend/src/App.tsx` solo si aparece una necesidad real de reflejar disponibilidad validada en una superficie visible del inbox o del producto; no introducir UI nueva por inercia

### Testing Requirements

- Probar que una reserva activa reduce la disponibilidad operativa visible por `available_units`.
- Probar que cancelar o expirar una orden libera la reserva y restaura la disponibilidad.
- Probar que marcar una orden como pagada consume la reserva y deja el stock consistente.
- Probar que IA y WhatsApp filtran u ofrecen solo productos con disponibilidad operativa positiva.
- Probar que productos sin sincronizacion Meta o con stock incierto no se ofrecen como disponibles.
- Probar que no aparece una segunda formula divergente en servicios, herramientas o contexto de catalogo.
- Probar 404 cross-tenant y errores HTTP precisos para recursos ajenos o estados invalidos.

### Project Structure Notes

- El dominio principal sigue siendo `backend/app/inventory/` con consumidores puntuales en `orders`, `ai` y `whatsapp`.
- No mover la responsabilidad de stock a `frontend/src/App.tsx`; el frontend solo consume el resultado ya validado por backend.
- Si se ajusta un contrato serializado, hacerlo en `schemas.py` y en la ruta del dominio correspondiente para mantener FastAPI/Pydantic alineados.
- No introducir una tabla nueva ni un service nuevo para "availability"; esta historia debe reutilizar el inventario existente.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 3, Historia 3.4 y FR049-FR052]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - secciones Productos e Inventario, IA, Inbox y FR045-FR052, FR103-FR104, FR118]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - backend source of truth, no inventar datos, modulos de Inbox y Inventario]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - Inbox, stock, cola de atencion y mensajes honestos]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/frontend-implementation-brief.md` - cola de atencion, low/sin stock y rail de contexto]
- [Source: `_bmad-output/implementation-artifacts/3-3-registrar-y-calcular-disponibilidad-operativa-de-inventario.md` - `available_units`, Meta-only inventory y learnings previos]
- [Source: `backend/app/inventory/models.py` - `Inventory.available_units`]
- [Source: `backend/app/inventory/service.py` - `available_units()`, `list_inventory()`, `upsert_inventory()`, `adjust_inventory()`]
- [Source: `backend/app/orders/service.py` - `create_order`, `cancel_order`, `_mark_order_paid`]
- [Source: `backend/app/ai/runtime.py` - contexto de catalogo y filtros de disponibilidad]
- [Source: `backend/app/ai/tools.py` - herramientas de busqueda y chequeo de stock]
- [Source: `backend/app/whatsapp/service.py` - cards, fallback y sync de catalogo/inventario]
- [Source: `backend/tests/test_tenant_and_orders.py` - regresiones de inventario, AI y WhatsApp]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- 2026-07-04: Historia creada a partir de `epics.md`, `prd.md`, `architecture.md`, UX de Swaflow, la historia 3.3 y el codigo actual de inventario/AI/WhatsApp/ordenes.
- 2026-07-04: Se confirmo que `Inventory.available_units` y `available_units()` ya son la fuente canonica de stock operativo; la historia debe preservar esa unica semantica.
- 2026-07-04: Se corrigio la oferta de cards de WhatsApp para rechazar productos sin stock operativo confirmado y para usar `available_units(inventory)` en el caption.
- 2026-07-04: Se expuso disponibilidad operativa en Inbox con `available_product_count` y `available_products_preview`, usando stock validado del backend.
- 2026-07-04: Se ajusto la regresion de Inbox para reflejar la reserva creada por `create_order()` y validar la disponibilidad restante real.
- 2026-07-04: Validacion final ejecutada: `./backend/.venv/bin/pytest backend/tests/test_whatsapp_setup.py backend/tests/test_inbox_realtime.py -q`.

### Completion Notes List

- Se corrigio la oferta de productos en WhatsApp para bloquear cards sobre stock no confirmado.
- Se elimino la recomputacion inline del stock en el caption y se reutilizo `available_units(inventory)`.
- El Inbox ahora expone conteo y preview de productos disponibles desde backend, sin inventar stock en la UI.
- La regresion de Inbox quedo alineada con la reserva generada por `create_order()` y valida la disponibilidad restante real.
- Validacion final verde en backend: `31 passed`.

### File List

- `backend/app/conversations/schemas.py`
- `backend/app/conversations/service.py`
- `backend/app/whatsapp/service.py`
- `backend/tests/test_inbox_realtime.py`
- `backend/tests/test_whatsapp_setup.py`
- `frontend/src/App.tsx`
- `_bmad-output/implementation-artifacts/3-4-consumir-reservas-y-exponer-disponibilidad-a-ia-e-inbox.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-07-04: Se resolvieron los hallazgos de review para WhatsApp, caption de producto y exposicion de disponibilidad en Inbox.
- 2026-07-04: Se actualizo la regresion de Inbox para reflejar la reserva real creada por el pedido.
