---
baseline_commit: 595b380d6111b59e727b01d978cf27ebc2b6a335
---

# Story 6.3: Mantener aislamiento y rendimiento visible en el Dashboard

Status: done

## Story

Como usuario del tenant,
quiero que el Dashboard sea rapido y respete el aislamiento multi-tenant,
para confiar en la informacion sin ver datos de otras empresas ni sentir una interfaz congelada.

## Acceptance Criteria

1. Dado que el Dashboard consulta resumen o analitica, cuando calcula metricas o cambia filtros, entonces cada consulta queda filtrada por `company_id` y no expone datos de otro tenant bajo ningun flujo normal.
2. Dado que el usuario abre o refresca el Dashboard, cuando llegan las metricas iniciales o los cambios de filtro, entonces la vista responde dentro del objetivo de experiencia del producto bajo volumen normal y mantiene estados de carga/skeleton en lugar de bloquear la UI.
3. Dado que cambian ventas o citas en otros modulos, cuando el Dashboard vuelve a leer la fuente de verdad, entonces refleja esos cambios sin mezclar informacion entre tenants ni arrastrar resultados obsoletos.
4. Dado que el Dashboard ya fue cargado o refrescado, cuando se muestra la cabecera de la vista, entonces la UI deja visible la frescura de los datos con un timestamp breve tipo `Actualizado hace N min` y conserva un refresh manual accionable.

## Tasks / Subtasks

- [x] Auditar y endurecer el contrato de Dashboard para que la ruta siga siendo tenant-scoped y mas eficiente.
  - [x] Revisar `backend/app/dashboard/service.py` para confirmar que summary y analytics preservan el filtro por `company_id` en todas las ramas.
  - [x] Reemplazar materializacion innecesaria de listas completas por agregaciones SQL o proyecciones mas estrechas donde no cambie la semantica de salida.
  - [x] Mantener intactos los filtros existentes por fecha, usuario, estado, funnel, etapa y producto.
- [x] Visibilizar la frescura y el estado operativo del Dashboard en la UI.
  - [x] Exponer en `frontend/src/App.tsx` un timestamp legible de ultima actualizacion para summary y analitica.
  - [x] Conservar el boton de refresco manual y el estado de carga para que la percepcion de rendimiento sea clara.
  - [x] No cambiar la estructura general de la pagina ni crear un router nuevo.
- [x] Blindar el rendimiento con indices y reglas compatibles con MySQL si el analisis de consultas lo requiere.
  - [x] Verificar si hacen falta indices compuestos sobre `company_id` + columnas de rango/filtro usadas por Dashboard.
  - [x] Si se agregan indices, hacerlo con migracion Alembic compatible con MySQL y sin tocar migraciones antiguas.
  - [x] No introducir colas, workers ni procesamiento asincronico nuevo para resolver este problema.
- [x] Cubrir la historia con pruebas de aislamiento, regresion y comportamiento visible.
  - [x] Extender `backend/tests/test_dashboard_summary.py` o crear una prueba especifica para validar que el analytics sigue siendo tenant-scoped despues de la optimizacion.
  - [x] Probar que el Dashboard conserva la semantica de rangos y no regresa resultados fuera de fecha tras el refactor.
  - [x] Verificar `npm run lint`, `npm run build` y la suite backend relevante para dashboard.

## Dev Notes

### Contexto del producto

- Epic 6: Dashboard y Visibilidad Operativa.
- Esta historia es la capa de endurecimiento del Dashboard, no un redisenio funcional.
- FR relevantes: FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008.
- NFR relevantes: NFR-006, NFR-007, NFR-011.
- UX relevante: el Dashboard debe mostrar estado desactualizado de forma honesta con timestamp breve y refresh manual.

### Estado actual del codigo

- `backend/app/dashboard/routes.py` ya expone `/dashboard/summary` y `/dashboard/analytics` con acceso protegido por `require_module_access("dashboard")`.
- `backend/app/dashboard/service.py` ya filtra por `company_id`, respeta la zona horaria del tenant y devuelve series reales; hoy, sin embargo, materializa conversaciones, mensajes, ordenes y citas en memoria antes de agrupar.
- `backend/app/dashboard/schemas.py` ya define el resumen y la serie historica que consume el frontend.
- `frontend/src/App.tsx` ya concentra el `DashboardPage`, request-id guards, el refresh manual, el reset al cambiar de tenant y los estados honestos de carga/error.
- `frontend/src/App.tsx` ya usa Recharts y no necesita otra libreria de graficas para esta historia.
- `backend/tests/test_dashboard_summary.py` ya cubre aislamiento tenant y el contrato historico base.
- Los modelos de negocio tienen `company_id` por `TenantMixin`, pero las columnas temporales relevantes para Dashboard no estan necesariamente cubiertas por indices compuestos.

### Guardrails criticos

- No cambiar el modelo multi-tenant ni relajar el filtro por `company_id`.
- No usar superadmin como excepcion para esta historia.
- No introducir mocks, datos de ejemplo ni caches inventadas para aparentar rendimiento.
- No mover el Dashboard a un router nuevo ni separar el shell por anticipacion.
- No usar procesamiento asincronico nuevo, colas o workers para resolver la latencia del Dashboard.
- Mantener todo el copy visible en espanol.
- Si un cambio toca SQL o indices, debe seguir siendo compatible con MySQL.

### Arquitectura y estructura

- Mantener `frontend/src/App.tsx` como superficie principal del Dashboard mientras el shell siga concentrado ahi.
- Si se agrega metadata de frescura, preferir extender el contrato actual de forma minima y serializable.
- Si la optimizacion requiere indices, priorizar `company_id` + `created_at`/`last_message_at`/`scheduled_at`/`status`/`assigned_user_id`/`funnel_id`/`product_id` segun el plan de consultas real.
- No sobrecargar `/dashboard/summary` con filtros historicos adicionales; esta historia debe endurecer lo existente, no mezclar contratos.
- Preservar la semantica actual de 404 para cruces de tenant y 422 para rangos de fechas invalidos.

### Detalles funcionales a respetar

- El Dashboard debe seguir mostrando KPI primero, analitica despues.
- El refresh manual sigue disponible y no debe perder el estado de filtros actual.
- Los estados vacios, loading y error deben seguir siendo honestos, no decorativos.
- La frescura visible debe ser breve y util, no un banner invasivo.
- El sistema no debe recalcular en frontend lo que el backend ya considera fuente de verdad.
- Si una respuesta tarda o llega fuera de orden, el estado actual no debe ser sobrescrito por resultados obsoletos.

### Testing Requirements

- Probar que el contrato historico sigue devolviendo solo datos del tenant autenticado.
- Probar que un cambio de refactor no altera la semantica de rango de fechas ni el shape de la respuesta.
- Probar que la UI conserva el refresh manual, el estado de carga y el indicador de frescura.
- Verificar que el dashboard sigue compiliando y que la suite de backend relevante no regresa leakage cross-tenant.
- No agregar asserts de timing fragiles; si se valida performance, hacerlo con smoke test local o inspeccion de consultas, no con benchmarks unitarios inestables.

### Previous Story Intelligence

- La historia 6.1 estabilizo el resumen operativo del Dashboard y la recarga al entrar o cambiar de tenant.
- La historia 6.2 agrego las graficas, filtros y request-id guards para evitar respuestas obsoletas.
- Esta historia debe reutilizar esos patrones y endurecerlos, no reescribirlos.
- El flujo de Dashboard ya depende de la fuente de verdad del backend; mantener eso evita regresiones de consistencia.

### Git Intelligence Summary

- El trabajo reciente introdujo el contrato de analytics del Dashboard, tests de aislamiento y guards de concurrencia.
- No existe una capa de performance paralela; esta historia debe optimizar el camino actual, no duplicarlo.
- Los cambios recientes en frontend y backend muestran que el area ya es sensible a regresiones de tenant switch y refresh, asi que cualquier refactor debe ir acompanado de pruebas.

### Latest Tech Information

- No se requiere upgrade de dependencias para esta historia.
- `Recharts` ya esta aprobado y en uso; no introducir otra libreria de graficas.
- El stack vigente del proyecto sigue siendo la referencia para esta historia: React 18/Vite/TypeScript/Tailwind en frontend y FastAPI/SQLAlchemy 2/MySQL en backend.

### Project Structure Notes

- Frontend principal: `frontend/src/App.tsx`.
- Dashboard backend: `backend/app/dashboard/routes.py`, `backend/app/dashboard/service.py`, `backend/app/dashboard/schemas.py`.
- Pruebas de dashboard: `backend/tests/test_dashboard_summary.py` o un archivo nuevo si la cobertura de performance necesita separarse.
- Migraciones, si aplican: `backend/migrations/versions/`.
- No crear un router nuevo en frontend ni mover el shell a una arquitectura paralela.

### References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - `## Epic 6: Dashboard y Visibilidad Operativa`, `### Historia 6.3: Mantener aislamiento y rendimiento visible en el Dashboard`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, NFR-006, NFR-007, NFR-011]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - `Dashboard desactualizado`, `KPI card`, `Chart panel`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - secciones `Gráficas`, `Patrones de componentes`, `Patrones de estado`, `Flujo de implementación`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/dashboard/routes.py`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/dashboard/service.py`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/dashboard/schemas.py`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_dashboard_summary.py`]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

### Completion Notes List

- Reemplace la hidratacion completa de ORM en Dashboard analytics por proyecciones estrechas y agregaciones SQL tenant-scoped.
- Agregue indices compuestos compatibles con MySQL para `conversations`, `messages`, `orders` y `appointments` segun las rutas de consulta del Dashboard.
- Expuse timestamps de frescura separados para resumen y analitica en `frontend/src/App.tsx` sin cambiar el router ni el contrato de API.
- Resuelto hallazgos de revision: skeleton real para el resumen operativo, refresh completo de summary + analytics al mutar otros modulos, indice compuesto para `order_items`, etiquetas de fecha estables y 422 para timezone invalido en analytics.
- Corregi el orden de calculo en `backend/app/dashboard/service.py` para evitar referencias adelantadas en la agregacion diaria y alinear la semantica de citas por estado.
- Validado con `backend/tests/test_dashboard_summary.py`, `backend/tests/test_tenant_and_orders.py`, `npm run lint` y `npm run build`.
- Code review completado sin hallazgos accionables.

### Change Log

- 2026-07-13: Optimice el contrato de Dashboard para evitar hidratar entidades completas innecesariamente.
- 2026-07-13: Anadi indicadores de frescura visibles para resumen y analitica.
- 2026-07-13: Incorpore indices de soporte para los patrones de consulta del Dashboard.
- 2026-07-13: Verifique la implementacion con pruebas backend y build/lint del frontend.
- 2026-07-13: Addressed code review findings - 4 items resolved.
- 2026-07-13: Cerrado el seguimiento de revision restante corrigiendo la agregacion y alineando las expectativas de citas por estado.
- 2026-07-13: Code review completed cleanly with no findings.

### File List

- `_bmad-output/implementation-artifacts/6-3-mantener-aislamiento-y-rendimiento-visible-en-el-dashboard.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/app/appointments/models.py`
- `backend/app/companies/service.py`
- `backend/app/conversations/models.py`
- `backend/app/dashboard/service.py`
- `backend/app/messages/models.py`
- `backend/app/orders/models.py`
- `backend/migrations/versions/20260713_0022_dashboard_performance_indexes.py`
- `backend/tests/test_dashboard_summary.py`
- `backend/tests/test_tenant_and_orders.py`
- `frontend/src/App.tsx`
