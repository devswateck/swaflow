---
baseline_commit: 34029c557dd621508aec915ae1b0fea012ce5436
---

# Story 1.10: Configurar notificaciones por correo y webhooks salientes

Status: done

## Story

Como admin principal del tenant,
Quiero habilitar notificaciones por correo y webhooks salientes como integraciones auxiliares,
Para que el negocio reciba soporte operativo sin convertir estas integraciones en fuente de verdad.

## Acceptance Criteria

1. Dado que el tenant quiere avisos operativos, cuando el admin configura correo, entonces el sistema guarda la configuracion asociada al `company_id`, cifra las credenciales, conserva la marca o nombre del tenant en los correos generados y no expone secretos en UI, logs, auditoria ni respuestas API.
2. Dado que el tenant quiere automatizaciones externas, cuando el admin configura webhooks salientes, entonces el sistema permite filtrar por tipo de evento, activar o desactivar cada webhook y usar firma o secreto cuando se configure.
3. Dado que una integracion auxiliar falla, cuando el backend procesa un correo o webhook saliente, entonces el sistema registra el incidente para soporte o administracion, marca el estado operativo correspondiente y no revierte transacciones ya confirmadas en backend.
4. Dado que una integracion auxiliar esta inactiva o no existe, cuando se ejecuta una notificacion o despacho, entonces el flujo principal del negocio sigue disponible y no se bloquean ordenes, pagos, inventario, citas ni conversaciones.
5. Dado que el usuario no tiene permisos del modulo o pertenece a otro tenant, cuando intenta leer o modificar estas integraciones, entonces el backend responde `403` para falta de permiso y `404` para aislamiento cross-tenant.
6. Dado que el frontend muestra la superficie de Integraciones, cuando el usuario revisa correo y webhooks salientes, entonces ve configuracion honesta, labels claros de V1 y estados que reflejan el backend real sin datos falsos.

**FR cubiertos:** FR114, FR115, FR116, FR117, FR118, FR119

## Tasks / Subtasks

- [x] Auditar el contrato actual de correo y webhooks salientes para dejar solo una fuente de verdad por tenant.
  - [x] Confirmar que `CompanyIntegration` sigue siendo el contenedor canonico para correo.
  - [x] Confirmar que `OutboundWebhook` sigue siendo el contenedor canonico para webhooks salientes.
  - [x] Mantener el comportamiento `404` cross-tenant y `403` por permisos de modulo.
- [x] Ajustar el envio de correos operativos para que use la marca del tenant.
  - [x] Reusar la integracion de correo activa del tenant y sus credenciales cifradas.
  - [x] Construir subject/body con branding del tenant o defaults seguros cuando falte configuracion.
  - [x] Evitar que el correo operativo dependa de n8n o de confirmaciones externas.
- [x] Endurecer el despacho de webhooks salientes como mecanismo auxiliar.
  - [x] Mantener filtro por `event_type`, `active` y secreto/firma.
  - [x] Preservar soporte para evento comodin `*` si el contrato actual lo requiere.
  - [x] Registrar estados de entrega fallida sin romper el flujo que genero el evento.
- [x] Exponer trazabilidad util para soporte.
  - [x] Asegurar que eventos e incidencias queden visibles en el modelo de `Event` y/o `AuditLog` con metadata redacted.
  - [x] No persistir secretos completos en metadata, logs ni payloads de auditoria.
  - [x] Mantener la aplicacion de webhooks como una extension posterior al commit de negocio, nunca como precondicion.
- [x] Alinear la superficie de frontend de Integraciones.
  - [x] Reusar la pagina existente en `frontend/src/App.tsx`.
  - [x] Mantener las tarjetas de correo, automatizacion y webhooks salientes dentro del shell actual.
  - [x] Ajustar copy y estados para que quede claro que estas integraciones son auxiliares y tolerantes a fallos.
- [x] Agregar cobertura de regresion.
  - [x] Probar CRUD tenant-scoped de correo y webhooks con bloqueo cross-tenant.
  - [x] Probar cifrado/redaccion de secretos en integraciones y auditoria.
  - [x] Probar que un fallo de despacho marca evidencia operativa sin abortar la transaccion fuente.
  - [x] Probar que el frontend sigue compilando y muestra el copy actualizado.

## Dev Notes

### Business Context

- Esta story cubre integraciones auxiliares de salida: correo transaccional y webhooks salientes para n8n u otros servicios perifericos.
- La fuente de verdad sigue siendo el backend de Swaflow. Correo y webhooks solo acompañan eventos ya confirmados.
- El producto V1 ya considera que n8n, email o webhooks no deben confirmar ordenes, pagos, inventario ni citas.
- El valor funcional principal es soporte operativo, automatizacion periférica y notificacion comercial sin romper el flujo core.

### Current Code State

- `backend/app/integrations/models.py` ya define `CompanyIntegration` y `OutboundWebhook` como tablas tenant-scoped.
- `backend/app/integrations/service.py` ya centraliza CRUD de integraciones y webhooks, cifra credenciales y registra auditoria.
- `backend/app/integrations/routes.py` ya protege la superficie con `require_module_access("integrations")` y expone `/integrations` y `/outbound-webhooks`.
- `backend/app/events/dispatcher.py` ya firma webhooks salientes con HMAC SHA-256 cuando existe `secret_token`, y marca el `Event` como `processed` o `delivery_failed`.
- `backend/app/events/service.py` ya crea eventos de negocio y delega el despacho saliente despues del flush.
- `backend/app/payments/notifications.py` ya envia correos de pago confirmado usando una integracion de tipo `email`, aunque el branding de tenant puede seguir siendo demasiado generico.
- `frontend/src/App.tsx` ya incluye tarjetas de `Correo`, `Automatizaciones`, `Pasarela de pago` y la UI de `Webhooks salientes`.
- `frontend/src/App.tsx` ya define opciones de eventos salientes como `message.received`, `order.paid` y `appointment.created`.
- `backend/tests/test_tenant_and_orders.py` ya tiene cobertura de redaccion de secretos para integraciones y webhooks, pero la historia necesita ampliar cobertura sobre branding, entrega fallida y reglas de salida.
- Implementacion completada: el correo operativo ahora usa la marca del tenant en subject/body y registra incidentes de entrega fallida; el dispatcher de webhooks registra auditoria cuando una entrega falla; la UI de Integraciones quedo alineada con copy auxiliar; y se agregaron pruebas para branding, auditoria y firma HMAC.

### Critical Guardrails

- No crear un segundo subsistema de notificaciones que compita con `CompanyIntegration` y `OutboundWebhook`.
- No usar correo o webhooks como fuente de verdad para ningun estado critico.
- No permitir que un fallo auxiliar revierta una orden, pago, reserva, cita o mensaje ya confirmado por backend.
- No exponer secretos, tokens o firmas completas en respuestas, logs, auditoria o UI.
- No romper la separacion de permisos: `403` para falta de modulo, `404` para cross-tenant.
- No convertir n8n en propietario de transacciones; n8n sigue siendo periferico.

### Implementation Guidance

- Reusar el patron que ya existe en integraciones: validacion centralizada, cifrado de credenciales y auditoria segura.
- Si hace falta enriquecer metadata de eventos fallidos, preferir el `Event` ya existente o `AuditLog` antes que crear tablas nuevas.
- Mantener el despacho de webhooks tolerante a fallos. Un destino caido o un 5xx remoto no debe romper el commit de negocio.
- Mantener el branding de correo sencillo y honesto. Si falta configuracion de marca, usar un fallback claro y no inventar activos.
- Mantener el UI de Integraciones en la pagina existente; no abrir un flujo nuevo ni un router nuevo.
- Si se agregan campos de configuracion nuevos, deben seguir el patron `config` JSON existente y no introducir una segunda estructura paralela.

### Suggested File Targets

- Backend likely to change:
  - `backend/app/payments/notifications.py`
  - `backend/app/events/dispatcher.py`
  - `backend/app/events/service.py`
  - `backend/app/integrations/service.py`
  - `backend/app/integrations/schemas.py` only if the payload contract needs stronger validation
  - `backend/app/integrations/routes.py` only if endpoint behavior or copy needs a small adjustment
- Frontend likely to change:
  - `frontend/src/App.tsx`
- Tests likely to change:
  - `backend/tests/test_tenant_and_orders.py`
  - `backend/tests/test_whatsapp_setup.py` only if a shared integration fixture is truly reused there
  - A focused new file such as `backend/tests/test_integrations_notifications.py` if the coverage grows too large for the monolith test file
  - `_bmad-output/implementation-artifacts/1-10-configurar-notificaciones-por-correo-y-webhooks-salientes.md`

### Testing Requirements

- Cover tenant-scoped CRUD for email and outbound webhooks.
- Cover `404` for another tenant and `403` for users without `integrations` access.
- Cover secret encryption/redaction for email credentials and webhook secrets.
- Cover event filtering and active/inactive toggles for outbound webhooks.
- Cover HMAC signing behavior when a webhook has a secret configured.
- Cover delivery-failure handling so the event is marked with a non-success status and the source transaction remains committed.
- Cover email notification generation using tenant branding or a deterministic fallback when brand data is incomplete.
- Cover frontend compile/lint after any copy or field changes.
- Keep the tests compatible with the current SQLite-backed suite and MySQL-safe schema assumptions.

### Project Structure Notes

- Preserve the existing domain boundaries: `integrations` owns tenant connection metadata and `events` owns dispatch and incident state.
- Keep business writes inside services, not in routes.
- Preserve the current shell-centered frontend model. This story should not introduce a new route or rewrite the app shell.
- Use the existing `api<T>()` helper and the current auth store if the frontend needs to read or refresh integration state.
- Prefer additive changes to JSON config contracts over broad structural refactors.

### References

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Story 1.10, FR114-FR119]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - Integrations V1, external notifications, n8n boundary]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/addendum.md` - outbound webhook and integration contract expectations]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - integrations auxiliary, backend source of truth, outbox/event rules]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - Integrations grouped under Automation, desktop-only shell]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/frontend-implementation-brief.md` - Integrations page remains inside the existing shell]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/integrations/models.py` - tenant-scoped integration/webhook models]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/integrations/service.py` - encrypted integration CRUD and audit]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/integrations/routes.py` - module access gate and REST surface]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/events/dispatcher.py` - outbound webhook dispatch, HMAC signing, failure tolerance]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/payments/notifications.py` - email notification flow]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx` - Integrations page, email card, automation card, outbound webhooks UI]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py` - redaction and integration regression patterns]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/1-9-configurar-calendario-del-tenant.md` - previous integration-story implementation pattern]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Story selected automatically as the first backlog item in `sprint-status.yaml`: `1-10-configurar-notificaciones-por-correo-y-webhooks-salientes`.
- Reviewed epic, PRD, addendum, architecture, UX brief, existing integration models/service/routes, event dispatcher, payment notification path, frontend Integrations page, and the prior calendar story before writing this story.
- Confirmed the repo already has the canonical integration and event boundaries, so this story should extend them instead of inventing a new notification subsystem.
- Confirmed the current frontend already exposes email, automation, payment, and outbound webhook controls inside the existing shell.
- Confirmed the current backend already signs outbound webhooks and records `processed` versus `delivery_failed`, but the story still needs stronger incident visibility and brand-aware email output.
- Implemented tenant-branded email rendering, delivery-failure auditing, outbound webhook failure auditing, and small Integrations page copy updates.
- Validation executed: `python3 -m py_compile backend/app/payments/notifications.py backend/app/events/dispatcher.py backend/tests/test_tenant_and_orders.py`, `./backend/.venv/bin/pytest backend/tests/test_tenant_and_orders.py -q` (`79 passed`), `npm run lint`, `npm run build`.

### Completion Notes List

- Built the story around the existing `integrations`, `events`, and `payments` boundaries instead of introducing a parallel notifications stack.
- Anchored the acceptance criteria on tenant-scoped CRUD, encrypted secrets, failure isolation, and source-of-truth protection.
- Captured the current implementation state so the dev agent can reuse the existing email and webhook surfaces with minimal churn.
- Added explicit guardrails for cross-tenant access, secret redaction, and non-blocking auxiliary delivery failures.
- Implemented the requested backend and frontend changes and validated them with backend regression tests plus frontend lint/build.
- Resolved review findings by turning missing SMTP configuration into an audited delivery failure and isolating outbound webhook audit persistence so it cannot break the dispatch path.

### File List

- `_bmad-output/implementation-artifacts/1-10-configurar-notificaciones-por-correo-y-webhooks-salientes.md`
- `backend/app/payments/notifications.py`
- `backend/app/events/dispatcher.py`
- `backend/tests/test_tenant_and_orders.py`
- `frontend/src/App.tsx`

## Change Log

- 2026-06-29: Created the V1 story context for email notifications and outbound webhooks, aligned to the current backend and frontend contracts, and marked it ready for dev.
- 2026-06-29: Implemented tenant-branded email notifications, delivery-failure auditing for email and outbound webhooks, and updated frontend copy; validated with backend regression tests and frontend lint/build.
- 2026-06-29: Addressed code review findings by failing and auditing incomplete email configuration and hardening outbound webhook incident logging so auxiliary failures stay non-blocking.
