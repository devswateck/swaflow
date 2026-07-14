---
baseline_commit: 595b380d6111b59e727b01d978cf27ebc2b6a335
---

# Story 7.1: Operar como superadmin con acceso auditado

Status: done

## Story

Como operador de Swateck,
Quiero operar como superadmin con acceso cross-tenant auditable,
Para poder dar soporte interno sin romper el aislamiento normal ni perder trazabilidad.

## Acceptance Criteria

1. Dado que un usuario tiene rol `superadmin` autorizado, cuando accede a datos o acciones de un tenant distinto al suyo, entonces el sistema permite la operacion como excepcion explicita y registra el acceso para auditoria.
2. Dado que un usuario no tiene rol `superadmin`, cuando intenta acceder a datos de otro tenant, entonces el backend responde `404` para recursos cross-tenant o `403` para permisos de modulo ausentes, sin revelar informacion de otra empresa.
3. Dado que un superadmin revisa o modifica datos operativos sensibles, cuando el backend confirma la accion, entonces queda evidencia auditable con actor, tenant objetivo, entidad afectada y metadata redactada.
4. Dado que la auditoria auxiliar falla, cuando la accion principal ya fue validada por el backend, entonces la operacion no se revierte y el fallo solo queda en logs internos.

**FR cubiertos:** FR140, FR141

## Tasks / Subtasks

- [x] Revisar y consolidar los puntos actuales de acceso superadmin en auth, users, companies y audit para confirmar el contrato real de excepcion auditable.
  - [x] Verificar `backend/app/auth/service.py` para preservar `is_superadmin`, `require_roles` y `require_module_access` como excepcion explicita y no como bypass generico.
  - [x] Verificar `backend/app/users/routes.py` y `backend/app/users/service.py` para mantener el acceso cross-tenant permitido solo a superadmin y seguir registrando la trazabilidad correcta.
  - [x] Verificar `backend/app/companies/routes.py` y `backend/app/companies/service.py` para mantener el acceso al perfil del tenant con `404` normal y auditoria de acceso superadmin.
  - [x] Revisar `backend/app/audit/service.py` para preservar redaccion de metadata y el patron best-effort sin romper la mutacion principal.
- [x] Endurecer la trazabilidad de accesos superadmin sin introducir un sistema nuevo de permisos.
  - [x] Reusar `record_superadmin_access` o `record_audit_best_effort` para dejar evidencia con actor, tenant objetivo, entidad y metadata redactada.
  - [x] Mantener `404` para recursos de otro tenant y `403` para permisos insuficientes en el mismo tenant.
  - [x] Evitar que un fallo auxiliar de auditoria invalide una operacion ya confirmada por el backend.
- [x] Agregar cobertura de regresion para el contrato de soporte interno.
  - [x] Probar un caso positivo de superadmin cross-tenant.
  - [x] Probar un caso negativo de usuario normal con `404`/`403` segun corresponda.
  - [x] Probar que la auditoria guarda `actor_user_id`, `actor_role`, `company_id`, `entity_type` y `entity_id`.
  - [x] Probar que la metadata persiste redactada y sin secretos.

## Dev Notes

### Business Context

- Esta historia cubre soporte interno de Swateck: acceso superadmin auditable, no una relajacion general del aislamiento multi-tenant.
- El objetivo es permitir operacion cross-tenant solo donde la regla de negocio ya lo autoriza.
- El panel avanzado de SuperUsuario sigue fuera de V1; no crear una superficie nueva para eso en esta historia.
- La auditoria debe servir para soporte y seguridad sin introducir un segundo sistema de permisos.

### Current Code State

- `backend/app/auth/service.py` ya define `is_superadmin`, `require_roles` y `require_module_access`, con excepcion explicita para superadmin.
- `backend/app/users/routes.py` ya permite que superadmin omita `company_id` para leer o modificar usuarios de otros tenants mediante el contrato actual.
- `backend/app/users/service.py` y `backend/app/companies/service.py` ya llaman a `record_superadmin_access` en accesos cross-tenant relevantes y conservan el contrato `404`/`403`.
- `backend/app/audit/service.py` ya centraliza `record_audit`, redaccion de metadata sensible, `record_audit_best_effort` y `record_superadmin_access`.
- `backend/app/audit/routes.py` ya lista logs solo del tenant actual con permiso de `settings`.
- `backend/app/main.py` ya incluye los routers de audit, users, companies y offboarding; no hace falta un router nuevo.
- `frontend/src/App.tsx` ya muestra labels honestos sobre superadmin y soporte; no existe una superficie dedicada de auditoria que deba crearse aqui.

### Related Prior Implementation

- La historia `1-11-operar-acceso-superadmin-y-auditoria-transversal` ya implemento el contrato base de superadmin, auditoria transversal y exportacion.
- Para esta historia, toma ese trabajo como precedente funcional y evita duplicar capas, rutas o helpers que ya existen.
- Si detectas brechas entre el contrato del epic 7 y el codigo actual, corrige la brecha minima necesaria y preserva el comportamiento ya aprobado.

### Critical Guardrails

- No debilitar la regla vigente: `404` para recursos de otro tenant y `403` para permisos de modulo faltantes en el mismo tenant.
- No crear un segundo sistema de identidad o permisos para superadmin; se reutiliza el contrato actual.
- No exponer secretos, tokens, firmas o credenciales en auditoria, logs, UI o respuestas API.
- No introducir datos falsos para auditoria o paneles de soporte.
- No permitir que una falla auxiliar de auditoria rompa una operacion ya confirmada por el backend.
- No ampliar el alcance a exportacion al retiro del tenant; eso pertenece a la historia 7.3.

### Implementation Guidance

- Reusar `record_superadmin_access` y `record_audit_best_effort` antes de crear cualquier logger paralelo.
- Mantener la excepcion superadmin pequena y explicita; no generalizar el acceso cross-tenant.
- Usar queries tenant-scoped y el patron de servicios actual, no accesos globales ad hoc.
- Si una ruta sensible necesita auditabilidad adicional, registrar el evento con metadata redactada y seguir devolviendo la respuesta de negocio correcta.
- Si hay que tocar frontend, limitarlo a labels honestos dentro del shell existente. No abrir rutas nuevas.

### Suggested File Targets

- Backend likely to change:
  - `backend/app/auth/service.py`
  - `backend/app/users/routes.py`
  - `backend/app/users/service.py`
  - `backend/app/companies/routes.py`
  - `backend/app/companies/service.py`
  - `backend/app/audit/service.py`
  - `backend/tests/test_superadmin_offboarding.py`
  - `backend/tests/test_user_permissions.py`
- Frontend likely to change only if a support label must be aligned:
  - `frontend/src/App.tsx`

### Testing Requirements

- Probar que superadmin puede cruzar tenant solo donde el contrato lo permite.
- Probar que el resto de usuarios mantiene `404`/`403` y no recibe informacion de otra empresa.
- Probar que la auditoria registra actor, tenant objetivo y entidad afectada.
- Probar que la metadata de auditoria queda redactada y sin secretos.
- Probar que un fallo de auditoria auxiliar no invalida la mutacion principal.
- Probar compatibilidad con la suite SQLite actual y con el contrato multi-tenant vigente.

### Project Structure Notes

- Mantener el aislamiento por `company_id` en todas las consultas de negocio.
- Reusar los dominios existentes de `users`, `auth`, `companies` y `audit`; no agregar un subsistema nuevo.
- Si se amplia la bateria de regresion, preferir el suite existente de superadmin antes que una copia paralela innecesaria.
- Cualquier salida visual debe seguir la superficie unica ya existente; no crear un router nuevo.

## References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 7, historia 7.1, criterios de aceptacion]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - superadmin y soporte interno]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/decision-audit.md` - superadmin cross-tenant y retencion]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/review-technical-product.md` - riesgos de auditoria y provisionamiento]
- [Source: `backend/app/auth/service.py` - excepcion explicita de superadmin y helpers de acceso]
- [Source: `backend/app/users/routes.py` - acceso cross-tenant para superadmin en usuarios]
- [Source: `backend/app/users/service.py` - auditoria y acceso superadmin]
- [Source: `backend/app/companies/routes.py` - acceso superadmin a perfil de tenant]
- [Source: `backend/app/companies/service.py` - auditoria de acceso y contrato `404`/`403`]
- [Source: `backend/app/audit/service.py` - redaccion, `record_audit_best_effort`, `record_superadmin_access`]
- [Source: `backend/app/audit/routes.py` - lectura auditada tenant-scoped]
- [Source: `frontend/src/App.tsx` - superficie actual de superadmin y labels de soporte]
- [Source: `_bmad-output/implementation-artifacts/1-11-operar-acceso-superadmin-y-auditoria-transversal.md` - historia previa relacionada y patrones ya implementados]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Se resolvio el siguiente backlog desde `sprint-status.yaml`: `7-1-operar-como-superadmin-con-acceso-auditado`.
- Se cargo el contexto persistente de `project-context.md`, el epic 7 completo, el PRD, `decision-audit.md`, `review-technical-product.md`, la arquitectura frontend y la UX de experiencia.
- Se confirmo que el repo ya tiene la excepcion superadmin, helpers de auditoria y soporte cross-tenant en users y companies; esta historia documenta y blinda ese contrato para regresion.
- Se tomo la historia `1-11-operar-acceso-superadmin-y-auditoria-transversal` como precedente funcional para no duplicar soluciones ni abrir nuevas superficies.
- Se valido el contrato con `backend/.venv/bin/python -m pytest backend/tests/test_superadmin_offboarding.py backend/tests/test_user_permissions.py -q` (`25 passed`).
- Se cerro el hueco de regresion del hallazgo: `record_superadmin_access` ahora es best-effort real y no rompe el flujo si la auditoria auxiliar falla.
- Se agrego una prueba de integracion para confirmar que el acceso cross-tenant de superadmin a companias sigue respondiendo `200` aunque falle la persistencia de auditoria.
- Se valido la regresion con `PYTHONPATH=backend /private/tmp/swaflow-venv/bin/pytest backend/tests/test_superadmin_offboarding.py backend/tests/test_user_permissions.py -q` (`26 passed`).

### Completion Notes List

- Historia creada para epic 7 con foco en acceso cross-tenant auditable.
- Se definieron criterios de aceptacion, tareas, guardrails, pruebas y file targets sin introducir una superficie paralela innecesaria.
- Se dejo el alcance separado de la historia 7.3 para que la exportacion al retiro del tenant se desarrolle como trabajo posterior.
- El codigo ya cumplia el contrato esperado; no fue necesario modificar fuentes de aplicacion para cerrar esta historia, solo validar y documentar el alcance.
- Se reforzo el contrato para que un fallo auxiliar de auditoria no pueda romper el acceso superadmin cross-tenant.
- Se agrego cobertura de regresion directa sobre el flujo de `companies` para el caso de auditoria fallida.

### File List

- `_bmad-output/implementation-artifacts/7-1-operar-como-superadmin-con-acceso-auditado.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/app/audit/service.py`
- `backend/tests/test_superadmin_offboarding.py`

## Change Log

- 2026-07-13: Validado el contrato superadmin cross-tenant y la auditoria best-effort existente; se cerraron tareas, se confirmo la cobertura de regresion y no fueron necesarios cambios de codigo adicionales para esta historia.
- 2026-07-13: Resuelto el hallazgo de revision sobre resiliencia de auditoria superadmin; `record_superadmin_access` ahora absorbe fallos auxiliares y existe regresion que verifica que el acceso cross-tenant sigue funcionando si la auditoria falla.
