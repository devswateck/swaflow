---
title: "Historia 6.1: Ver resumen operativo del tenant en el Dashboard"
status: done
baseline_commit: 595b380d6111b59e727b01d978cf27ebc2b6a335
---

# Historia 6.1: Ver resumen operativo del tenant en el Dashboard

Status: done

## Historia

Como admin o usuario autorizado del tenant,
Quiero ver un resumen rapido de chats, ventas y agendamientos en el Dashboard,
Para que pueda entender el estado comercial sin entrar a cada modulo por separado.

## Criterios de aceptación

1. Dado que el usuario abre el Dashboard, cuando la vista principal termina de cargar, entonces el sistema muestra tarjetas resumen con chats totales, chats pendientes por leer, ventas confirmadas y agendamientos.
2. Dado que el Dashboard calcula esas tarjetas, cuando renderiza los valores, entonces la informacion pertenece solo al tenant autenticado y no mezcla datos de otra empresa.
3. Dado que el tenant no tiene actividad para una de las metricas, cuando el Dashboard renderiza la tarjeta correspondiente, entonces muestra `0` o un estado vacio honesto y no inventa valores.
4. Dado que el estado operativo cambia por eventos del Inbox, Ordenes o Citas, cuando el usuario vuelve al Dashboard o la app refresca sus datos, entonces el resumen se mantiene coherente con el backend como fuente de verdad sin obligar a navegar a otros modulos.
5. Dado que el Dashboard carga bajo volumen normal, cuando la vista principal se monta, entonces las tarjetas resumen aparecen dentro del objetivo de experiencia del producto y no bloquean la navegacion principal.

## Tareas / Subtareas

- [x] Auditar la fuente de verdad del resumen del Dashboard sin introducir un endpoint nuevo por inercia.
  - [x] Revisar `DashboardPage` y el flujo de datos del shell para confirmar si el resumen puede salir de `conversations`, `orders`, `appointments` y `totalUnread` ya disponibles.
  - [x] Mantener el contrato tenant-scoped actual y evitar duplicar logica de calculo en mas de una capa.
  - [x] Si se necesita un agregado backend, hacerlo solo con alcance minimo y preservando `company_id` en todas las consultas.
- [x] Ajustar la superficie del Dashboard para que el resumen operativo sea claro y honesto.
  - [x] Mostrar de forma explicita la tarjeta de `chats pendientes por leer` en vez de dejar ese dato solo como variable derivada fuera de la vista.
  - [x] Mantener tarjetas separadas para chats totales, ventas confirmadas y agendamientos.
  - [x] Conservar el tono visual actual del shell y no abrir un redisenio general de Dashboard en esta historia.
- [x] Preservar estados vacios, carga y consistencia entre modulos.
  - [x] Si faltan datos, mostrar estados vacios honestos o ceros, nunca mocks.
  - [x] No romper la reflexion que ya hacen Inbox, Ordenes y Citas sobre el estado comercial.
  - [x] Evitar que el resumen dependa de navegar a otros modulos para "recalcularse".
- [x] Cubrir la regresion con pruebas y verificacion de build.
  - [x] Agregar o extender pruebas si la implementacion introduce un agregado nuevo o un helper compartido.
  - [x] Verificar que el resumen siga siendo tenant-scoped y que no existan leaks cross-tenant.
  - [x] Ejecutar la validacion de frontend necesaria para asegurar que el cambio compile y mantenga el comportamiento esperado.

### Review Findings

- [x] [Review][Patch] Los filtros de citas pueden pisarse por respuestas fuera de orden [frontend/src/App.tsx:2638] — resuelto con control de request id en la carga de citas para ignorar respuestas obsoletas.
- [x] [Review][Patch] El resumen del Dashboard no se solicita directamente al entrar al Dashboard [frontend/src/App.tsx:2348] — resuelto con carga explicita del resumen cuando la vista activa es Dashboard.

## Notas de desarrollo

### Contexto de producto

- Epic 6, historia 6.1.
- FR relevantes: FR-001, FR-008, NFR-001, NFR-002, NFR-006, NFR-007.
- La historia esta orientada a lectura rapida del negocio; no es la historia de graficas ni de filtros avanzados.
- El resumen debe ayudar a un usuario autorizado a entender el estado comercial del tenant sin cambiar de modulo.

### Estado actual del codigo

- `frontend/src/App.tsx` ya tiene `DashboardPage`, pero hoy el resumen visual usa `conversations.length`, `orders` y `appointments.length` con una tarjeta de conversaciones abiertas, ordenes en pago, ventas confirmadas y citas agendadas.
- `frontend/src/App.tsx` ya calcula `totalUnread` en el shell como suma de `conversation.unreadCount`, pero ese valor no esta expuesto como tarjeta propia del Dashboard.
- `frontend/src/App.tsx` ya carga `conversations`, `orders` y `appointments` desde la superficie principal de la app; el Dashboard no necesita una arquitectura nueva para mostrar un resumen util.
- `frontend/src/App.tsx` ya sigue el patron de shell unico React/Vite con `swaflow_theme`, `swaflow_active_page` y `Zustand`.
- El backend ya actua como fuente de verdad para las entidades que alimentan el resumen; esta historia no debe inventar un store paralelo ni datos simulados.

### Guardrails criticos

- No introducir un router nuevo.
- No agregar mocks, fixtures inventadas ni numeros hardcodeados para "rellenar" el Dashboard.
- Mantener `api<T>()`, `Zustand`, `swaflow_theme` y `swaflow_active_page`.
- Mantener aislamiento multi-tenant estricto; cualquier agregado backend o lectura de datos debe seguir devolviendo solo el tenant autenticado.
- No rehacer Dashboard ni Inbox por completo en esta historia.
- No mezclar esta historia con las graficas y filtros de la historia 6.2.

### Arquitectura y estructura

- La implementacion debe quedarse preferentemente en `frontend/src/App.tsx`, que hoy ya concentra el shell y `DashboardPage`.
- Si se extrae algun helper, debe ser por reduccion real de complejidad, no por anticipacion.
- No mover el Dashboard a un modulo separado solo para esta historia.
- Si se descubre que falta un agregado real en backend, crear el contrato minimo y dejar la renderizacion de tarjetas consumiendo esa fuente de verdad sin duplicar logica en varias capas.

### Testing Requirements

- Verificar que el resumen renderiza las cuatro metricas esperadas y que `chats pendientes por leer` usa datos reales del tenant.
- Verificar que no haya leak cross-tenant si la historia introduce un agregado o endpoint nuevo.
- Verificar estados vacios y ceros honestos cuando no haya actividad.
- Verificar build de frontend y, si aplica, una prueba de backend minima para el agregado nuevo.

### Previous Story Intelligence

- La historia 5.5 ya dejo estable la visibilidad de citas y la reflexion de eventos de agenda, asi que el Dashboard puede apoyarse en esos datos sin cambiar la semantica de citas.
- El trabajo previo de Inbox ya consolidó `unreadCount` en el modelo de conversacion; esta historia debe reutilizar ese dato en lugar de volver a derivarlo de forma inconsistente.
- No tocar el comportamiento realtime del Inbox ni la persistencia de citas de la historia 5.5.

### Latest Tech Information

- No hay cambio de dependencia ni version para esta historia; usar el stack vigente del proyecto definido en `project-context.md`.
- Mantener la implementacion dentro del patron actual de React/Vite/TypeScript/Tailwind y del backend FastAPI/SQLAlchemy 2 ya establecido.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - `## Epic 6: Dashboard y Visibilidad Operativa`, `### Historia 6.1: Ver resumen operativo del tenant en el Dashboard`]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - FR-001, FR-008, NFR-001, NFR-002, NFR-006, NFR-007]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - Dashboard y visualizacion de metricas, capas del frontend y reglas de shell unico]
- [Source: `frontend/src/App.tsx:2289-2292`]
- [Source: `frontend/src/App.tsx:3611-3632`]
- [Source: `frontend/src/App.tsx:3975-4035`]
- [Source: `frontend/src/App.tsx:4818-5850`]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- 2026-07-12: Se expuso `totalUnread` en `DashboardPage` y se ajustaron las tarjetas para mostrar chats totales, chats pendientes por leer, ventas confirmadas y agendamientos.
- 2026-07-12: Validado con `npm run lint` y `npm run build` en `frontend/`.
- 2026-07-12: Se separo el resumen del Dashboard en un endpoint agregado tenant-scoped y se desacóplo de `conversations`, `orders` y `appointments` paginados/filtrados.
- 2026-07-12: Se agregaron guardas para `update_appointment` con payloads nulos, versionado de agenda compartida y fallback best-effort para `appointments/operational-config` cuando no existe agente IA.
- 2026-07-12: Se validó el cambio con `backend/tests/test_dashboard_summary.py`, `npm run lint` y `npm run build`.
- 2026-07-13: Se corrigió el control de concurrencia de la agenda compartida para que la version avance en cada guardado exitoso y el stale write quede bloqueado de verdad.
- 2026-07-13: Se revalidó el flujo con `backend/tests/test_dashboard_summary.py` y `backend/tests/test_tenant_and_orders.py`.
- 2026-07-13: Se ejecutó la suite backend completa y pasó sin regresiones.
- 2026-07-13: Se expuso `company_currency` en `currentUser` para contexto del tenant y configuraciones relacionadas.
- 2026-07-13: Se resetea el resumen del Dashboard al cambiar de tenant para evitar arrastrar KPIs de sesiones anteriores.
- 2026-07-13: Se validó el ajuste con `backend/tests/test_user_permissions.py`, `backend/tests/test_dashboard_summary.py`, `npm run lint` y `npm run build`.
- 2026-07-13: Se corrigió la presentacion de `Ventas confirmadas` para no inferir una moneda donde el agregado no la garantiza; el Dashboard ahora muestra un valor neutro y se conservaron los helpers monetarios usados en otras vistas.

### Completion Notes List

- Se mantuvo el resumen dentro de `frontend/src/App.tsx` sin crear endpoint nuevo ni duplicar calculos tenant-scoped.
- La tarjeta de chats pendientes por leer ahora se renderiza de forma explicita con `totalUnread` derivado del shell.
- Se conservaron estados honestos para ceros y se mantuvo el tono visual del shell sin redisenio general.
- Se corrigieron dos helpers huérfanos y una dependencia de hook para dejar `eslint` en verde.
- El dashboard ahora consume `GET /api/v1/dashboard/summary` para evitar que paginacion y filtros de otras vistas alteren los numeros de síntesis.
- Se agregaron pruebas para el resumen tenant-scoped, para rechazar updates de cita con `null` y para detectar versiones obsoletas en la agenda compartida.
- Se ajustó el guardrail de versionado de la agenda compartida para que cada guardado exitoso incremente la version y deje el conflicto pendiente para writes obsoletos reales.
- Se validó el cambio con la suite backend completa (`215 passed`).
- El Dashboard ya no infiere moneda para `Ventas confirmadas`; ese KPI se muestra de forma neutra para no mezclar un agregado numerico con una moneda no garantizada.
- Se agregó cobertura de contrato para `GET /api/v1/auth/me` con moneda de la empresa.

### File List

- `frontend/src/App.tsx`
- `backend/app/dashboard/__init__.py`
- `backend/app/dashboard/routes.py`
- `backend/app/dashboard/schemas.py`
- `backend/app/dashboard/service.py`
- `backend/app/auth/schemas.py`
- `backend/app/auth/service.py`
- `backend/app/main.py`
- `backend/app/appointments/service.py`
- `backend/tests/conftest.py`
- `backend/tests/test_dashboard_summary.py`
- `backend/tests/test_user_permissions.py`
- `backend/tests/test_tenant_and_orders.py`
- `_bmad-output/implementation-artifacts/6-1-ver-resumen-operativo-del-tenant-en-el-dashboard.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-07-12: Historia creada para abrir la Epic 6 con el resumen operativo del Dashboard.
- 2026-07-12: Dashboard operativo actualizado para mostrar chats pendientes por leer y consolidar el resumen con datos del shell.
- 2026-07-12: Resumen del Dashboard desacoplado de listas paginadas y endurecidas las guardas de agenda/citas tras review.
- 2026-07-13: Addressed code review finding - la version de la agenda compartida ahora avanza en cada guardado exitoso y el stale write queda protegido.
- 2026-07-13: Addressed code review findings - el Dashboard ya no hereda KPIs de otro tenant y mantiene `Ventas confirmadas` sin inferir moneda.
- 2026-07-13: Addressed code review findings - se eliminó la inferencia de moneda en `Ventas confirmadas` para evitar presentar una conversion potencialmente incorrecta.
- 2026-07-13: Addressed code review findings - se blindó la carga de citas contra respuestas fuera de orden y se solicitó el resumen del Dashboard al entrar a la vista.
