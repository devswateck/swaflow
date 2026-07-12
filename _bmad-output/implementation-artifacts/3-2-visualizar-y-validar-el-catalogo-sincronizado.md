# Story 3.2: Visualizar y validar el catalogo sincronizado

baseline_commit: ee0b2c761a0873ae7b8b682ce757a43546222c48
Status: done

## Story

Como usuario autorizado del tenant,
quiero ver el catalogo sincronizado con mensajes claros sobre su estado en Meta,
para que pueda entender si los productos estan listos para operar o requieren correccion.

## Acceptance Criteria

1. Dado que el catalogo ya fue sincronizado, cuando el usuario abre Productos, entonces el sistema muestra los productos sincronizados dentro de Swaflow y la vista permite distinguir productos activos, inactivos o con problemas de asociacion.
2. Dado que el catalogo Meta no esta asociado a la WABA activa, cuando el usuario revisa el estado del catalogo, entonces el sistema lo advierte claramente y explica cuando Meta permite leer productos pero no enviarlos como cards nativas.
3. Dado que Meta devuelve errores comunes de configuracion, cuando ocurre un problema con IDs de catalogo o conjuntos de productos, entonces el sistema muestra un mensaje entendible para el admin y no oculta el motivo tecnico esencial de la falla.

## Tasks / Subtasks

- [x] Revisar la pagina actual de Productos y preservar el flujo de sincronizacion ya existente.
  - [x] Reusar la accion `Actualizar catalogo` y el endpoint `POST /whatsapp/catalog/sync`.
  - [x] Evitar crear un modulo o ruta nueva para catalogo; la superficie sigue siendo `Productos`.
  - [x] Mantener estados vacios y mensajes en espanol, sin datos inventados.
- [x] Hacer visible el estado de cada producto sincronizado y su relacion con Meta.
  - [x] Extender la lectura de productos para exponer campos utiles de mapeo Meta si la UI los necesita.
  - [x] Mostrar de forma distinguible productos `active`, `inactive` y productos sin asociacion Meta completa.
  - [x] Separar en la UI los productos sincronizados desde Meta de los registros que no tienen origen Meta.
- [x] Endurecer los mensajes de validacion del catalogo.
  - [x] Mantener el warning cuando el catalogo no esta vinculado a la WABA activa.
  - [x] Traducir errores comunes de Meta a texto util para admin sin perder el detalle tecnico esencial.
  - [x] Conservar el resumen de resultados del sync: leidos, creados, actualizados y advertencias.
- [x] Agregar cobertura de regresion y verificacion manual.
  - [x] Verificar que la pagina sigue compilando y que el flujo de Productos/Inventario no se rompe.
  - [x] Validar que el estado mostrado coincide con la fuente de verdad del backend.
  - [x] Revisar que la copia en la UI no sugiera que Swaflow crea catalogos paralelos.

## Dev Notes

### Business Context

- Esta historia cierra la experiencia de visualizacion del catalogo ya sincronizado en Epic 3.
- El objetivo no es crear un catalogo nuevo, sino ayudar al usuario a entender si los productos del tenant estan listos para operar o si Meta exige correccion.
- El backend sigue siendo la fuente de verdad. La UI solo interpreta y muestra el estado real ya persistido.

### Current Code State

- `frontend/src/App.tsx` ya tiene `ProductsPage` con:
  - campo manual `Catalog ID Meta`
  - accion `Actualizar catalogo`
  - banner de `notice`, `warning` y `error`
  - tabla de productos sincronizados
- `ProductsPage` hoy lista `GET /products?limit=200&offset=0&include_inactive=true` y `GET /inventory?limit=200&offset=0`.
- `ApiProduct` en `frontend/src/App.tsx` solo mapea `id`, `name`, `sku`, `price`, `currency` y `status`; si la UI necesita distinguir origen o mapeo Meta, ese contrato debe ampliarse ahi.
- `backend/app/whatsapp/service.py` ya devuelve `WhatsAppCatalogSyncResponse` con `fetched`, `created`, `updated` y `warning`.
- `_catalog_link_warning()` ya cubre el caso en que Meta permite leer el catalogo pero no lo tiene vinculado a la WABA activa.
- `_sync_catalog_products_with_account()` ya marca productos como `inactive` cuando Meta reporta `out of stock` o `discontinued`, y deja el inventario consistente.
- La historia 3.1 ya dejo el sync canonico en WhatsApp/Product/Inventory; no reinvertir ese flujo.

### Critical Guardrails

- No crear un catalogo paralelo ni un endpoint nuevo si el actual ya cumple el contrato.
- No inventar estados de Meta ni advertencias que no vengan del backend o de una derivacion directa de los datos persistidos.
- No ocultar productos inactivos ni registros sin mapeo Meta; la UI debe explicarlos, no maquillarlos.
- No romper el 404 cross-tenant ni los permisos de modulo ya existentes.
- No introducir mocks para contenido operativo.

### Implementation Guidance

- Reusar `ProductsPage` en `frontend/src/App.tsx` y concentrar la logica de validacion en esa superficie.
- Si hace falta mostrar mas detalle de origen Meta, extender `ApiProduct`, `mapApiProduct` y la tabla de Productos antes de tocar otras pantallas.
- Mantener la vista de Inventario como complemento, no como fuente primaria de validacion del catalogo.
- Si se ajustan mensajes de advertencia, hacerlo en backend solo cuando la UI no pueda inferir el estado con seguridad.
- La UX debe seguir siendo honesta: si Meta no confirma vinculacion o reporta problemas, el usuario debe verlo sin ambiguedad.

### Suggested File Targets

- `frontend/src/App.tsx`
- `backend/app/whatsapp/service.py` solo si se necesita ajustar el contenido de `warning`
- `backend/app/whatsapp/schemas.py` solo si cambia el contrato de respuesta del sync
- `backend/tests/test_tenant_and_orders.py` o `backend/tests/test_whatsapp_setup.py` si se necesita regresion del warning o del estado sincronizado

### Testing Requirements

- Verificar `npm run lint` y `npm run build` despues de cualquier ajuste de UI.
- Si cambia el contrato de sync, agregar o actualizar tests backend para:
  - warning de catalogo no vinculado a WABA
  - catalogos invalidos y mensajes de error util para admin
  - productos activos/inactivos derivados del sync
- Confirmar manualmente que la pantalla de Productos:
  - muestra el resumen del sync
  - diferencia activos, inactivos y sin asociacion Meta
  - no rompe el flujo de Inventario

### Project Structure Notes

- La arquitectura del frontend sigue siendo una superficie React/Vite unica con `App.tsx` como shell.
- No introducir router nuevo ni mover la pagina de Productos a una ruta separada.
- Mantener `api<T>()`, `Zustand`, `swaflow_theme` y `swaflow_active_page`.
- Los tokens visuales y el dark mode por defecto se preservan; esta historia no debe alterar la identidad base de la app.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 3, Historia 3.2, FR038, FR041, FR043]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - seccion Productos e Inventario, FR036-FR052]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - capas de frontend, Tokens de diseno, Modulos de pagina y reglas de no inventar datos]
- [Source: `_bmad-output/implementation-artifacts/3-1-sincronizar-el-catalogo-meta-del-tenant.md` - learnings y contrato canonico del sync]
- [Source: `frontend/src/App.tsx` - `ProductsPage`, `InventoryPage`, `ApiProduct`, `mapApiProduct`]
- [Source: `backend/app/whatsapp/service.py` - `_catalog_link_warning()`, `_sync_catalog_products_with_account()`]
- [Source: `backend/app/whatsapp/schemas.py` - `WhatsAppCatalogSyncResponse`]
- [Source: `backend/app/products/service.py` - lectura canonica de productos y estados]
- [Source: `backend/app/inventory/service.py` - inventario sincronizado y disponibilidad]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- 2026-07-03: Extendido `frontend/src/App.tsx` para separar productos Meta y locales, mostrar asociacion y mantener el resumen de validacion del catalogo.
- 2026-07-03: Validaciones ejecutadas con `frontend` `npm run lint` y `npm run build`, ambas correctas.
- 2026-07-03: Regresion backend validada con `./backend/.venv/bin/python -m pytest backend/tests/test_whatsapp_setup.py -q` y `./backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py -q`.

### Completion Notes List

- La pagina de Productos ahora diferencia catalogo sincronizado desde Meta y registros locales del tenant.
- Se agrego informacion de asociacion Meta para detectar productos sin mapeo o con mapping incompleto.
- El resumen de sincronizacion sigue mostrando advertencias del backend cuando Meta no confirma la vinculacion con la WABA.
- No se creo un catalogo paralelo ni una ruta nueva; se preservo `ProductsPage` como superficie unica.
- Las validaciones de frontend y las suites relevantes de backend quedaron verdes.

### File List
- `frontend/src/App.tsx`
- `_bmad-output/implementation-artifacts/3-2-visualizar-y-validar-el-catalogo-sincronizado.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-07-03: Mejorada la visualizacion y validacion del catalogo sincronizado en la pagina de Productos, con separacion de origen Meta/local, resumen operacional y mensajes de asociacion claros.
