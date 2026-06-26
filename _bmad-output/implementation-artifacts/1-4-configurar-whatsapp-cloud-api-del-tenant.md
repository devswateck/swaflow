---
title: "Historia 1.4: Configurar WhatsApp Cloud API del tenant"
status: done
baseline_commit: 533ce87609109706230237ebe5629fd34c324fa9
---

# Historia 1.4: Configurar WhatsApp Cloud API del tenant

Status: done

## Historia

Como admin principal del tenant,
Quiero configurar y probar la cuenta de WhatsApp Cloud API de mi empresa,
para que Swaflow pueda conectar, verificar y operar el canal oficial del tenant sin exponer secretos ni mezclar cuentas entre empresas.

## Criterios de aceptación

1. Dado que el admin principal abre la superficie de WhatsApp, when registra o actualiza `phone_number_id`, `business_account_id`, `access_token` y `verify_token`, then el sistema persiste una cuenta tenant-scoped, cifra el access token y nunca expone el secreto en texto plano despues de guardarlo.
2. Dado que el admin abre la pantalla de setup, when el backend responde, then la UI muestra la `callback_url`, el `verify_token`, la `graph_api_version` y el estado de firma de webhook de forma honesta, usando `public_base_url` y la configuracion vigente.
3. Dado que Meta verifica la suscripcion del webhook, when llega `GET /webhooks/whatsapp` con `hub.mode=subscribe` y un verify token valido, then el sistema devuelve el challenge; when el token es invalido, then responde `403`.
4. Dado que el tenant tiene `whatsapp_app_secret` configurado, when llega `POST /webhooks/whatsapp` con una firma `x-hub-signature-256` invalida o ausente, then el sistema rechaza la peticion; when la firma es valida, then procesa el payload.
5. Dado que existe una cuenta activa configurada, when el admin ejecuta la prueba de cuenta, then el sistema consulta Meta, devuelve `display_phone_number`, `verified_name` y `quality_rating` cuando existan, y mantiene la cuenta dentro del mismo tenant.
6. Dado que otro tenant intenta leer o modificar la configuracion de WhatsApp, when la peticion llega al backend, then el sistema no expone datos ajenos y responde `404` para recursos de otro tenant.
7. Dado que un usuario del mismo tenant sin permiso del modulo de WhatsApp intenta leer o modificar la configuracion, when la peticion llega al backend, then el sistema deniega el acceso con `403` por el control de permisos existente.
8. Dado que llegan mensajes entrantes o respuestas interactivas de WhatsApp, when el webhook valida la firma y enruta el payload, then el sistema los asocia al tenant, contacto y conversacion correspondientes y preserva el flujo operativo del inbox.
9. Dado que el equipo evalua Embedded Signup o popup de Meta, when revisa esta story, then queda claro que ese flujo es V2 y no forma parte del alcance de V1.

**FR cubiertos:** FR027, FR028, FR029, FR030, FR031, FR033, FR034

## Tareas / Subtareas

- [x] Auditar y endurecer `backend/app/whatsapp/routes.py`, `backend/app/whatsapp/service.py` y `backend/app/whatsapp/schemas.py` para que el contrato de setup, webhook y prueba de cuenta quede consistente con V1.
  - [x] Mantener el verify token global o por cuenta segun la configuracion vigente.
  - [x] Preservar la validacion de firma cuando exista `whatsapp_app_secret`.
  - [x] No tocar el flujo de envio de mensajes salvo que sea necesario para la prueba de cuenta.
- [x] Confirmar que `backend/app/whatsapp/models.py` sigue cifrando credenciales y que la persistencia de `WhatsAppAccount` permanece tenant-scoped.
  - [x] No introducir almacenamiento en texto plano para access tokens.
  - [x] Mantener el estado `active` como flujo por defecto de V1.
- [x] Revisar `backend/app/core/config.py` y el uso de `public_base_url`, `whatsapp_verify_token`, `whatsapp_app_secret` y `whatsapp_graph_api_version`.
  - [x] No inventar valores ni hardcodear URLs que deban venir de configuracion.
- [x] Actualizar `frontend/src/App.tsx` en `WhatsAppPage` para que la configuracion muestre setup, alta/edicion de cuenta, prueba y listado con copy claro.
  - [x] Mantener la pantalla como superficie propia de WhatsApp, no moverla a `SettingsPage`.
  - [x] Mostrar estados de carga, error y exito sin ocultar fallos de Meta.
- [x] Agregar o ampliar pruebas de backend para setup, verificacion de webhook, firma de webhook, alta/listado/prueba de cuenta y aislamiento cross-tenant.
  - [x] Cubrir el caso valido y el caso invalido de `hub.verify_token`.
  - [x] Cubrir firma valida e invalida cuando haya `whatsapp_app_secret`.
  - [x] Cubrir `404` cuando se intenta leer una cuenta de otro tenant.
  - [x] Cubrir `403` cuando un usuario del mismo tenant intenta operar sin permiso del modulo de WhatsApp.
  - [x] Cubrir procesamiento inbound de mensajes entrantes y respuestas interactivas con asociacion a tenant, contacto y conversacion.
- [x] Verificar la implementacion con `pytest`, `npm run build` y `npm run lint`.

## Notas de desarrollo

### Contexto de negocio

- WhatsApp Cloud API es el canal principal del MVP.
- V1 usa configuracion tecnica actual; el popup/Embedded Signup de Meta queda como mejora V2.
- Esta story no trata de construir una nueva superficie de administracion, sino de cerrar y endurecer la configuracion operativa del canal.

### Reglas criticas a preservar

- Mantener aislamiento multi-tenant por `company_id` en lectura y escritura.
- No exponer secretos, tokens ni credenciales en UI, logs, respuestas o documentos generados.
- No convertir esta story en un redisenio del shell ni en un modulo generico nuevo.
- No mover la configuracion de WhatsApp a `SettingsPage`; ya existe `WhatsAppPage` para este dominio.
- Mantener mensajes visibles en espanol y copy operativo, no marketing.

### Estado actual del codigo

- `backend/app/whatsapp/routes.py` ya expone `GET /webhooks/whatsapp`, `POST /webhooks/whatsapp`, `GET /whatsapp/setup`, `POST /whatsapp/accounts`, `GET /whatsapp/accounts`, `POST /whatsapp/accounts/{id}/test`, envio de mensajes y sync de catalogo.
- `backend/app/whatsapp/service.py` ya crea cuentas, cifra access tokens, resuelve cuentas activas por tenant, valida tokens de webhook y publica eventos de mensajes.
- `backend/app/whatsapp/schemas.py` ya modela el payload de cuenta, setup, prueba y respuestas de envio.
- `backend/app/whatsapp/models.py` ya guarda `phone_number_id`, `business_account_id`, `access_token_encrypted`, `verify_token` y `status`.
- `backend/app/core/config.py` ya contiene `whatsapp_verify_token`, `whatsapp_app_secret`, `whatsapp_graph_api_version` y `public_base_url`.
- `frontend/src/App.tsx` ya tiene `WhatsAppPage` con formulario de cuenta, prueba de envio y panel de webhook; esta story debe completar/hardener ese flujo, no reemplazarlo.

### Que debe cambiar

- La configuracion debe quedar cerrada para V1: guardar cuenta, mostrar setup, probar cuenta y validar webhook sin ambiguedad.
- La UI debe mostrar el estado real de la configuracion, incluyendo firma de webhook y datos de Meta, sin inventar valores.
- Las pruebas deben cubrir el contrato publico del modulo y el aislamiento entre tenants.

### Que debe preservarse

- El flujo de login y autorizacion existente.
- El helper de permisos por modulo para `whatsapp`.
- La convencion de backend por dominio (`whatsapp`, `auth`, `companies`, etc.).
- El comportamiento actual de enviar mensajes, sincronizar catalogo y procesar webhooks salvo que la story necesite ajustes de contrato.

### Inference explicita para la solucion

- El flujo actual ya cubre buena parte de la integracion; el foco de esta story es asegurar que la experiencia de configuracion y verificacion quede lista para desarrollo y no genere falsos positivos.
- Si falta una mejora para el test de cuenta o la exposicion del setup, debe vivir dentro del dominio `whatsapp`, no en un modulo nuevo.
- La firma de webhook debe seguir siendo un no-op cuando no exista `whatsapp_app_secret`; eso es parte del comportamiento esperado de V1.
- Embedded Signup y cualquier flujo tipo popup deben tratarse como decision separada de V2.

### Arquitectura y salvaguardas

- Seguir el patron de backend por dominio: `backend/app/whatsapp/`, `backend/app/core/`, `backend/tests/`.
- No introducir un router nuevo ni un modulo generic de integraciones solo para esta story.
- La UI de WhatsApp debe seguir consumiendo `api<T>()` y el estado de auth existente.
- Mantener la regla de `404` para recursos de otro tenant y no ocultar fallos reales de Meta.

### File Structure Notes

- Backend candidato a tocar:
  - `backend/app/whatsapp/routes.py`
  - `backend/app/whatsapp/service.py`
  - `backend/app/whatsapp/schemas.py`
  - `backend/app/whatsapp/models.py`
  - `backend/app/core/config.py`
  - `backend/tests/test_tenant_and_orders.py` o un test dedicado para WhatsApp
- Frontend candidato a tocar:
  - `frontend/src/App.tsx`
- No tocar dominios ajenos si el cambio cabe en los archivos anteriores.

### Testing requirements

- Cubrir creacion, listado y prueba de cuenta WhatsApp.
- Cubrir el endpoint de verificacion del webhook con token valido e invalido.
- Cubrir el rechazo por firma invalida cuando exista `whatsapp_app_secret`.
- Cubrir aislamiento cross-tenant para lectura y prueba de cuenta.
- Mantener compatibilidad con la suite actual y con SQLite en memoria.

### Previous story intelligence

- La story 1.3 dejo establecido el patron de permisos por modulo; esta story debe respetar ese helper y no abrir accesos nuevos por error.
- La configuracion de cuenta no debe depender de `SettingsPage`; el modulo WhatsApp ya tiene su propia pagina y debe seguir ahi.
- El proyecto ya usa `api<T>()`, mensajes en espanol y un shell operacional estable; esta story debe extender ese patron, no improvisar otro.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 1, Historia 1.4, cobertura FR FR027-FR035]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - WhatsApp V1 scope y setup requirements]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - WhatsApp as primary MVP channel y shell structure]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - WhatsApp placement in the sidebar y setup/salud guidance]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/DESIGN.md` - Swa Tech tokens, dark mode default, y operational UI rules]
- [Source: `backend/app/whatsapp/routes.py`]
- [Source: `backend/app/whatsapp/service.py`]
- [Source: `backend/app/whatsapp/schemas.py`]
- [Source: `backend/app/whatsapp/models.py`]
- [Source: `backend/app/core/config.py`]
- [Source: `frontend/src/App.tsx` - `WhatsAppPage`]
- [Source: `_bmad-output/implementation-artifacts/1-3-administrar-usuarios-roles-y-permisos-del-tenant.md` - module access patterns y SettingsPage boundaries]

## Dev Agent Record

### Agent Model Used

GPT-5

### Referencias de depuración

- 2026-06-12: Se analizo el sprint-status, PRD, epics, arquitectura, UX, estado del dominio WhatsApp y las historias 1.1-1.3 para crear la siguiente historia del flujo.

### Lista de notas de cierre

- Se endurecio la superficie de WhatsApp para V1 sin moverla fuera de `WhatsAppPage`.
- La UI ahora permite elegir una cuenta existente, editarla y alternar entre alta y edicion con copy mas claro.
- El `verify_token` se mantiene global cuando existe configuracion central y queda editable por cuenta cuando no hay token global.
- Se agrego cobertura backend para setup, verificacion de webhook, firma HMAC, alta/listado/prueba de cuenta y `404` cross-tenant.
- Se dejo explicitado que el acceso cross-tenant sigue siendo `404`, mientras que el acceso sin permiso de modulo se resuelve con `403` por el control de autorizacion existente.
- Se agrego criterio verificable para el procesamiento inbound de WhatsApp, incluyendo mensajes entrantes e interacciones asociadas al tenant, contacto y conversacion.
- Se agrego un test dedicado para el webhook inbound happy path con verificacion de contacto, conversacion y mensaje creados.
- `backend/.venv/bin/pytest backend/tests/test_whatsapp_setup.py backend/tests/test_tenant_and_orders.py backend/tests/test_user_permissions.py`, `npm run build` y `npm run lint` pasaron.
- 2026-06-15: Se re-ejecuto la regresion backend ampliada y paso con `52 passed`, incluyendo el test dedicado del webhook inbound de WhatsApp.

### Lista de archivos

- `_bmad-output/implementation-artifacts/1-4-configurar-whatsapp-cloud-api-del-tenant.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/tests/test_whatsapp_setup.py`
- `frontend/src/App.tsx`

### Registro de cambios

- 2026-06-12: Implementada y validada la configuracion V1 de WhatsApp Cloud API con pruebas de webhook, firma, alta/listado/prueba de cuenta y ajuste de la UI.
- 2026-06-12: Addressed code review findings - split access semantics into `404` cross-tenant y `403` same-tenant module permissions, y made inbound WhatsApp processing an explicit acceptance criterion for V1.
- 2026-06-12: Adjusted story coverage to exclude `FR032` y `FR035`, which remain outside the explicit acceptance criteria for this V1 story.
- 2026-06-12: Agregado un test de camino feliz para el webhook entrante dedicado de WhatsApp y documentado en el registro de la historia.
- 2026-06-15: Re-validated the WhatsApp story with the backend regression suite after adding the inbound webhook happy-path test.
- 2026-06-12: Creada la historia 1.4 con criterios de aceptacion, tareas, notas de dev y referencias para desarrollo.
