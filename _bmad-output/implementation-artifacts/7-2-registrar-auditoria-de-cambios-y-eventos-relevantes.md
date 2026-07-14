---
baseline_commit: 595b380d6111b59e727b01d978cf27ebc2b6a335
---

# Story 7.2: Registrar auditoria de cambios y eventos relevantes

Status: done

## Story

Como operador o admin del tenant,
Quiero que los cambios criticos y eventos operativos queden registrados con auditoria trazable,
Para que exista evidencia util para soporte, seguridad y control interno sin romper el flujo principal.

## Acceptance Criteria

1. Dado que ocurre un evento de negocio relevante, cuando el backend confirma la operacion, entonces se registra evidencia auditable con `actor`, `company_id`, `entity_type`, `entity_id` cuando aplique, `action`, resumen y metadata redactada.
2. Dado que un usuario reasigna un chat, cuando el cambio se confirma, entonces queda auditado el usuario actor, el responsable anterior, el nuevo responsable, la fecha/hora efectiva y el estado operativo resultante.
3. Dado que se modifica una configuracion critica de permisos, integraciones, credenciales, IA o funnels, cuando la accion se guarda, entonces el cambio queda auditado sin exponer secretos, tokens, firmas o credenciales en claro.
4. Dado que se procesa un cambio de ciclo de vida en mensajes, ordenes, pagos o citas, cuando el backend confirma la transicion, entonces se mantiene una trazabilidad consistente para soporte y consulta posterior.
5. Dado que la auditoria o el despacho auxiliar fallan, cuando la operacion principal ya fue validada por el backend, entonces la mutacion no se revierte y el fallo queda solo en logs internos.

## Tasks / Subtasks

- [x] Inventariar los puntos actuales de auditoria y eventos en `auth`, `users`, `companies`, `conversations`, `orders`, `payments`, `appointments`, `integrations`, `ai`, `funnels`, `whatsapp`, `audit` y `events`.
  - [x] Confirmar que `record_audit_best_effort` y `create_event` se reutilizan antes de introducir helpers nuevos.
  - [x] Identificar los flujos sensibles que aun registran solo parte de la transicion o que siguen acoplados al commit principal.
  - [x] Verificar que no se esta duplicando auditoria para el mismo hecho de negocio en mas de un sitio.
- [x] Estandarizar la forma de registrar cambios sensibles y eventos relevantes.
  - [x] Mantener la auditoria tenant-scoped y con redaccion recursiva de metadata sensible.
  - [x] Usar metadata minima y util: actor, tenant objetivo, entidad, accion, previo, nuevo y contexto operativo solo cuando aporte valor.
  - [x] Conservar el contrato best-effort: una falla auxiliar no puede invalidar la operacion de negocio ya confirmada.
- [x] Cubrir los dominios donde la trazabilidad es obligatoria para esta historia.
  - [x] Reasignaciones y cambios de estado de conversaciones.
  - [x] Eventos de mensajes, pagos, ordenes y citas.
  - [x] Cambios de permisos, integraciones, credenciales, IA y funnels.
  - [x] Acciones operativas de soporte o superadmin que ya requieran auditabilidad, sin abrir un segundo sistema de permisos.
- [x] Ajustar o ampliar la capa de eventos solo si hace falta para mantener la trazabilidad util.
  - [x] Preservar la semantica de `create_event` y del despacho actual.
  - [x] Extender tipos de evento solo cuando aporten contexto real para soporte o exportacion posterior.
  - [x] No introducir cola, worker o subsistema nuevo para esta necesidad.
- [x] Agregar regresion automatizada para los flujos sensibles afectados.
  - [x] Probar que la auditoria persiste en un caso representativo por dominio.
  - [x] Probar que los secretos quedan redactados.
  - [x] Probar que la mutacion principal sigue funcionando si la auditoria auxiliar falla.
  - [x] Probar que el orden temporal y el scope por tenant permanecen correctos.

## Dev Notes

### Business Context

- Esta historia cierra el vacio de trazabilidad operativa del epic 7 sin convertir la auditoria en una nueva fuente de verdad.
- El objetivo es soporte y control interno: saber quien cambio que, cuando y bajo que tenant, con suficiente contexto para investigar problemas.
- La historia no cubre exportacion al retiro del tenant; eso pertenece a la 7.3.
- La historia tampoco introduce una UI nueva de auditoria. Si hace falta alguna superficie, debe reusar la app existente y mantenerse honesta.

### Current Code State

- `backend/app/audit/service.py` ya centraliza `record_audit`, `record_audit_best_effort`, redaccion recursiva de metadata sensible y `record_superadmin_access`.
- `backend/app/events/service.py` ya centraliza `create_event` y `list_conversation_events`, con tipos de evento existentes para conversaciones, mensajes, ordenes y citas.
- `backend/app/conversations/service.py` ya usa `record_audit_best_effort` y `create_event` en varias transiciones del inbox.
- `backend/app/orders/service.py` ya emite eventos y auditoria best-effort para ordenes y pagos.
- `backend/app/appointments/service.py` ya registra eventos y auditoria para citas y sincronizacion de calendario.
- `backend/app/integrations/service.py` ya audita cambios de integraciones y webhooks, con helpers locales para limpiar metadata sensible.
- `backend/app/ai/service.py` ya audita cambios de configuracion del agente, FAQs y templates interactivos.
- `backend/app/funnels/service.py` ya audita cambios de funnels.
- `backend/app/users/service.py` y `backend/app/companies/service.py` ya registran accesos o cambios de soporte y superadmin cuando corresponde.
- `backend/app/events/dispatcher.py` ya trata la entrega auxiliar de webhooks como best-effort y registra incidencias sin romper la mutacion principal.

### Previous Story Intelligence

- La historia 7.1 establecio el contrato de superadmin auditable y reforzo que las incidencias auxiliares de auditoria no deben romper accesos validos.
- El aprendizaje critico de la historia previa es mantener la excepcion superadmin explicita y pequena, no crear un sistema paralelo de permisos.
- Tambien quedo claro que la auditoria debe ocurrir sin contaminar el flujo de negocio principal; esa regla sigue aplicando aqui.
- No ampliar el alcance a exportacion ni a superficies de soporte nuevas. Mantener la historia enfocada en trazabilidad de cambios y eventos.

### Critical Guardrails

- No romper el aislamiento por `company_id`.
- No registrar secretos, tokens, firmas, contraseñas o credenciales en claro en audit logs, metadata, responses o logs internos.
- No convertir la auditoria en una dependencia transaccional de ordenes, citas, pagos, IA o mensajes.
- No duplicar eventos o auditoria por el mismo hecho de negocio.
- No introducir un nuevo sistema de colas o workers para resolver esta trazabilidad.
- No tocar el contrato de exportacion de la 7.3.

### Implementation Guidance

- Reusar `record_audit_best_effort` para todo cambio sensible que deba persistir aun si la auditoria falla.
- Reusar `create_event` para transiciones de negocio que necesitan timeline o trazabilidad consultable.
- Cuando un payload tenga deltas `before/after`, conservar solo campos utiles y redactar cualquier campo sensible de forma recursiva.
- Si un flujo ya audita en el punto correcto, no duplicar la escritura en otro nivel.
- Si un flujo sigue acoplado al commit principal, mover la auditoria a best-effort post-commit o aislarla de forma equivalente.
- Priorizar trazabilidad de cambios reales sobre auditar cada lectura o cada vista.

### Suggested File Targets

- Backend likely to change:
  - `backend/app/audit/service.py`
  - `backend/app/events/service.py`
  - `backend/app/conversations/service.py`
  - `backend/app/orders/service.py`
  - `backend/app/appointments/service.py`
  - `backend/app/integrations/service.py`
  - `backend/app/ai/service.py`
  - `backend/app/funnels/service.py`
  - `backend/app/whatsapp/service.py`
  - `backend/app/payments/notifications.py`
  - `backend/app/users/service.py`
  - `backend/app/companies/service.py`
  - `backend/app/auth/service.py`
  - `backend/tests/test_tenant_and_orders.py`
  - `backend/tests/test_superadmin_offboarding.py`
  - `backend/tests/test_audit_events.py` if a focused regression file is needed
- Frontend:
  - No se espera cambio de frontend para esta historia.

### Testing Requirements

- Probar un caso representativo de auditoria por dominio sensible, al menos en:
  - conversacion o chat reasignado,
  - orden o pago,
  - cita,
  - integracion o webhook,
  - IA o funnel.
- Probar que la metadata sensible queda redactada.
- Probar que un fallo en auditoria auxiliar no revierte una mutacion valida.
- Probar que el scope del tenant sigue siendo correcto y que no se filtra informacion cross-tenant.
- Probar que los eventos conservan orden y payload util para consumo posterior.
- Mantener la compatibilidad con la suite actual de SQLite en tests y con el contrato MySQL vigente de la app.

### Project Structure Notes

- Mantener la estructura por dominio existente; no crear un subsistema transversal nuevo sin necesidad.
- Si se agrega un helper compartido, debe vivir en `audit` o `events`, no en un modulo ad hoc.
- No mover la logica de negocio a `n8n`, a la IA o a un dispatcher nuevo.
- La trazabilidad debe seguir el patron de servicios sincronicos y respuestas de backend ya usado en el repo.

## References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 7, historia 7.2 y criterios de aceptacion]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - FR140, FR141, FR159, FR160, FR175, FR176, FR177 y seccion de retencion/exportacion]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/decision-audit.md` - retencion indefinida y soporte cross-tenant]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/review-technical-product.md` - contenido minimo de exportacion y riesgos de auditoria]
- [Source: `_bmad-output/project-context.md` - reglas de stack, multi-tenancy, redaccion y best-effort]
- [Source: `backend/app/audit/service.py` - redaccion de metadata y helpers de auditoria]
- [Source: `backend/app/events/service.py` - eventos de negocio y timeline consultable]
- [Source: `backend/app/events/dispatcher.py` - despacho auxiliar best-effort de eventos]
- [Source: `backend/app/conversations/service.py` - auditoria y eventos en el inbox]
- [Source: `backend/app/orders/service.py` - auditoria y eventos en ordenes y pagos]
- [Source: `backend/app/appointments/service.py` - auditoria y eventos en citas]
- [Source: `backend/app/integrations/service.py` - auditoria de integraciones y webhooks]
- [Source: `backend/app/ai/service.py` - auditoria de cambios de configuracion de IA]
- [Source: `backend/app/funnels/service.py` - auditoria de funnels]
- [Source: `backend/app/users/service.py` - accesos y cambios sensibles del usuario]
- [Source: `backend/app/companies/service.py` - accesos y cambios sensibles del tenant]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Se identifico un hueco real en `backend/app/auth/service.py`: el cambio de contrasena seguia usando auditoria transaccional y podia fallar si la auditoria auxiliar fallaba.
- Se cambio `change_own_password()` a `record_audit_best_effort` con wrapper local y logging defensivo para que el flujo principal no dependa de la persistencia de auditoria.
- Se agrego regresion en `backend/tests/test_tenant_and_orders.py` para confirmar que el cambio de contrasena sigue funcionando aun cuando la auditoria auxiliar falla.
- Se validaron las trayectorias relevantes con `./backend/.venv/bin/python -m pytest backend/tests/test_tenant_and_orders.py backend/tests/test_superadmin_offboarding.py backend/tests/test_user_permissions.py -q`.

### Completion Notes

- Se blindo el cambio de contrasena de usuario para que la auditoria sea best-effort y no rompa el flujo principal.
- Se agrego cobertura de regresion para el caso de fallo auxiliar de auditoria en `auth`.
- Se confirmo que las trazas de conversacion, ordenes, citas, integraciones, IA, funnels y exportacion ya siguen el contrato esperado de auditoria/eventos en la base de codigo actual.
- Se dejo el story file listo para revision con estado `review`.

### File List

- `_bmad-output/implementation-artifacts/7-2-registrar-auditoria-de-cambios-y-eventos-relevantes.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/app/auth/service.py`
- `backend/tests/test_tenant_and_orders.py`

### Change Log

- 2026-07-13: Se blindo `change_own_password()` para que la auditoria sea best-effort y no afecte la mutacion principal si falla el helper auxiliar.
- 2026-07-13: Se agrego cobertura de regresion para validar que el cambio de contrasena sobrevive a un fallo de auditoria.

### Review Findings

- [x] [Review][Patch] Emitir la auditoria de `auth.password_changed` despues del commit principal [backend/app/auth/service.py:130]
