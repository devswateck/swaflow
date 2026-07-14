# Story 6.2: Visualizar gráficas y filtrar métricas del Dashboard

Status: done

## Story

Como admin o usuario autorizado del tenant,
quiero ver gráficas y filtrar las métricas del Dashboard por distintos criterios,
para analizar tendencias de ventas, chats y agendamientos con contexto útil y sin mezclar datos de otras empresas.

## Acceptance Criteria

1. Dado que el usuario abre el Dashboard, cuando la vista carga la información histórica, entonces el sistema muestra gráficas reales de chats, ventas y agendamientos en el tiempo.
2. Dado que el usuario aplica filtros por rango de fechas, asesor/usuario, estado de chat, funnel o etapa, y producto, cuando se recalculan las métricas, entonces el Dashboard devuelve datos filtrados coherentes con el tenant autenticado.
3. Dado que un filtro no aplica al tenant actual o no hay opciones útiles para esa dimensión, cuando se renderiza la barra de filtros, entonces el sistema oculta, deshabilita o aclara el filtro de forma honesta y no inventa valores.
4. Dado que no existe serie real para una gráfica o la carga falla, cuando la tarjeta de gráfica se renderiza, entonces el sistema muestra estado vacío, skeleton o error accionable con reintento y no rellena el panel con datos ficticios.
5. Dado que el usuario cambia filtros o vuelve al Dashboard, cuando llegan respuestas tardías o se cambia de tenant, entonces el sistema ignora resultados obsoletos y mantiene el contexto del tenant correcto.
6. Dado que el Dashboard ya muestra el resumen operativo de la historia 6.1, cuando se agrega esta capa histórica, entonces se preservan las KPIs existentes y el comportamiento sigue siendo fluido bajo volumen normal.

## Tasks / Subtasks

- [x] Definir el contrato de datos históricos del Dashboard sin reutilizar indebidamente `/dashboard/summary`.
  - [x] Confirmar qué métricas ya existen y cuáles requieren agregado backend específico para series históricas.
  - [x] Diseñar un endpoint o contrato dedicado para series y agregados filtrables del Dashboard, siempre tenant-scoped por `company_id`.
  - [x] Reutilizar vocabulario de filtros ya existente en otros módulos cuando aplique: fechas, usuario/asesor, estado, funnel/etapa y producto.
- [x] Implementar la capa visual del Dashboard con gráficas reales y estados honestos.
  - [x] Añadir el bloque de filtros con defaults claros y persistencia local solo si no rompe el contexto del tenant.
  - [x] Renderizar paneles de gráfica con Recharts para series reales, con ejes, leyenda, tooltip y labels visibles.
  - [x] Mantener KPI cards y resumen operativo de 6.1 como base superior del Dashboard.
  - [x] Mostrar estados vacíos o mensajes de carga/error cuando falte serie real.
- [x] Integrar el Dashboard con datos del tenant sin derivar desde listas paginadas.
  - [x] Usar el contrato backend para agregados históricos en lugar de reconstruir series desde `conversations`, `orders` o `appointments` paginados.
  - [x] Reutilizar `tenantUsers`, `funnels` y `products` ya cargados en `App.tsx` para poblar filtros cuando existan opciones.
  - [x] Asegurar que los cambios de filtro se limpien al cambiar de tenant y que las respuestas fuera de orden no pisen el estado nuevo.
- [x] Cubrir el cambio con pruebas de backend y verificación de frontend.
  - [x] Agregar pruebas de tenant isolation para el contrato histórico.
  - [x] Probar filtros con datos reales, datos vacíos y respuestas obsoletas.
  - [x] Verificar `npm run lint` y `npm run build` para el frontend.

## Dev Notes

### Contexto del producto

- Epic 6: Dashboard y Visibilidad Operativa.
- Esta historia cubre la parte analítica del Dashboard, no el resumen operativo de la historia 6.1.
- FR relevantes: FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008.
- NFR relevantes: NFR-001, NFR-002, NFR-006, NFR-007, NFR-010, NFR-011.
- El Dashboard debe servir para leer tendencias reales del tenant, no para mostrar gráficas decorativas.

### Estado actual del código

- `frontend/src/App.tsx` ya concentra el shell, el `DashboardPage` y el fetch del resumen operativo con `loadDashboardSummary()`.
- `frontend/src/App.tsx` hoy solo pinta métricas simples en el Dashboard; no existen paneles de gráfica ni barra de filtros para análisis histórico.
- `frontend/src/App.tsx` ya tiene request-id guards para evitar respuestas obsoletas en otras vistas; el nuevo flujo del Dashboard debe seguir ese patrón.
- `backend/app/dashboard/routes.py`, `backend/app/dashboard/service.py` y `backend/app/dashboard/schemas.py` solo exponen `/dashboard/summary`.
- `frontend/package.json` no incluye `recharts`; si se agrega gráfica real, esta dependencia debe incorporarse explícitamente.
- `tenantUsers`, `funnels`, `products`, `orders`, `appointments` y `conversations` ya viven en el estado del shell y pueden reutilizarse para poblar filtros o validar opciones, pero no para inventar series históricas.

### Guardrails críticos

- No derivar gráficas desde listas paginadas o parciales del frontend.
- No usar mocks, series hardcodeadas ni datos de ejemplo para completar paneles vacíos.
- No mezclar esta historia con cambios de navegación, branding o rediseño general del shell.
- No romper el resumen operativo de la historia 6.1 ni su comportamiento tenant-scoped.
- Mantener el aislamiento por `company_id` en toda consulta y agregación.
- Mantener microcopy y estados visibles en español.
- Si una dimensión no tiene datos útiles para el tenant, ocultarla o explicarla honestamente en vez de forzar un filtro inútil.

### Arquitectura y estructura

- La UI del Dashboard sigue viviendo en `frontend/src/App.tsx` mientras el shell siga concentrado ahí.
- Si la complejidad crece, extraer solo componentes con forma estable y reutilizable; no separar por anticipación.
- El contrato histórico del Dashboard debe ser explícitamente distinto del resumen; no sobrecargar `/dashboard/summary` con series y filtros complejos.
- Preferir un contrato backend dedicado para agregados/series filtrables, con respuestas tenant-scoped y listas para graficar sin que el frontend tenga que recalcular estados críticos.
- Reusar los mismos criterios de filtrado cuando existan equivalentes en otros módulos: `created_from`, `created_to`, `assigned_user_id`, `status`, `funnel_id`, `funnel_step_id`, `product_id`.

### Detalles funcionales a respetar

- La vista debe conservar la idea de "KPI primero, gráficas segundo" definida en arquitectura y UX.
- Las gráficas deben tener labels reales, rango visible, leyenda y tooltip; no deben ser paneles vacíos decorativos.
- Si no hay serie real, usar estado vacío honesto con CTA de reintento o mensaje breve, no placeholder inventado.
- La barra de filtros debe mostrar el periodo activo y dejar claro cuando un filtro impacta los resultados.
- Si hay más de un usuario activo o adicional en el tenant, el filtro por asesor/usuario debe estar disponible; si no, no debe estorbar la vista.
- El Dashboard debe seguir respondiendo bien en desktop/laptop y respetar la densidad operacional del producto.

### Testing Requirements

- Probar que el contrato histórico solo devuelve datos del tenant autenticado.
- Probar que los filtros cambian las series y no solo el texto visible.
- Probar comportamiento con series vacías, con un solo punto y con varias series.
- Probar que respuestas tardías o fuera de orden no sobreescriben el estado más reciente.
- Probar que el Dashboard conserva el resumen operativo de la historia 6.1.
- Verificar `npm run lint` y `npm run build` en frontend.

### Previous Story Intelligence

- La historia 6.1 ya dejó estable el resumen operativo del Dashboard y expuso la necesidad de mantener coherencia entre resumen y datos del backend.
- El resumen actual se recarga al entrar al Dashboard y cuando cambia el tenant; esa misma disciplina debe mantenerse para las series históricas.
- La revisión previa corrigió el manejo de respuestas obsoletas en otras superficies; reutilizar ese patrón evita que un filtro lento pise el estado actual.
- No volver a calcular en frontend lo que el backend ya considera fuente de verdad para el tenant.

### Git Intelligence Summary

- Los commits recientes muestran sincronización de cambios locales y fixes de rutas/proxy, pero no aportan una base específica para gráficas históricas.
- No hay una línea de implementación previa para charts en el frontend; esta historia introduce ese contrato por primera vez.

### Latest Tech Information

- `recharts` es la librería de gráficas aprobada por la arquitectura/UX, pero hoy no está en `frontend/package.json`.
- Al implementar, agregar la dependencia explícitamente y usar la API oficial de Recharts para `ResponsiveContainer`, `LineChart`, `AreaChart`, `BarChart`, `XAxis`, `YAxis`, `CartesianGrid`, `Tooltip` y `Legend`.
- No construir SVG manual ni introducir otra librería de charts sin una decisión arquitectónica nueva.
- Si se define un nuevo endpoint histórico, mantener el contrato simple y serializable para que el frontend solo pinte, no compute negocio.

### Project Structure Notes

- Frontend principal: `frontend/src/App.tsx`.
- Dependencias frontend: `frontend/package.json` y `frontend/package-lock.json`.
- Dashboard backend actual: `backend/app/dashboard/routes.py`, `backend/app/dashboard/service.py`, `backend/app/dashboard/schemas.py`.
- Pruebas backend para dashboard: `backend/tests/test_dashboard_summary.py` o un nuevo archivo de pruebas de dashboard si el alcance crece.
- No crear router nuevo en frontend.
- No mover el shell completo a un router ni a una arquitectura paralela para esta historia.

### References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - `## Epic 6: Dashboard y Visibilidad Operativa`, `### Historia 6.2: Visualizar graficas y filtrar metricas del Dashboard`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - sección `Dashboard`, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/DESIGN.md` - `Chart panel`, `Dashboard: grid responsivo de 12 columnas`, `Metric card`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - `Flujos clave`, `Dashboard sin datos`, `Dashboard cargando`, `Dashboard desactualizado`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - secciones `Gráficas`, `Patrones de componentes`, `Patrones de estado`, `Flujo de implementación`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx` - `DashboardPage`, `loadDashboardSummary`, request-id guards, estado actual del shell]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/dashboard/routes.py`, `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/dashboard/service.py`, `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/dashboard/schemas.py` - contrato actual de `/dashboard/summary`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/conversations/routes.py`, `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/orders/routes.py`, `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/routes.py` - vocabulario de filtros reutilizable]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Backend: `backend/app/dashboard/routes.py`, `backend/app/dashboard/service.py`, `backend/app/dashboard/schemas.py`
- Frontend: `frontend/src/App.tsx`, `frontend/package.json`, `frontend/package-lock.json`
- Tests: `backend/tests/test_dashboard_summary.py`
- Baseline commit: `595b380d6111b59e727b01d978cf27ebc2b6a335`
- Validations: `npm run lint`, `npm run build`, `UV_CACHE_DIR=/private/tmp/uv-cache uv run --with pytest pytest tests/test_dashboard_summary.py -q`
- Review fixes: chats filtered by range, safe dashboard date labels, empty-date query handling, empty-product filter state, tenant switch resets.

### Completion Notes List

- Se agregó `/api/v1/dashboard/analytics` con series históricas tenant-scoped y filtros por fecha, usuario, estado, funnel, etapa y producto.
- La UI del Dashboard ahora muestra KPIs, filtros y gráficas reales con Recharts, más estados honestos de carga, vacío y error.
- Se preservó el resumen operativo de la historia 6.1 y se aisló la carga asíncrona con request-id guards para evitar respuestas obsoletas.
- Se añadió cobertura backend para aislamiento por tenant y comportamiento histórico filtrado.
- Se corrigieron los hallazgos de code review y se cerró el story con validación completa.

### File List

- `backend/app/dashboard/routes.py`
- `backend/app/dashboard/schemas.py`
- `backend/app/dashboard/service.py`
- `backend/tests/test_dashboard_summary.py`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/src/App.tsx`

### Review Findings

- [x] [Review][Patch] Chats "en el rango" usa totales del tenant, no el rango filtrado [backend/app/dashboard/service.py:196]
- [x] [Review][Patch] El eje de fechas del dashboard puede desplazarse al día anterior en zonas horarias negativas [frontend/src/App.tsx:2172]
- [x] [Review][Patch] El filtro de producto no se oculta ni se deshabilita cuando el tenant no tiene productos activos [frontend/src/App.tsx:4078]
- [x] [Review][Patch] Respuestas de citas en vuelo pueden reescribir el tenant actual [frontend/src/App.tsx:2494]
- [x] [Review][Patch] Refresh de citas no protege estado de error/carga contra respuestas obsoletas [frontend/src/App.tsx:2834]
- [x] [Review][Patch] El filtro de producto arrastra conversaciones con órdenes fuera del rango seleccionado [backend/app/dashboard/service.py:111]
- [x] [Review][Patch] Los tooltips de chats y ventas usan rótulos que no coinciden con los datos expuestos por Recharts [frontend/src/App.tsx:4150]
- [x] [Review][Patch] El filtro de usuario oculta assignees históricos cuando no hay más de un usuario activo [frontend/src/App.tsx:3903]
- [x] [Review][Patch] El filtro de producto oculta productos históricos inactivos aunque el backend acepta `product_id` [frontend/src/App.tsx:3905]
