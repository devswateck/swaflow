---
baseline_commit: 34029c557dd621508aec915ae1b0fea012ce5436
---

# Story 1.11: Operar acceso superadmin y auditoria transversal

Status: done

## Story

Como operador de Swateck,
Quiero acceder a tenants como superadmin con trazabilidad completa y exportar sus gestiones cuando se retire,
Para que pueda dar soporte interno sin romper el aislamiento normal ni perder evidencia operativa.

## Acceptance Criteria

1. Dado que un usuario tiene rol `superadmin` autorizado, cuando accede a datos o acciones de un tenant distinto al suyo, entonces el sistema permite la operacion como excepcion explicita, registra el acceso para auditoria y conserva el aislamiento normal para cualquier usuario que no sea superadmin.
2. Dado que un usuario no tiene rol `superadmin`, cuando intenta acceder a datos de otro tenant, entonces el backend responde `404` para recursos de otro tenant o `403` para permisos de modulo ausentes, sin revelar informacion de otra empresa.
3. Dado que ocurren cambios criticos o sensibles en permisos, integraciones, credenciales, IA, funnels, mensajes, ordenes, pagos, citas o reasignaciones de chat, cuando el backend confirma la accion, entonces registra auditoria/eventos con actor, tenant, tipo de entidad y metadata redactada, sin persistir secretos completos ni romper el flujo principal.
4. Dado que un tenant se retira y un operador autorizado solicita la exportacion, cuando Swaflow genera el paquete, entonces entrega un archivo ZIP con un TXT por modulo, filas delimitadas por pipe `|` y encabezados de columnas, incluyendo el conjunto minimo de datos historicos y excluyendo secretos, tokens o credenciales en claro.
5. Dado que el frontend muestra superficies administrativas o de soporte, cuando el usuario revisa el estado de superadmin, auditoria o exportacion, entonces ve labels honestos y V1 claros sin inventar registros, contadores o datos de otra empresa.

**FR cubiertos:** FR140, FR141, FR142, FR159, FR160, FR175, FR176, FR177

## Tasks / Subtasks

- [x] Auditar los puntos actuales de superadmin, auditoria y exportacion para confirmar el contrato real.
  - [x] Revisar `backend/app/auth/service.py`, `backend/app/users/routes.py`, `backend/app/users/service.py` y `backend/app/users/permissions.py` para preservar la excepcion superadmin y el contrato `404`/`403`.
  - [x] Revisar `backend/app/audit/service.py`, `backend/app/audit/routes.py` y `backend/app/events/service.py` para entender como se registran hoy auditoria y eventos.
  - [x] Confirmar en `frontend/src/App.tsx` que el estado de superadmin ya existe y que no hay una segunda superficie de auditoria/exportacion que deba preservarse.
- [x] Endurecer el acceso superadmin como excepcion explicita y auditable.
  - [x] Mantener la capacidad de cruzar tenant solo para `superadmin` y solo donde la regla de negocio lo permita.
  - [x] Registrar acceso y accion sensible con `actor_user_id`, `actor_role`, `company_id` objetivo y entidad afectada.
  - [x] Preservar `404` para cross-tenant en usuarios normales y `403` para permisos de modulo insuficientes en el mismo tenant.
- [x] Expandir la auditoria transversal de cambios criticos.
  - [x] Registrar cambios criticos de permisos, integraciones, credenciales, IA, funnels, mensajes, ordenes, pagos, citas y reasignaciones de chat.
  - [x] Redactar secretos, tokens, firmas y credenciales en metadata, respuestas y logs.
  - [x] Mantener la auditoria tenant-scoped y evitar que una falla auxiliar invalide una operacion ya confirmada por backend.
- [x] Implementar el paquete de exportacion por retiro del tenant.
  - [x] Crear un servicio de exportacion/offboarding que construya un ZIP usando librerias de la stdlib cuando sea posible.
  - [x] Generar un TXT por modulo con filas `|` y encabezados consistentes.
  - [x] Incluir el minimo historico esperado: contactos, conversaciones/mensajes, ordenes, metadatos de pagos, citas, eventos, snapshot de productos, inventario/reservas, actividad de usuarios/auditoria, configuraciones de integraciones sin secretos y assets cargados.
  - [x] Exponer la generacion/descarga solo a operadores autorizados de Swateck o rutas equivalentes de soporte.
- [x] Alinear la superficie frontend con el alcance real de soporte.
  - [x] Reusar la superficie existente en `frontend/src/App.tsx` para mostrar el estado de superadmin y cualquier entrada de auditoria/exportacion.
  - [x] Mantener labels honestos, sin datos inventados ni contadores ficticios.
  - [x] Evitar introducir un router nuevo o un flujo paralelo solo para esta historia.
- [x] Agregar cobertura de regresion.
  - [x] Probar acceso superadmin cross-tenant y las fronteras `404`/`403`.
  - [x] Probar que la auditoria redacta secretos y conserva el tenant correcto.
  - [x] Probar que el ZIP de exportacion tiene la forma esperada, incluye un TXT por modulo y no expone secretos.
  - [x] Probar compilacion/lint del frontend si la superficie de soporte cambia.

## Dev Notes

### Business Context

- Esta historia cubre el frente de soporte interno de Swateck: acceso superadmin auditable, trazabilidad transversal de cambios y exportacion al retiro del tenant.
- El acceso superadmin es una excepcion explicita, no una relajacion general del aislamiento multi-tenant.
- El paquete de exportacion existe para offboarding y soporte documental; no debe convertirse en un segundo sistema de verdad.
- La exportacion debe cubrir la informacion operativa ya registrada por el backend, no solo una parte cosmetica del tenant.

### Current Code State

- `backend/app/auth/service.py` ya define `is_superadmin`, `require_roles` y `require_module_access`, con excepcion explicita para superadmin.
- `backend/app/users/routes.py` ya permite que superadmin omita `company_id` para leer o modificar usuarios de otros tenants mediante el contrato actual.
- `backend/app/users/service.py` ya preserva roles privilegiados del tenant y escribe auditoria en altas, cambios de usuario, reseteos y desactivaciones.
- `backend/app/users/permissions.py` ya distingue modulos permitidos, roles privilegiados y acceso por modulo.
- `backend/app/audit/models.py`, `backend/app/audit/service.py` y `backend/app/audit/routes.py` ya existen para auditoria tenant-scoped, pero hoy solo cubren lectura de logs del propio tenant con permiso de `settings`.
- `backend/app/events/service.py` y `backend/app/events/dispatcher.py` ya manejan eventos de negocio y despacho externo, lo que sirve como referencia para registrar trazabilidad sin inventar una cola nueva.
- `backend/app/models.py` ya expone `AuditLog` y `Event` para descubrimiento de metadata en SQLAlchemy.
- `frontend/src/App.tsx` ya muestra una pequena referencia a superadmin en la vista de configuracion, pero no existe una superficie completa de auditoria/exportacion.
- No existe hoy un modulo dedicado de exportacion al retiro del tenant; esta historia debe definirlo y mantenerlo coherente con el ADR de auditoria y outbox.

### Critical Guardrails

- No debilitar la regla vigente: `404` para recursos de otro tenant y `403` para permisos de modulo faltantes en el mismo tenant.
- No crear un segundo sistema de identidad o permisos para superadmin; se reutiliza el contrato actual.
- No exponer secretos, tokens, firmas o credenciales en ZIPs, auditoria, logs, UI o respuestas API.
- No introducir datos falsos para auditoria, exportacion o paneles de soporte.
- No hacer que la exportacion dependa de n8n, de un worker nuevo o de una cola adicional si no existe decision explicita.
- No permitir que una falla auxiliar de auditoria/exportacion rompa una operacion ya confirmada por el backend.

### Implementation Guidance

- Reusar `record_audit` y los modelos existentes siempre que sea posible, antes de crear nuevas tablas o subsistemas.
- Si se necesita una nueva frontera de dominio para offboarding/exportacion, mantenerla pequena y centrada en `ZIP + TXT` usando la estructura de la app por dominio.
- Preferir metadatos minimales y redactados en auditoria; la informacion sensible debe quedarse fuera del payload persistido.
- Para exportacion, usar formatos simples y verificables: encabezado de columnas + filas `|` para cada modulo.
- Mantener el frontend dentro del shell actual; cualquier vista de soporte debe ser una extension del layout existente, no una reescritura.
- Si hay que leer muchos modelos para exportar, usar queries tenant-scoped y ordenar el contenido de forma deterministica para facilitar pruebas.

### Suggested File Targets

- Backend likely to change:
  - `backend/app/users/routes.py`
  - `backend/app/users/service.py`
  - `backend/app/users/permissions.py`
  - `backend/app/audit/service.py`
  - `backend/app/audit/routes.py`
  - `backend/app/events/service.py`
  - `backend/app/main.py`
  - `backend/app/exports/service.py` or `backend/app/offboarding/service.py` if a dedicated export module is needed
  - `backend/app/exports/routes.py` or `backend/app/offboarding/routes.py` if the export is exposed as an endpoint
  - `backend/tests/test_tenant_and_orders.py` or a focused regression file for superadmin/export behavior
- Frontend likely to change:
  - `frontend/src/App.tsx`

### Testing Requirements

- Probar que superadmin puede cruzar tenant solo donde el contrato lo permite y que el resto de usuarios mantiene `404`/`403`.
- Probar que la auditoria registra actor, tenant y entidad, y que la metadata redacta secretos y credenciales.
- Probar que los cambios sensibles generan evidencia auditable sin romper el flujo principal.
- Probar que la exportacion genera un ZIP valido con un TXT por modulo y con contenido delimitado por pipe.
- Probar que el ZIP no contiene secretos, tokens o credenciales en claro.
- Probar compatibilidad con la suite SQLite actual y con supuestos compatibles con MySQL.

### Project Structure Notes

- Mantener el aislamiento por `company_id` en todas las consultas de negocio.
- Reusar los dominios existentes de `users`, `audit`, `events` y, si hace falta, una frontera minima de `exports` o `offboarding`.
- No agregar un router nuevo al frontend solo para mostrar soporte; preservar la app Vite/React de superficie unica.
- Cualquier exportacion debe ser verificable y reproducible con el set de datos que el backend ya conserva.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 7, historias 7.1, 7.2 y 7.3, FR140-FR142, FR159-FR160, FR175-FR177]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - superadmin, auditoria operativa y retencion/exportacion]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/decision-audit.md` - retencion indefinida y paquete de exportacion al retiro]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/review-technical-product.md` - contenido minimo del export package]
- [Source: `docs/adr/0001-security-and-multi-tenant-enforcement.md` - 404 cross-tenant, 403 permisos, secretos cifrados]
- [Source: `docs/adr/0004-integrations-events-audit-and-outbox.md` - audit trails, outbox y fronteras de integraciones]
- [Source: `backend/app/auth/service.py` - excepcion explicita de superadmin]
- [Source: `backend/app/users/routes.py` - acceso superadmin cross-tenant en usuarios]
- [Source: `backend/app/users/service.py` - auditoria y preservacion de roles privilegiados]
- [Source: `backend/app/audit/service.py` - helper actual de auditoria]
- [Source: `backend/app/audit/routes.py` - lectura auditada tenant-scoped]
- [Source: `backend/app/events/service.py` - referencia de trazabilidad de eventos]
- [Source: `frontend/src/App.tsx` - superficie actual de superadmin en configuracion]
- [Source: `_bmad-output/implementation-artifacts/1-10-configurar-notificaciones-por-correo-y-webhooks-salientes.md` - patron previo de historia de integraciones y auditoria]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Historia seleccionada automaticamente como el siguiente backlog en `sprint-status.yaml`: `1-11-operar-acceso-superadmin-y-auditoria-transversal`.
- Se revisaron el epic 7, el PRD, `decision-audit.md`, `review-technical-product.md`, `open-questions.md`, las ADRs de seguridad/auditoria, el backend actual de users/audit/events y la superficie existente de frontend.
- Se confirmo que la aplicacion ya soporta superadmin como excepcion explicita, pero no existe aun una historia de exportacion al retiro ni una superficie dedicada de auditoria/exportacion en frontend.
- La historia se definio para cubrir el frente completo de soporte interno: acceso superadmin auditable, auditoria transversal y exportacion ZIP/TXT al retiro del tenant.
- Implementacion completada con auditoria de acceso `superadmin` en company/user routes, redaccion recursiva de metadata sensible, un nuevo modulo `offboarding` para exportacion ZIP/TXT y un panel honesto de soporte/exportacion en el frontend.
- Se corrigieron hallazgos de revision para auditar reasignaciones de chat, mensajes, citas, cambios de IA y funnels, y para ampliar el export al incluir AI, funnels y WhatsApp sin exponer secretos.
- Validacion ejecutada: `./backend/.venv/bin/python -m py_compile backend/app/audit/service.py backend/app/companies/service.py backend/app/companies/routes.py backend/app/users/service.py backend/app/users/routes.py backend/app/conversations/service.py backend/app/conversations/routes.py backend/app/ai/service.py backend/app/ai/routes.py backend/app/funnels/service.py backend/app/funnels/routes.py backend/app/appointments/service.py backend/app/appointments/routes.py backend/app/offboarding/service.py backend/app/offboarding/routes.py backend/app/main.py backend/tests/test_superadmin_offboarding.py backend/tests/test_tenant_and_orders.py`, `./backend/.venv/bin/python -m pytest backend/tests/test_superadmin_offboarding.py -q` (`4 passed`), `./backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py backend/tests/test_user_permissions.py backend/tests/test_whatsapp_setup.py -q` (`102 passed`).

### Completion Notes

- Se implemento la excepcion auditable de `superadmin` para accesos cross-tenant en companys y users, con logs de acceso separados de la auditoria de negocio.
- Se centralizo la redaccion de metadata sensible para que audit logs no conserven secretos, tokens, firmas ni credenciales en claro.
- Se agregaron auditorias best-effort para cambios sensibles en IA, funnels, conversaciones, mensajes y citas, manteniendo el flujo principal aun si la auditoria auxiliar falla.
- Se agrego el modulo `offboarding` con descarga ZIP para retiro de tenant, incluyendo un TXT por modulo con formato pipe `|`, encabezados consistentes y contenido historico de contactos, conversaciones, mensajes, ordenes, citas, eventos, productos, inventario, auditoria, integraciones, WhatsApp, AI y funnels.
- Se preservo el panel honesto de "Soporte y exportacion" en el frontend, dentro de la pantalla existente, sin introducir nuevas rutas ni datos falsos.
- Se verifico la compatibilidad con la suite de backend afectada por los cambios y con la exportacion ampliada.
- Se resolvieron los hallazgos finales de code review moviendo auditoria de integraciones y ordenes a best-effort post-commit.

### File List

- `_bmad-output/implementation-artifacts/1-11-operar-acceso-superadmin-y-auditoria-transversal.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- backend/app/ai/routes.py
- backend/app/ai/service.py
- backend/app/appointments/routes.py
- backend/app/appointments/service.py
- `backend/app/audit/service.py`
- `backend/app/companies/routes.py`
- `backend/app/companies/service.py`
- `backend/app/conversations/routes.py`
- `backend/app/conversations/service.py`
- `backend/app/main.py`
- `backend/app/offboarding/__init__.py`
- `backend/app/offboarding/routes.py`
- `backend/app/offboarding/service.py`
- `backend/app/funnels/routes.py`
- `backend/app/funnels/service.py`
- `backend/app/users/routes.py`
- `backend/app/users/service.py`
- `backend/tests/test_tenant_and_orders.py`
- `backend/tests/test_superadmin_offboarding.py`
- `frontend/src/App.tsx`

## Change Log

- 2026-06-29: Se creo la historia 1.11 para superadmin, auditoria transversal y exportacion al retiro del tenant, alineada con el epic 7, el PRD y las ADRs vigentes.
- 2026-06-29: Se implemento la historia 1.11 con auditoria explicita de accesos superadmin, exportacion ZIP/TXT al retiro del tenant, redaccion de metadata sensible y soporte visual honesto en frontend.
- 2026-06-29: Se corrigieron los hallazgos de revision: auditoria best-effort para cambios sensibles, ampliacion del export a AI/funnels/WhatsApp, y cobertura adicional para reasignaciones de chat y cambios operativos.

### Review Findings

- [x] [Review][Patch] Integration and webhook writes still fail hard on audit errors [backend/app/integrations/service.py:31] — `create_integration()`, `update_integration()`, `create_outbound_webhook()`, `update_outbound_webhook()` and `delete_outbound_webhook()` still call `record_audit(...)` before the business commit. A failure in the audit insert can still roll back a valid integration/credential change, which violates AC 3's requirement to keep the main flow alive when audit fails.
- [x] [Review][Patch] Order and payment mutations are still transactionally coupled to audit inserts [backend/app/orders/service.py:131] — `create_order()`, `_mark_order_paid()`, `cancel_order()` and `update_payment_status()` still persist audit rows with `record_audit(...)` before `db.commit()`. If the audit write fails, an otherwise valid order or payment-state change can be lost, which conflicts with AC 3 and the no-breaking-flow guardrail.
