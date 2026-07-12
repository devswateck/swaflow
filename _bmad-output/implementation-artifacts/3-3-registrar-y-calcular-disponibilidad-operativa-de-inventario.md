---
baseline_commit: ee0b2c761a0873ae7b8b682ce757a43546222c48
---

# Story 3.3: Registrar y calcular disponibilidad operativa de inventario

Status: done

## Story

Como usuario autorizado del tenant,
quiero ver la disponibilidad base, las reservas y el stock operativo,
para que pueda evaluar con precision que productos estan realmente disponibles.

## Acceptance Criteria

1. Dado que un producto fue sincronizado desde Meta, cuando el sistema crea o actualiza su inventario local, entonces solo lo hace para productos existentes en el catalogo sincronizado y no permite inventario para productos inexistentes en Meta.
2. Dado que el inventario local existe, cuando el usuario abre la vista de inventario, entonces el sistema muestra disponibilidad base, reservas operativas y disponibilidad operativa calculada, y la disponibilidad operativa considera disponibilidad base menos reservas vigentes.
3. Dado que Meta no puede leerse o sincronizarse, cuando el sistema no tiene stock confiable, entonces advierte que la disponibilidad es incierta y evita tratar el producto como disponible sin validacion.
4. Dado que un consumidor lee inventario, cuando el backend serializa el registro, entonces expone la disponibilidad operativa calculada de forma consistente para que UI, IA y WhatsApp no repliquen la formula por su cuenta.

## Tasks / Subtasks

- [x] Auditar el contrato actual de inventario y disponibilidad operativa.
  - [x] Revisar `backend/app/inventory/service.py`, `backend/app/inventory/routes.py`, `backend/app/inventory/schemas.py`, `backend/app/products/service.py`, `backend/app/orders/service.py`, `backend/app/ai/tools.py`, `backend/app/ai/runtime.py` y `backend/app/whatsapp/service.py`.
  - [x] Confirmar que `available_units()` siga siendo la formula canonica para stock operativo.
  - [x] Identificar si la disponibilidad operativa se expone solo como helper o tambien como campo serializado del backend.
- [x] Endurecer la frontera entre inventario y productos sincronizados.
  - [x] Centralizar una comprobacion unica de "producto sincronizado con Meta" para evitar repetir la logica de mapping en varios modulos.
  - [x] Bloquear la creacion, actualizacion y auto-seed de inventario para productos sin catalogo Meta sincronizado.
  - [x] Evitar limpieza destructiva de filas legacy salvo que la migracion explicitamente lo requiera.
- [x] Exponer la disponibilidad operativa de forma consistente.
  - [x] Si el contrato de lectura lo requiere, extender `InventoryRead` con el valor calculado de disponibilidad operativa.
  - [x] Mantener la formula `quantity_available - quantity_reserved` como unica fuente de verdad.
  - [x] Alinear `list_inventory()`, `upsert_inventory()` y `adjust_inventory()` con la misma representacion de stock.
- [x] Proteger consumidores existentes y no romper el flujo comercial.
  - [x] Verificar que las ordenes sigan reservando, liberando y consumiendo inventario con la semantica actual.
  - [x] Verificar que AI y WhatsApp sigan leyendo la misma disponibilidad operativa para decidir si un producto puede ofrecerse.
  - [x] Mantener `404` cross-tenant y errores HTTP precisos para recursos ajenos o estados invalidos.
- [x] Agregar cobertura de regresion.
  - [x] Cubrir inventario creado/actualizado solo para productos sincronizados desde Meta.
  - [x] Cubrir el calculo de disponibilidad operativa y su exposicion consistente en la lectura.
  - [x] Cubrir advertencia de stock incierto cuando la sincronizacion no es confiable.
  - [x] Cubrir que el flujo de ordenes y la reserva/liberacion de inventario no se rompen.

## Dev Notes

### Business Context

- Esta historia cierra la parte de inventario del Epic 3. La sincronizacion de catalogo ya existe; aqui se amarra la lectura y el calculo de stock real.
- La regla de negocio es operativa, no cosmética: el stock util para vender es el disponible base menos la reserva vigente.
- No crear un modulo nuevo ni una fuente paralela de stock. El backend sigue siendo la fuente de verdad.
- El alcance de esta historia termina en la exposicion y calculo de inventario. El uso por IA e Inbox se consolida en la historia 3.4.

### Current Code State

- `backend/app/inventory/service.py` ya tiene:
  - `ensure_inventory_for_products()` para crear filas faltantes.
  - `list_inventory()` que hoy auto-crea filas para todos los productos del tenant antes de leer.
  - `upsert_inventory()` y `adjust_inventory()` para mutar stock base y reservas.
  - `available_units()` como formula actual de disponibilidad operativa.
- `backend/app/inventory/schemas.py` expone solo `quantity_available` y `quantity_reserved`; si el backend debe serializar disponibilidad operativa, ese contrato todavia no existe.
- `backend/app/orders/service.py` ya consume el inventario para reservar stock al crear orden y para liberar o consumir reservas al cancelar o pagar.
- `backend/app/ai/tools.py`, `backend/app/ai/runtime.py` y `backend/app/whatsapp/service.py` ya calculan disponibilidad operativa desde `quantity_available - quantity_reserved`; no duplicar esa logica con otra formula divergente.
- `backend/app/whatsapp/service.py` ya sincroniza `quantity_available` desde Meta y pone inventario en cero cuando el producto desaparece o deja de ser confiable.
- `frontend/src/App.tsx` ya muestra `Disponible real` en Inventario y Productos usando `available - reserved`; si el contrato backend cambia, esa vista debe mantenerse alineada sin inventar stock.

### Critical Guardrails

- No crear una tabla nueva para "disponibilidad". El dato derivado debe salir de `quantity_available` y `quantity_reserved`.
- No permitir que el frontend sea la fuente de verdad del stock operativo.
- No romper la reserva/liberacion/consumo que usan Ordenes, IA y WhatsApp.
- No inventar disponibilidad cuando Meta no confirmo un stock confiable.
- No eliminar de forma destructiva filas legacy sin una decision explicita; si hay que migrar, hacerlo con pruebas y sin perder trazabilidad.
- No convertir esta historia en la 3.4: aqui se calcula y se registra, no se diseña el uso conversacional completo del stock.

### Implementation Guidance

- Si hace falta una comprobacion reutilizable de producto sincronizado con Meta, centralizarla en `backend/app/products/service.py` o en una helper pequena compartida, no en cada caller.
- Si el backend expone disponibilidad operativa en la respuesta, derivarla del helper canonico o de una expresion ORM equivalente; no guardar un segundo contador persistido.
- Si la restriccion Meta-only afecta `ensure_inventory_for_products()`, conservar la operacion idempotente y limitar el cambio al alta/actualizacion de filas, no a la lectura de inventario historico.
- Mantener los mensajes visibles en espanol y con tono operacional.
- Si el contrato de `InventoryRead` cambia, revisar tambien el mapeo frontend de inventario para no desalinear la UI.

### Latest Technical Information

- SQLAlchemy 2.0.51 es la referencia actual de la documentacion oficial. Su seccion de `hybrid_property` describe atributos con comportamiento dual: evaluacion en instancia y expresion SQL a nivel de clase. Si se expone un campo derivado como disponibilidad operativa, ese patron es una opcion valida, pero una helper de servicio simple tambien es aceptable. [Source](https://docs.sqlalchemy.org/en/20/orm/extensions/hybrid.html)
- FastAPI sigue apoyandose en parametros tipados y modelos Pydantic para validacion de requests y responses. Si cambia el contrato de lectura de inventario, mantener la forma en `schemas.py` y en el response model del router, no en parsing manual. [Source](https://fastapi.tiangolo.com/tutorial/query-params/)

### Suggested File Targets

- `backend/app/inventory/service.py`
- `backend/app/inventory/schemas.py`
- `backend/app/inventory/routes.py`
- `backend/app/products/service.py`
- `backend/app/orders/service.py` solo si la validacion Meta-only requiere ajustar fixtures o guardrails compartidos
- `backend/tests/test_tenant_and_orders.py`
- `backend/tests/test_whatsapp_setup.py`
- `frontend/src/App.tsx` solo si el contrato de lectura de inventario cambia

### Testing Requirements

- Probar que solo los productos sincronizados con Meta reciben filas o actualizaciones de inventario.
- Probar que la disponibilidad operativa se calcula como `quantity_available - quantity_reserved`.
- Probar que la lectura de inventario expone el dato calculado de forma consistente si el contrato cambia.
- Probar advertencia de stock incierto cuando la sincronizacion no puede garantizar disponibilidad.
- Probar que crear, reservar, liberar y consumir inventario desde ordenes sigue funcionando con stock sincronizado.
- Probar `404` cross-tenant y errores HTTP correctos para recursos ajenos o estados invalidos.

### Project Structure Notes

- El dominio correcto para esta historia es `backend/app/inventory/`, con apoyo puntual de `backend/app/products/` y los consumidores ya existentes.
- No mover la logica a `orders`, `ai` o `whatsapp`; esos modulos deben consumir la misma fuente de verdad, no redefinirla.
- El frontend ya sabe mostrar stock calculado desde el par `quantity_available` / `quantity_reserved`; evita introducir una segunda semantica de disponibilidad.
- Conflicto detectado: varios tests existentes crean inventario sobre productos sin mapping Meta. Si la frontera Meta-only se endurece, esos fixtures deben migrar a productos sincronizados en vez de relajar la regla.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 3, Historia 3.3 y 3.4, FR044-FR052]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - seccion Productos e Inventario, FR044-FR052]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - backend source of truth, no inventar datos, modulos de Inventario y Productos]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - patrones de Inventario y estados honestos]
- [Source: `_bmad-output/implementation-artifacts/3-1-sincronizar-el-catalogo-meta-del-tenant.md` - learnings de sync, inventario y catalogo canonico]
- [Source: `_bmad-output/implementation-artifacts/3-2-visualizar-y-validar-el-catalogo-sincronizado.md` - contrato actual de Productos/Inventario y disponibilidad visible]
- [Source: `backend/app/inventory/service.py` - `ensure_inventory_for_products()`, `list_inventory()`, `upsert_inventory()`, `adjust_inventory()`, `available_units()`]
- [Source: `backend/app/inventory/routes.py` - endpoints de lectura y mutacion de inventario]
- [Source: `backend/app/inventory/schemas.py` - contrato actual de lectura y mutacion]
- [Source: `backend/app/products/service.py` - semantica de producto y frontera Meta]
- [Source: `backend/app/orders/service.py` - reserva, liberacion y consumo de inventario]
- [Source: `backend/app/ai/tools.py` y `backend/app/whatsapp/service.py` - consumidores actuales de la disponibilidad operativa]
- [Source: `backend/tests/test_tenant_and_orders.py` - regresiones de reserva, pago y stock]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- 2026-07-04: Agregado contrato `available_units` en `Inventory` y `InventoryRead`, con frontend consumiendo el dato derivado en vez de recalcularlo.
- 2026-07-04: Endurecida la frontera Meta-only para auto-seed y mutaciones de inventario; `list_inventory()` ahora filtra solo productos sincronizados.
- 2026-07-04: Validado con `./backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py -q`, `./backend/.venv/bin/python -m pytest backend/tests/test_whatsapp_setup.py -q`, `npm run lint` y `npm run build`.

### Completion Notes List

- Se expuso la disponibilidad operativa calculada como parte del contrato de inventario.
- El backend ahora usa una sola fuente de verdad para disponibilidad operativa y la comparte con IA, WhatsApp y frontend.
- La auto-creacion y mutacion de inventario quedaron restringidas a productos sincronizados con Meta.
- Se preservo el flujo de ordenes para no romper la reserva y consumo de stock existente.
- Las pruebas de regresion de inventario, ordenes y WhatsApp quedaron verdes.

### File List
- `backend/app/ai/runtime.py`
- `backend/app/inventory/models.py`
- `backend/app/inventory/schemas.py`
- `backend/app/inventory/service.py`
- `backend/app/products/service.py`
- `backend/app/whatsapp/service.py`
- `backend/tests/test_tenant_and_orders.py`
- `frontend/src/App.tsx`
- `_bmad-output/implementation-artifacts/3-3-registrar-y-calcular-disponibilidad-operativa-de-inventario.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-07-04: Implementada la disponibilidad operativa serializada y el control Meta-only para inventario, con consumo alineado en backend y frontend.
