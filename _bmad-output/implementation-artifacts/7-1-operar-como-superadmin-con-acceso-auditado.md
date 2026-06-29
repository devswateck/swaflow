---
baseline_commit: 34029c557dd621508aec915ae1b0fea012ce5436
---

# Story 7.1: Operar como superadmin con acceso auditado

Status: backlog

## Story

Como operador de Swateck,
Quiero operar como superadmin con acceso cross-tenant auditable,
Para poder dar soporte interno sin romper el aislamiento normal ni perder trazabilidad.

## Acceptance Criteria

1. Dado que un usuario tiene rol `superadmin` autorizado, cuando accede a datos o acciones de un tenant distinto al suyo, entonces el sistema permite la operacion como excepcion explicita y registra el acceso para auditoria.
2. Dado que un usuario no tiene rol `superadmin`, cuando intenta acceder a datos de otro tenant, entonces el backend responde `404` para recursos cross-tenant o `403` para permisos de modulo ausentes, sin revelar informacion de otra empresa.
3. Dado que un superadmin revisa o modifica datos operativos sensibles, cuando el backend confirma la accion, entonces queda evidencia auditable con actor, tenant objetivo, entidad afectada y metadata redactada.
4. Dado que la auditoria auxiliar falla, cuando la accion principal ya fue validada por el backend, entonces la operacion no se revierte y el fallo solo queda en logs internos.

**FR cubiertos:** FR140, FR141, FR142

## Tasks / Subtasks

- [ ] Revisar los puntos actuales de acceso superadmin en auth, users y companies para confirmar el contrato real de excepcion auditable.
  - [ ] Verificar `backend/app/auth/service.py` para preservar `is_superadmin`, `require_roles` y `require_module_access` como excepcion explicita.
  - [ ] Verificar `backend/app/users/routes.py` y `backend/app/users/service.py` para mantener el acceso cross-tenant permitido solo a superadmin.
  - [ ] Revisar cualquier ruta adicional con acceso cross-tenant para preservar el mismo contrato de aislamiento.
- [ ] Endurecer la trazabilidad de accesos superadmin sin romper el flujo principal.
  - [ ] Reusar `record_superadmin_access` o `record_audit_best_effort` para dejar evidencia con actor, tenant objetivo, entidad y metadata redactada.
  - [ ] Mantener `404` para recursos de otro tenant y `403` para permisos insuficientes en el mismo tenant.
  - [ ] Evitar que un fallo auxiliar de auditoria invalide una operacion ya confirmada por el backend.
- [ ] Agregar cobertura de regresion para el contrato de soporte interno.
  - [ ] Probar un caso positivo de superadmin cross-tenant.
  - [ ] Probar un caso negativo de usuario normal con `404`/`403` segun corresponda.
  - [ ] Probar que la auditoria guarda `actor_user_id`, `actor_role`, `company_id`, `entity_type` y `entity_id`.
  - [ ] Probar que la metadata persiste redactada y sin secretos.

## Dev Notes

### Business Context

- Esta historia cubre soporte interno de Swateck: acceso superadmin auditable, no una relajacion general del aislamiento multi-tenant.
- El objetivo es permitir operacion cross-tenant solo donde la regla de negocio ya lo autoriza.
- La auditoria debe servir para soporte y seguridad sin introducir un segundo sistema de permisos.

### Current Code State

- `backend/app/auth/service.py` ya define `is_superadmin`, `require_roles` y `require_module_access`, con excepcion explicita para superadmin.
- `backend/app/users/routes.py` ya permite que superadmin omita `company_id` para leer o modificar usuarios de otros tenants mediante el contrato actual.
- `backend/app/audit/service.py` ya centraliza `record_audit`, redaccion de metadata sensible, `record_audit_best_effort` y `record_superadmin_access`.
- `docs/adr/0001-security-and-multi-tenant-enforcement.md` fija el contrato `404` cross-tenant y `403` para permisos faltantes.
- `docs/adr/0004-integrations-events-audit-and-outbox.md` refuerza que audit trails son una preocupacion de persistencia de primera clase.
- No se requiere un router nuevo ni una superficie frontend dedicada para esta historia; el trabajo es principalmente de backend y regresion.

### Critical Guardrails

- No debilitar la regla vigente: `404` para recursos de otro tenant y `403` para permisos de modulo faltantes en el mismo tenant.
- No crear un segundo sistema de identidad o permisos para superadmin; se reutiliza el contrato actual.
- No exponer secretos, tokens, firmas o credenciales en auditoria, logs, UI o respuestas API.
- No permitir que una falla auxiliar de auditoria rompa una operacion ya confirmada por el backend.
- No introducir datos falsos ni contadores inventados para soporte interno.

### Implementation Guidance

- Reusar `record_superadmin_access` o `record_audit_best_effort` antes de crear cualquier logger paralelo.
- Mantener la excepcion superadmin pequeña y explicita; no generalizar el acceso cross-tenant.
- Usar queries tenant-scoped y el patron de servicios actual, no accesos globales ad hoc.
- Si hace falta tocar frontend, limitarlo a labels honestos dentro del shell existente. No abrir rutas nuevas.

### Suggested File Targets

- Backend likely to change:
  - `backend/app/auth/service.py`
  - `backend/app/users/routes.py`
  - `backend/app/users/service.py`
  - `backend/app/companies/routes.py`
  - `backend/app/audit/service.py`
  - `backend/app/main.py`
  - `backend/tests/test_superadmin_access.py`
- Frontend likely to change only if there is an existing support surface:
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
- Reusar los dominios existentes de `users`, `auth` y `audit`; no agregar un subsistema nuevo.
- Si se crea una bateria de regresion, ubicarla en `backend/tests/` con un nombre focalizado en superadmin.
- Cualquier salida visual debe seguir la superficie unica ya existente; no crear un router nuevo.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 7, Historia 7.1, criterios de aceptacion]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - superadmin y soporte interno]
- [Source: `docs/adr/0001-security-and-multi-tenant-enforcement.md` - contrato `404` cross-tenant y `403` permisos]
- [Source: `docs/adr/0004-integrations-events-audit-and-outbox.md` - audit trails y persistencia de eventos]
- [Source: `backend/app/auth/service.py` - `is_superadmin`, `require_roles`, `require_module_access`]
- [Source: `backend/app/users/routes.py` - acceso cross-tenant para superadmin en usuarios]
- [Source: `backend/app/audit/service.py` - redaccion, `record_audit_best_effort`, `record_superadmin_access`]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - no introducir router nuevo para soporte]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Se resolvio el siguiente backlog desde `sprint-status.yaml`: `7-1-operar-como-superadmin-con-acceso-auditado`.
- Se cargo el contexto persistente de `project-context.md`, el epic 7 completo, el PRD, las ADRs de seguridad y auditoria, la arquitectura frontend y el brief de UX.
- Se confirmo que la base tecnica ya tiene excepcion superadmin, redaccion de metadata y helpers de auditoria; esta historia documenta y blinda ese contrato para implementacion/regresion.
- La historia quedo archivada fuera del flujo activo para respetar el orden actual de trabajo del epic 1.

### Completion Notes List

- Historia creada para epic 7 con foco en acceso cross-tenant auditable.
- Se definieron criterios de aceptacion, tareas, guardrails, pruebas y file targets sin introducir una superficie paralela innecesaria.
- Se dejo el alcance separado de la historia 7.2 para que la auditoria transversal de eventos sensibles se desarrolle como trabajo posterior.

### File List

- `_bmad-output/implementation-artifacts/7-1-operar-como-superadmin-con-acceso-auditado.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
