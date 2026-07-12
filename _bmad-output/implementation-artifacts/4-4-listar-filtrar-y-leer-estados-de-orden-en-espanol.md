---
baseline_commit: ee0b2c761a0873ae7b8b682ce757a43546222c48
---

# Story 4.4: Listar, filtrar y leer estados de orden en espanol

Status: done

## Story

Como usuario autorizado del tenant,
quiero revisar las ordenes por fecha, estado, cliente, producto y conversacion, con sus estados visibles en espanol,
para que pueda dar seguimiento comercial rapido y entendible sin perder el contexto del tenant.

## Acceptance Criteria

1. Dado que el usuario abre Ordenes, cuando se carga la lista, entonces el sistema muestra las ordenes de la mas reciente a la mas antigua y las agrupa visualmente por mes y anio.
2. Dado que el usuario aplica filtros por rango de fechas, estado, cliente/contacto, producto o usuario/conversacion cuando exista relacion, cuando se ejecuta la consulta, entonces el backend devuelve solo las ordenes del tenant que cumplen los filtros y la UI conserva las acciones operativas existentes.
3. Dado que el usuario ve el estado de una orden, cuando se renderiza en la interfaz, entonces el estado de orden y el estado de pago se presentan en espanol con etiquetas estables, mientras el backend sigue usando codigos tecnicos internos.
4. Dado que una orden tiene conversacion asociada o link de pago, cuando aparece en la lista, entonces el usuario puede abrir el chat y ver la referencia, el link y el vencimiento persistidos sin recalcular nada en frontend.
5. Dado que no hay datos para un filtro o la consulta no devuelve resultados, cuando se muestra la vista, entonces la UI presenta un estado vacio honesto y no inventa ordenes.

## Tasks / Subtasks

- [x] Extender el contrato de listado de ordenes sin crear un endpoint paralelo. (AC: 1, 2, 5)
  - [x] Revisar `backend/app/orders/service.py` y `backend/app/orders/routes.py` para ampliar `GET /orders` con filtros de rango de fechas, estado, contacto, producto y conversacion, manteniendo `company_id` como unico contexto valido.
  - [x] Preservar el orden descendente por `created_at` y el paginado existente; los filtros deben acotar el resultado, no cambiar el contrato base del listado.
  - [x] Si el filtro por usuario/asesor requiere la relacion del chat, resolverlo mediante `conversation_id` y el join con conversaciones ya persistidas; no denormalizar un campo nuevo solo para esta historia.
  - [x] Mantener intactos los flujos de creacion, link de pago, confirmacion por webhook y cancelacion.
- [x] Normalizar la presentacion de estados de orden en la UI. (AC: 1, 3, 4)
  - [x] Revisar `frontend/src/App.tsx` para que `OrdersPage` siga mostrando link de pago, referencia, vencimiento y salto al chat, pero con estados de orden y pago traducidos a espanol.
  - [x] Evitar reutilizar `StatusBadge` de forma global si su heuristica actual depende de codigos en ingles; preferir un helper o badge especifico para ordenes para no romper Inbox y otros modulos.
  - [x] Agrupar la lista por mes y anio usando datos ya persistidos por backend, sin recalcular estados ni totales en el cliente.
  - [x] Mantener la experiencia honesta cuando falten datos: vacio visible, filtros claros y sin placeholders inventados.
- [x] Cubrir regresion de listado y filtros. (AC: 1, 2, 3, 5)
  - [x] Agregar o ajustar pruebas en `backend/tests/test_tenant_and_orders.py` para validar orden descendente, filtros combinados y aislamiento por tenant.
  - [x] Probar que los filtros no mezclan ordenes de otro tenant y que el resultado respeta `company_id`.
  - [x] Si la UI cambia, validar `npm run lint` y `npm run build`.

## Dev Notes

### Contexto de negocio

- Esta historia cierra la operacion diaria del modulo de Ordenes: despues de crear, cobrar y confirmar una orden, el usuario necesita encontrarla rapido por cliente, producto, conversacion, estado y fecha.
- El usuario no debe ver codigos crudos como superficie principal; necesita etiquetas en espanol que ayuden a operar sin traducir manualmente estados internos.
- El backend sigue siendo la fuente de verdad de las ordenes, sus relaciones y su estado. La UI solo presenta y filtra datos ya persistidos.

### Estado actual del codigo

- `backend/app/orders/service.py:list_orders()` ya filtra por `company_id` y ordena por `created_at.desc()`, pero hoy no acepta filtros de negocio adicionales.
- `backend/app/orders/routes.py` expone `GET /orders` solo con `limit` y `offset`.
- `backend/app/orders/schemas.py` ya expone `status`, `payment_status`, `conversation_id`, `payment_reference`, `payment_link`, `metadata_json` y `created_at` en `OrderRead`.
- `frontend/src/App.tsx` carga las ordenes con `api<ApiOrder[]>("/orders?limit=200&offset=0")` y `OrdersPage` hoy renderiza `StatusBadge value={order.status}` y el `paymentStatus` crudo debajo del badge.
- `frontend/src/App.tsx` ya conserva `paymentLink`, `paymentReference`, `paymentExpiresAt` y la accion `onOpenConversation`, asi que la historia debe preservar esos comportamientos.
- `StatusBadge` es un componente compartido; cambiar su heuristica de forma global podria alterar conversacion, IA y otros modulos que hoy dependen de sus codigos actuales.

### Que debe cambiar

- El listado de ordenes debe seguir saliendo del mismo contrato `GET /orders`; esta historia no introduce una pantalla nueva ni una ruta paralela.
- La traduccion a espanol debe hacerse al renderizar la lista de ordenes, no cambiando los codigos internos almacenados en backend.
- La agrupacion por mes y anio es una decision de presentacion en la UI; no debe introducir logica de negocio nueva ni recalcular informacion sensible.
- Si se agrega filtro por usuario/asesor, la implementacion debe apoyarse en la relacion existente con la conversacion. Esto es una inferencia a partir del esquema actual, porque `Order` no tiene `assigned_user_id`.

### Que debe preservarse

- `company_id` como unico contexto de consulta y mutacion de datos de negocio.
- El orden descendente por fecha de creacion como default del modulo.
- Los links de pago persistidos, el vencimiento almacenado y el salto al chat desde Ordenes.
- El contrato de creacion, pago, webhook y cancelacion ya resuelto en las historias 4.1 a 4.3.
- Estados vacios honestos cuando no existan resultados o cuando el tenant no tenga ordenes que cumplan el filtro.

### Guardrails de arquitectura

- No crear un endpoint nuevo si `GET /orders` puede extenderse.
- No mover la verdad de estado al frontend.
- No traducir ni reescribir los codigos persistidos en backend; traducir solo en la vista.
- No tocar el flujo de pagos, reservas ni webhooks salvo que sea necesario para leer datos ya existentes.
- No cambiar `StatusBadge` globalmente sin revisar regresiones en Inbox y Conversation events; si hace falta, crear un wrapper especifico para ordenes.

### Pistas de implementacion

- Si el backend necesita filtros adicionales, mantenerlos en `service.py` con una firma clara y pasar los parametros desde `routes.py`.
- Para la UI, usar secciones agrupadas por mes y anio sobre la lista ya cargada y conservar el refresh manual existente.
- Para el estado visible, preferir helpers dedicados como `formatOrderStatusLabel()` y `formatPaymentStatusLabel()` en vez de hardcodear strings en JSX.
- Si el filtro por producto se hace desde el backend, debe seguir siendo tenant-scoped y compatible con el stock/inventario ya sincronizado.

### Testing requirements

- Probar que `GET /orders` sigue devolviendo resultados ordenados de mas nuevo a mas antiguo.
- Probar filtros por fecha, estado, contacto, producto y conversacion, solos y en combinacion.
- Probar que una orden de otro tenant no aparece en los resultados del tenant actual.
- Probar que la UI sigue permitiendo abrir el chat y copiar/abrir el link de pago cuando la orden lo tiene.
- Si la UI cambia, validar `npm run lint` y `npm run build`.

### Project Structure Notes

- Backend probable: `backend/app/orders/service.py`, `backend/app/orders/routes.py` y, si se requiere, pequenos ajustes en `backend/app/orders/schemas.py`.
- Frontend probable: `frontend/src/App.tsx`, concentrando ahi la agrupacion visual y los labels de estados para no abrir un router ni una nueva capa de pagina.
- Tests probables: `backend/tests/test_tenant_and_orders.py`.
- No se encontro un UX doc independiente para esta historia; mantener los patrones ya establecidos en `OrdersPage`, `SectionHeader`, `Notice` y `DataTable`.

### References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/sprint-status.yaml` - `development_status`, epic-4 backlog order]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Epic 4, Historia 4.4 y FR059-FR062]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - secciones de Ordenes y NFR-010, NFR-011, NFR-022, NFR-027]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - backend source of truth, no inventar datos, modulos de pagina y reglas de Inbox/Ordenes]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/orders/service.py` - `list_orders()`, `get_order()`, `generate_payment_link()`, `update_payment_status()`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/orders/routes.py` - `GET /orders`, `GET /orders/{order_id}`, `POST /orders/{order_id}/payment-link`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/orders/schemas.py` - `OrderRead`, `payment_status`, `conversation_id`, `metadata_json`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx` - `loadOrders()`, `mapApiOrder()`, `OrdersPage`, `StatusBadge`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py` - base de regresion de ordenes, pagos e inventario]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Se selecciono automaticamente la primera historia backlog del sprint: `4-4-listar-filtrar-y-leer-estados-de-orden-en-espanol`.
- Se revisaron `sprint-status.yaml`, el epic 4, el PRD, la arquitectura frontend, la historia 4.1, la historia 4.2 y la historia 4.3 para conservar el contrato existente de ordenes y pagos.
- Se confirmo que `GET /orders` hoy solo ordena por fecha y que `OrdersPage` renderiza estados crudos, asi que el trabajo de esta historia es extender listado y presentacion, no reinventar el flujo transaccional.
- Se identifico que `StatusBadge` es compartido, por lo que cualquier traduccion a espanol debe evitar romper Inbox y otros modulos.
- Se implemento filtro backend por fecha, estado, cliente, conversacion, producto y responsable, manteniendo el orden descendente y el aislamiento por tenant.
- Se implementaron filtros y agrupacion por mes y anio en `OrdersPage`, con badges dedicados para estado de orden y estado de pago en espanol.
- Se agregaron pruebas de orden descendente, filtros relacionales e aislamiento multi-tenant para `list_orders`.
- Se valido `npm run lint`, `npm run build` y `backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py -q`.

### Completion Notes List

- Listado de ordenes extendido sin crear endpoints paralelos.
- La UI ahora agrupa por mes y anio y muestra estados de orden/pago en espanol sin modificar `StatusBadge`.
- Los filtros de ordenes se aplican contra backend y respetan `company_id`.
- Suite completa de `backend/tests/test_tenant_and_orders.py` validada con 120 pruebas aprobadas, y despues extendida con `backend/tests/test_user_permissions.py` para un total de 140 pruebas ejecutadas en la validacion final.
- `npm run lint` y `npm run build` completados sin errores.
- Hallazgos de review resueltos: filtro de fechas alineado al huso horario del tenant y manejo visible de errores de carga de ordenes en la UI.
- Hallazgos de review resueltos en la segunda pasada: carga de ordenes desacoplada de los filtros para evitar reconexiones del websocket y refresco realtime alineado con el estado visible de error.
- Hallazgos de review resueltos en la tercera pasada: agrupado por mes alineado a la zona horaria del tenant y proteccion contra respuestas viejas que pudieran sobrescribir resultados recientes.
- Hallazgos de review resueltos en la cuarta pasada: validacion defensiva de la zona horaria del tenant en la UI y proteccion del mensaje de error de cargas obsoletas.
- Hallazgos de review resueltos en la quinta pasada: se elimino la doble carga inicial de ordenes y quedo una sola via de refresco al montar la pantalla.
- Hallazgo de review resuelto en la sexta pasada: los errores de refrescos obsoletos ya no se propagan al usuario ni ensucian el estado visible de la vista de ordenes.
- Hallazgo de review resuelto en la septima pasada: el selector de responsables de Ordenes dejo de depender del estado del Inbox y ahora usa la lista estable de usuarios del tenant.
- Hallazgo de review resuelto en la septima pasada: la UI ya no muestra exito cuando un refresco de ordenes queda obsoleto por una solicitud mas nueva.
- Hallazgo de review resuelto en la octava pasada: el tenant ahora expone una lista de usuarios accesible para miembros autenticados y el selector de responsables funciona tambien para roles no privilegiados.
- Validacion final de esta pasada: `backend/tests/test_user_permissions.py` y `backend/tests/test_tenant_and_orders.py` pasaron con 140 pruebas en total, junto con `npm run lint` y `npm run build`.

### File List

- `_bmad-output/implementation-artifacts/4-4-listar-filtrar-y-leer-estados-de-orden-en-espanol.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/app/orders/service.py`
- `backend/app/orders/routes.py`
- `backend/app/users/routes.py`
- `backend/tests/test_user_permissions.py`
- `frontend/src/App.tsx`
- `backend/tests/test_tenant_and_orders.py`

## Change Log

- 2026-07-08: Se extendio `GET /orders` con filtros por fecha, estado, cliente, conversacion, producto y responsable.
- 2026-07-08: Se reordeno `OrdersPage` para agrupar por mes/anio y traducir estados de orden y pago a espanol con badges dedicados.
- 2026-07-08: Se agregaron pruebas de listado, filtros relacionales e aislamiento multi-tenant; se valido lint, build y la suite completa de ordenes.
- 2026-07-08: Se corrigio el filtro de fechas para usar la zona horaria del tenant y se agrego un estado de error visible si falla la carga inicial de ordenes.
- 2026-07-08: Se desacoplo la recarga de ordenes de los filtros para evitar reconexiones del websocket y se mantuvo la visibilidad de errores tambien en refrescos realtime.
- 2026-07-08: Se ajusto el agrupado por mes para usar la zona horaria del tenant y se agrego proteccion de concurrencia contra respuestas obsoletas.
- 2026-07-08: Se agrego validacion defensiva de la zona horaria del tenant en la UI y se evito que errores obsoletos sobrescribieran el estado visible.
- 2026-07-08: Se removio la doble carga inicial de ordenes para dejar un unico refresco al montar la vista.
- 2026-07-08: Se ajusto el refresco de ordenes para ignorar errores de solicitudes obsoletas y evitar falsos mensajes de fallo en la UI.
- 2026-07-08: Se corrigio el selector de responsables para que use usuarios del tenant y se eviten opciones incompletas por filtros del Inbox.
- 2026-07-08: Se evito mostrar un mensaje de exito si el refresco de ordenes queda obsoleto por una solicitud mas nueva.
- 2026-07-08: Se agrego un endpoint tenant-scoped de usuarios para que el selector de responsables funcione para cualquier miembro autenticado del tenant.
