---
title: "Historia 1.1: Configurar perfil base del tenant"
status: done
baseline_commit: 533ce87609109706230237ebe5629fd34c324fa9
---

# Historia 1.1: Configurar perfil base del tenant

Status: done

## Historia

Como admin principal del tenant,
Quiero editar los datos basicos y operativos de mi empresa,
para que la plataforma refleje correctamente la identidad administrativa del tenant.

## Criterios de aceptación

1. Dado que el admin principal esta autenticado en Configuracion, when abre la vista de perfil del tenant, then el sistema muestra los datos actuales de la empresa y no inventa valores faltantes.
2. Dado que el admin edita nombre comercial, datos de contacto, moneda, zona horaria y modo de negocio, when guarda los cambios, then el sistema persiste la informacion en el tenant correcto y la vuelve a mostrar al recargar.
3. Dado que otro tenant o un usuario sin acceso intenta leer o modificar esa configuracion, when llega al backend, then el sistema responde `404` para mantener el aislamiento multi-tenant.
4. Dado que el tenant no ha cargado un campo, when se renderiza la UI, then se muestra un estado vacio o placeholder honesto, nunca datos falsos.

## Tareas / Subtareas

- [x] Extender el modelo `Company` para guardar los campos base del perfil del tenant.
- [x] Actualizar `CompanyRead` y `CompanyUpdate` para exponer y validar los nuevos campos.
- [x] Mantener `CompanyCreate` enfocado en bootstrap inicial y no mezclarlo con el editor de perfil.
- [x] Crear la migracion Alembic para alterar `companies` sin romper compatibilidad MySQL.
- [x] Preservar la regla de aislamiento: `404` cuando un usuario intente acceder a otra empresa.
- [x] Actualizar `SettingsPage` en `frontend/src/App.tsx` para cargar y guardar el perfil del tenant con `api<T>()`.
- [x] Mantener el flujo de contrasena actual intacto dentro de Configuracion.
- [x] Agregar pruebas de servicio y de acceso para cambio de perfil y aislamiento cross-tenant.
- [x] Verificar `npm run build`, `npm run lint` y la suite backend relevante.

## Notas de desarrollo

### Contexto de negocio

- Esta es la primera story de la Epic 1, asi que no hay story previa que heredar.
- La Epic 1 cubre la base del tenant, roles y configuracion del asistente; esta story fija el perfil administrativo base del tenant antes de WhatsApp, IA, funnels e integraciones.
- El PRD y el breakdown de epics dejan claro que el tenant debe poder reflejar nombre, contacto, moneda, zona horaria y modo de negocio.
- El lanzamiento V1 no usa self-service signup de tenants; la creacion inicial del tenant y su owner sigue siendo operativa/admin.

### Reglas criticas a preservar

- Mantener aislamiento multi-tenant por `company_id` en lectura y escritura.
- No convertir esta story en un redisenio del shell ni en un router nuevo.
- No romper `swaflow_theme` ni `swaflow_active_page`; el estado visual del frontend ya existe y debe seguir funcionando.
- No inventar datos de empresa, imagenes o defaults no persistidos.
- Mantener mensajes visibles en espanol.
- No ampliar permisos cross-tenant salvo la excepcion explicita de superadmin ya contemplada en backend.

### Estado actual del codigo

- `backend/app/companies/models.py` solo tiene `name` y `status`.
- `backend/app/companies/schemas.py` solo expone `name` y `status` en create/update/read.
- `backend/app/companies/service.py` ya tiene `get_company_for_user()` y `update_company()`, con `404` para company ajena.
- `backend/app/companies/routes.py` ya expone `GET /companies/{company_id}` y `PUT /companies/{company_id}`.
- `frontend/src/App.tsx` ya tiene `SettingsPage`, pero hoy solo maneja contrasena y metadatos de cuenta; no edita perfil de empresa.
- `frontend/src/App.tsx` ya obtiene `currentUser.company_id` desde `/auth/me`, asi que el frontend puede cargar la empresa correcta sin un nuevo store.

### Que debe cambiar

- La base de datos necesita nuevos campos para identidad, contacto, moneda, zona horaria y modo de negocio del tenant.
- El servicio de companies debe aceptar y devolver esos campos sin perder el comportamiento actual de `404` en otras empresas.
- La UI de Configuracion debe convertirse en el editor del perfil del tenant, no solo del password.

### Que debe preservarse

- El flujo de login, logout y password change.
- El shell global React/Vite con tema por defecto oscuro y grupo de navegacion existente.
- La convencion de usar `api<T>()` para HTTP y Zustand para auth/token.
- El estilo de monolito frontend en `App.tsx` salvo que una extraccion reduzca complejidad real.
- La disciplina de backend por dominio (`companies`, `auth`, `users`, etc.).

### Inference explicita para assets

- La gestion de logo, banner y profile visual queda fuera de esta historia.
- No existe un servicio de storage de assets de empresa ya consolidado en el repo.
- La implementacion de assets debe tratarse como una historia separada con una decision tecnica explicita sobre uploads, URLs o storage.

### Testing requirements

- Agregar pruebas de servicio para update del perfil de company y para el `404` cross-tenant.
- Mantener la base de tests compatible con SQLite en memoria, pero sin introducir SQL que solo funcione en SQLite.
- Verificar que la actualizacion de company no rompa bootstrap de owner ni el flujo existente de auth.
- Agregar cobertura de frontend solo si el repo ya usa tests de UI para esta zona; si no, al menos asegurar build/lint.

### Project Structure Notes

- El dominio correcto para este cambio es `backend/app/companies/`.
- No crear un modulo generico nuevo de `settings` en backend para esta historia; la configuracion de identidad pertenece a `companies`.
- En frontend, mantener el cambio dentro de `frontend/src/App.tsx` salvo una extraccion pequena y clara.
- Si se requiere estilo nuevo para estados vacios, reutilizar `frontend/src/styles.css` y `frontend/tailwind.config.ts` sin romper la marca Swa Tech.

## References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 1, Historia 1.1, cobertura FR FR120-FR123, FR143-FR144]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - Product scope, tenant administration, business mode y branding requirements]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - App Shell, State Patterns, Sequence of Implementation]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/DESIGN.md` - Colors, Layout & Spacing, Components]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - Settings / navigation patterns, copy, y shell behavior]
- [Source: `backend/app/companies/models.py`]
- [Source: `backend/app/companies/routes.py`]
- [Source: `backend/app/companies/schemas.py`]
- [Source: `backend/app/companies/service.py`]
- [Source: `frontend/src/App.tsx` - `SettingsPage`, `getStoredTheme`, shell y account area]
- [Source: `frontend/src/styles.css`]
- [Source: `frontend/tailwind.config.ts`]
- [Source: `backend/tests/test_tenant_and_orders.py`]

## Dev Agent Record

### Agent Model Used

GPT-5

### Referencias de depuración

- Cargue el contexto del proyecto, el sprint-status y la historia 1.1 antes de editar.
- Revi el modelo, schemas, servicio, rutas, `SettingsPage` y los tests existentes para extender el perfil del tenant sin romper el flujo de contrasena.
- Implemente los campos de perfil del tenant en backend, migracion Alembic, pruebas de aislamiento y editor de Configuracion en frontend.
- Verifique la suite backend relevante, `npm run build` y `npm run lint` con exito.
- Resolvi el hallazgo de review sobre autorizacion del perfil del tenant; ahora lectura y escritura responden `404` para usuarios sin acceso.

### Lista de notas de cierre

- Se agregaron al modelo `Company` los campos `contact_email`, `contact_phone`, `currency`, `timezone` y `business_mode`.
- `CompanyRead` y `CompanyUpdate` ahora exponen y validan el perfil base del tenant; `CompanyCreate` permanecio solo para bootstrap inicial.
- Se creo la migracion `20260610_0010_company_profile_fields` para alterar `companies` de forma compatible con MySQL.
- `SettingsPage` ahora carga el perfil de empresa por `company_id`, permite editarlo y lo guarda con `api<T>()` sin afectar el flujo de cambio de contrasena.
- Se agregaron pruebas para persistencia del perfil y bloqueo `404` cross-tenant.
- Validaciones ejecutadas: `pytest backend/tests -q` (`25 passed`), `npm run build`, `npm run lint`.

### Lista de archivos

- `backend/app/companies/models.py`
- `backend/app/companies/schemas.py`
- `backend/app/companies/routes.py`
- `backend/app/companies/service.py`
- `backend/migrations/versions/20260610_0010_company_profile_fields.py`
- `backend/tests/test_tenant_and_orders.py`
- `frontend/src/App.tsx`

### Registro de cambios

- 2026-06-10: Se implemento el perfil base del tenant con nuevos campos operativos, migracion MySQL, editor en Configuracion y pruebas de aislamiento.
- 2026-06-10: Se ajusto la autorizacion del perfil del tenant para responder `404` a usuarios sin acceso, incluyendo el caso de usuarios del mismo tenant sin permisos.
- 2026-06-16: Se cerro la story y se alino el artefacto con el estado `Done` ya reflejado en sprint-status.
