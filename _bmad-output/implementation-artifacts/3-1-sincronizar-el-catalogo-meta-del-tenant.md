---
baseline_commit: ee0b2c761a0873ae7b8b682ce757a43546222c48
---

# Story 3.1: Sincronizar el catalogo Meta del tenant

Status: done

## Story

Como admin principal del tenant,
Quiero sincronizar el catalogo existente de Meta con Swaflow,
Para que el sistema opere productos reales sin crear catalogos paralelos.

## Acceptance Criteria

1. Dado que el tenant tiene un catalogo Meta asociado, cuando el admin ejecuta la sincronizacion, entonces el sistema trae los productos existentes desde Meta y guarda localmente nombre, descripcion, precio, moneda, estado, catalogo Meta, `whatsapp_product_retailer_id` y metadata relevante.
2. Dado que un producto se sincroniza correctamente, cuando el sistema lo almacena, entonces queda disponible para visualizacion y uso operativo dentro del tenant, y conserva el `whatsapp_product_retailer_id` cuando corresponda.
3. Dado que el producto no existe en Meta, cuando el admin revisa el catalogo local, entonces el sistema no permite crear ese producto como si fuera nativo de Swaflow y evita mezclar productos inventados con productos sincronizados.
4. Dado que la sincronizacion usa el catalogo de WhatsApp/Meta, cuando el usuario no tiene acceso al modulo correspondiente o pertenece a otro tenant, entonces el backend responde con el error correcto y no expone productos ni credenciales ajenas.
5. Dado que el sync detecta productos removidos o no sincronizables, cuando actualiza el catalogo, entonces el producto local queda consistente con el estado de Meta y el inventario asociado no queda apuntando a un producto inexistente.

**FR cubiertos:** FR036, FR037, FR038, FR039, FR042, FR043, NFR010, NFR011, NFR013, NFR014, NFR018, NFR030, NFR032

## Tasks / Subtasks

- [x] Auditar el contrato real de sincronizacion de catalogo y preservar lo que ya funciona.
  - [x] Revisar `backend/app/whatsapp/service.py`, `backend/app/whatsapp/routes.py`, `backend/app/whatsapp/schemas.py`, `backend/app/products/models.py`, `backend/app/products/service.py`, `backend/app/products/schemas.py`, `backend/app/inventory/models.py`, `backend/app/inventory/service.py` y `frontend/src/App.tsx`.
  - [x] Confirmar que `sync_catalog_products()` y `_sync_catalog_products_with_account()` sigan siendo la fuente canonica del sync de Meta.
  - [x] Preservar la regla de tenant-scoping y el uso de `require_module_access("whatsapp")` para la accion de sincronizacion existente.
- [x] Mantener el mapeo Meta -> Product sin crear una tabla o modulo paralelo.
  - [x] Reusar `Product` como verdad persistida del catalogo local.
  - [x] Conservar `whatsapp_catalog_id`, `whatsapp_product_retailer_id`, `status` y `metadata_json` como contrato de producto sincronizado.
  - [x] Mantener `meta_catalog_sync` como fuente de metadata trazable para productos importados.
- [x] Preservar la inicializacion/actualizacion de inventario ligada al sync.
  - [x] Reusar `ensure_inventory_for_products()` para crear inventario local solo para productos existentes en el catalogo sincronizado.
  - [x] Mantener consistente el inventario de productos removidos o no retornados por Meta.
  - [x] No permitir que el sync cree inventario para productos que no existan en Meta.
- [x] Exponer el estado sincronizado en la superficie de productos sin inventar datos.
  - [x] Reusar la pagina existente de Productos para mostrar los items sincronizados.
  - [x] Reusar la pagina de Inventario para reflejar el stock inicial y la disponibilidad base ya derivada por el backend.
  - [x] Mantener textos honestos en espanol para warning, estado vacio y errores de sincronizacion.
- [x] Agregar cobertura de regresion.
  - [x] Cubrir el sync exitoso de productos Meta con `fetched`, `created`, `updated` y metadata persistida.
  - [x] Cubrir que productos removidos queden inactivos y que su inventario no quede con stock utilizable.
  - [x] Cubrir el rechazo de IDs invalidos de catalogo/conjunto con mensaje entendible para el admin.
  - [x] Cubrir `404` cross-tenant y permiso insuficiente en la ruta de sincronizacion.
  - [x] Cubrir que la UI sigue compilando y que el flujo no inventa productos ni inventario fuera del backend.

## Dev Notes

### Business Context

- Esta story inicia el Epic 3: el tenant necesita sincronizar el catalogo real de Meta para operar ventas conversacionales con productos existentes, no inventados.
- El alcance no es crear un nuevo sistema de catalogo. Ya existen `products` e `inventory`; esta historia debe llenar esos dominios desde Meta.
- La sincronizacion debe ser util para Producto, Inventario, WhatsApp e IA, pero el backend sigue siendo la fuente de verdad y no se permite crear un catalogo paralelo.

### Current Code State

- `backend/app/whatsapp/service.py` ya implementa `_sync_catalog_products_with_account()` y `sync_catalog_products()`.
- La sync actual trae filas de Meta, normaliza `name`, `description`, `price`, `currency`, `availability`, `retailer_id`, persiste `Product` y usa `ensure_inventory_for_products()` para inventario local.
- La sync ya marca productos removidos o ausentes como `inactive` y pone `quantity_available = 0` cuando no aparecen en la respuesta de Meta.
- `backend/app/whatsapp/routes.py` ya expone `POST /whatsapp/catalog/sync` con `require_module_access("whatsapp")`.
- `backend/app/products/service.py` y `backend/app/products/routes.py` ya son la superficie canonica para leer productos del tenant.
- `backend/app/inventory/service.py` y `backend/app/inventory/routes.py` ya son la superficie canonica para leer y ajustar inventario del tenant.
- `frontend/src/App.tsx` ya tiene paginas de Productos e Inventario que leen `/products` y `/inventory`, asi que el sync debe alimentar esas pantallas sin crear otra superficie nueva.

### Critical Guardrails

- No crear un modulo nuevo de catalogo si `whatsapp`, `products` e `inventory` ya cubren la frontera correcta.
- No permitir que el frontend sea la fuente de verdad del catalogo sincronizado.
- No permitir productos inventados fuera de Meta.
- No permitir inventario para productos inexistentes en Meta o no sincronizados.
- No mover la accion de sync a una ruta nueva si la ruta actual ya cumple el contrato.
- No romper el comportamiento cross-tenant: otro tenant debe seguir respondiendo `404`.
- No exponer tokens, IDs o payloads de Meta en texto plano fuera de lo estrictamente necesario.

### Implementation Guidance

- Reusar `_sync_catalog_products_with_account()` como flujo canonico de ingestión de catalogo.
- Si hace falta ajustar validaciones o mensajes, hacerlo dentro de `backend/app/whatsapp/service.py` y no duplicando la logica en `products` o `inventory`.
- Mantener `Product.status` derivado de la disponibilidad de Meta y del estado de sincronizacion, no de un estado inventado desde UI.
- Mantener la metadata de importacion en `metadata_json` para trazabilidad y depuracion.
- Si el sync detecta errores comunes de Meta, devolver mensajes claros para el admin sin filtrar detalles sensibles de credenciales.
- No mezclar esta historia con la disponibilidad operativa detallada de inventario; eso pertenece a la historia 3.3.

### Suggested File Targets

- Backend likely to change:
  - `backend/app/whatsapp/service.py`
  - `backend/app/whatsapp/routes.py`
  - `backend/app/whatsapp/schemas.py` si el contrato de sync necesita feedback adicional
  - `backend/app/products/service.py` solo si se requiere un ajuste de lectura/persistencia
  - `backend/app/inventory/service.py` solo si hace falta afinar la inicializacion de inventario
  - `backend/tests/test_tenant_and_orders.py`
- Frontend likely to change:
  - `frontend/src/App.tsx`

### Testing Requirements

- Probar sincronizacion exitosa desde Meta y persistencia de `Product` con `whatsapp_catalog_id`, `whatsapp_product_retailer_id` y `metadata_json`.
- Probar que los productos removidos o ausentes queden inactivos y no queden disponibles para operacion.
- Probar que el inventario local se crea o actualiza solo para productos sincronizados.
- Probar rechazo de catalogos invalidos con mensaje util para el admin.
- Probar `404` cross-tenant y permisos insuficientes.
- Probar que `npm run build` y `npm run lint` siguen pasando despues de cualquier ajuste de UI.

### Project Structure Notes

- El dominio correcto del sync vive en `backend/app/whatsapp/`, con persistencia final en `backend/app/products/` y `backend/app/inventory/`.
- No introducir un `catalog` module paralelo si el repositorio ya tiene productos e inventario normalizados.
- La UI de Productos e Inventario debe seguir usando `api<T>()` y el estado existente.
- Mantener los nombres de campo ya usados por el backend: `whatsapp_catalog_id`, `whatsapp_product_retailer_id`, `metadata_json`, `quantity_available`, `quantity_reserved`.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 3, Historia 3.1, FR036-FR039 y FR042-FR043]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - seccion Productos e Inventario, FR036-FR052]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - dominios de productos/inventario, backend source of truth y contrato de integracion]
- [Source: `_bmad-output/implementation-artifacts/1-9-configurar-calendario-del-tenant.md` - patrón previo de integracion canonica, UX honesta y pruebas tenant-scoped]
- [Source: `backend/app/whatsapp/service.py` - `_sync_catalog_products_with_account()`, `sync_catalog_products()` y persistencia de productos/inventario]
- [Source: `backend/app/whatsapp/routes.py` - `POST /whatsapp/catalog/sync`]
- [Source: `backend/app/products/models.py` - contrato de `Product`]
- [Source: `backend/app/products/service.py` - lectura/persistencia canonica de productos]
- [Source: `backend/app/inventory/models.py` - contrato de inventario]
- [Source: `backend/app/inventory/service.py` - inicializacion y lectura de inventario]
- [Source: `frontend/src/App.tsx` - paginas de Productos e Inventario]
- [Source: `backend/tests/test_tenant_and_orders.py` - regresion existente para catalogo, cards y disponibilidad]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References
- 2026-07-03: Revisado el contrato canonico de sincronizacion en `backend/app/whatsapp/service.py` y confirmado que `products` e `inventory` siguen siendo la fuente persistida.
- 2026-07-03: Ajustada la UI de Productos/Inventario para separar `warning` de `error` y mostrar estados vacios honestos.
- 2026-07-03: Agregadas pruebas de regresion para catalogo invalido, cross-tenant y permisos de modulo en `backend/tests/test_whatsapp_setup.py`.
- 2026-07-03: Validado con `UV_CACHE_DIR=/private/tmp/uv-cache uv run pytest -q`, `npm run lint` y `npm run build`.
- 2026-07-03: Corregido el sync para omitir filas Meta con precio invalido en vez de inventar un valor.
- 2026-07-03: Bloqueada la creacion/edicion manual de productos con mapping Meta en `backend/app/products/service.py`.
- 2026-07-03: Agregada regresion para precio invalido en sync y para bloqueo de mappings Meta manuales.
- 2026-07-03: Ajustado el sync para preservar productos Meta ya existentes cuando una fila llega con precio invalido.
- 2026-07-03: Normalizados los campos de mapping Meta vacios a `None` en `backend/app/products/schemas.py`.
- 2026-07-03: Agregada regresion para preservar productos existentes y aceptar mappings vacios como nulos.

### Completion Notes List
- Sincronizacion de catalogo Meta validada sobre el flujo existente; no se introdujo un modulo paralelo de catalogo.
- La UI de Productos ahora muestra advertencias separadas, y las pantallas de Productos/Inventario tienen estado vacio explicito.
- Se cubrieron con pruebas el rechazo de IDs de conjunto/catálogo, `404` cross-tenant y `403` por falta de acceso al modulo WhatsApp.
- Se corrigio la inventada de precio en la sincronizacion y se bloqueo la edicion manual de productos con mapping Meta.
- La suite completa de backend y la compilacion/lint de frontend quedaron verdes despues del ajuste.
- El sync preserva productos ya sincronizados aunque Meta emita un precio invalido, sin inventar un valor nuevo.
- Los campos de mapping Meta vacios ya se normalizan a `None`, evitando persistencia de IDs vacios.

### File List
- backend/tests/test_whatsapp_setup.py
- backend/tests/test_tenant_and_orders.py
- backend/app/products/service.py
- backend/app/products/schemas.py
- backend/app/whatsapp/service.py
- frontend/src/App.tsx

### Change Log
- 2026-07-03: Implementada la cobertura de regresion para la historia 3.1 y ajustada la UI de catalogo/inventario para reflejar estados reales del backend.
- 2026-07-03: Addressed code review findings - 2 items resolved.
- 2026-07-03: Addressed code review findings - invalid-price preservation and blank Meta mapping normalization.

### Review Findings
- [x] [Review][Patch] Definir manejo de precio invalido de Meta en productos ya sincronizados — la fila invalida ahora se omite de la sincronizacion y el producto local queda inactivo en vez de seguir operando con un precio viejo.
- [x] [Review][Patch] Permitir edicion local de productos sincronizados sin tocar el mapping Meta — `backend/app/products/service.py` ahora solo bloquea cambios al mapping cuando el payload intenta modificar esos campos, pero permite actualizar campos locales como nombre, precio o estado.
- [x] [Review][Patch] No persistir estados de WhatsApp sin conversación resuelta — `backend/app/whatsapp/service.py` ahora omite `message.status` cuando no puede resolver `conversation_id` por `Message` o por el evento `message.sent` asociado.
