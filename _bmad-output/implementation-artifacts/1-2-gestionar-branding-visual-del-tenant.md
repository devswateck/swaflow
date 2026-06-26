---
title: "Historia 1.2: Gestionar branding visual del tenant"
status: done
baseline_commit: 533ce87609109706230237ebe5629fd34c324fa9
---

# Historia 1.2: Gestionar branding visual del tenant

Status: done

## Historia

Como admin principal del tenant,
Quiero configurar los activos visuales de mi empresa,
para que la plataforma y las comunicaciones operativas usen la marca correcta del tenant.

## Criterios de aceptación

1. Dado que el admin principal esta autenticado en Configuracion, when carga o actualiza el logo de marca visible del shell y los assets de banner/profile para comunicaciones, then el sistema guarda los assets asociados solo al `company_id` del tenant.
2. Dado que otro tenant intenta leer o modificar esos activos, when llega al backend, then el sistema responde `404` y no expone recursos entre empresas.
3. Dado que el tenant tiene assets configurados, when se generan correos operativos o se renderizan vistas asociadas, then los assets guardados pueden reutilizarse sin introducir mocks ni datos de otra empresa.
4. Dado que el tenant no ha cargado un asset, when se renderiza la UI, then se muestra un placeholder honesto o estado vacio.

## Tareas / Subtareas

- [x] Extender `Company` o el modelo de assets correspondiente para asociar `logo_url`, `banner_url` y `profile_url` al tenant correcto.
- [x] Actualizar `CompanyRead` y `CompanyUpdate` o el esquema equivalente para exponer estado y referencias de assets.
- [x] Crear la migracion Alembic necesaria sin romper compatibilidad MySQL.
- [x] Preservar la regla de aislamiento: `404` cuando un usuario intente acceder a assets de otra empresa.
- [x] Actualizar `SettingsPage` en `frontend/src/App.tsx` para mostrar y guardar el branding visual con `api<T>()` si el flujo se resuelve en Configuracion.
- [x] Mostrar preview de las URLs o placeholder honesto sin inventar assets.
- [x] Agregar pruebas de servicio y de acceso para carga, lectura y aislamiento cross-tenant.
- [x] Verificar `npm run build`, `npm run lint` y la suite backend relevante.

## Notas de desarrollo

### Contexto de negocio

- Esta story separa el branding visual del perfil base del tenant para evitar mezclar datos operativos con almacenamiento de assets.
- La Epic 1 contempla branding, identidad y configuracion del asistente, pero el alcance de assets necesita una implementacion propia.
- La UI no debe inventar imagenes ni usar recursos de otra empresa como fallback silencioso.

### Reglas criticas a preservar

- Mantener aislamiento multi-tenant por `company_id` en lectura y escritura.
- No convertir esta story en un redisenio del shell ni en un modulo generico nuevo.
- No romper `swaflow_theme` ni `swaflow_active_page`.
- No inventar datos de marca, imagenes o placeholders falsos.
- Mantener mensajes visibles en espanol.

### Estado actual del codigo

- `backend/app/companies/models.py` hoy solo cubre identidad y status basicos.
- `backend/app/companies/schemas.py` no expone campos de branding visual.
- `backend/app/companies/service.py` ya aplica `404` para company ajena.
- `frontend/src/App.tsx` tiene `SettingsPage` y puede ampliarse para mostrar assets si el flujo vive ahi.

### Que debe cambiar

- La implementacion persiste `logo_url`, `banner_url` y `profile_url` como referencias tenant-scoped.
- El backend debe responder con estado y referencias seguras para renderizar el branding.
- La UI debe mostrar preview o placeholder honesto, sin mocks.

### Que debe preservarse

- El flujo de login, logout y password change.
- El shell global React/Vite con tema por defecto oscuro y grupo de navegacion existente.
- La convencion de usar `api<T>()` para HTTP y Zustand para auth/token.
- La disciplina de backend por dominio (`companies`, `auth`, `users`, etc.).

### Inference explicita para assets

- No existe un servicio de storage de assets de empresa ya consolidado en el repo.
- La historia usa URLs o referencias persistidas para `logo_url`, `banner_url` y `profile_url`, todas tenant-scoped.
- `logo_url` representa la marca visible del shell y debe alinearse con `SWAFLOW`; `banner_url` y `profile_url` son assets reutilizables para comunicaciones operativas.
- La implementacion debe extender `companies` o sus schemas/servicios asociados antes de crear cualquier modulo nuevo; solo abrir un submodulo de assets si hay una necesidad tecnica demostrable.
- Si en el futuro se requieren uploads, ese flujo se tratara como una historia separada con storage dedicado.

### Testing requirements

- Agregar pruebas de servicio para lectura, escritura y `404` cross-tenant.
- Mantener la base de tests compatible con SQLite en memoria, sin introducir SQL que solo funcione en SQLite.
- Verificar que la historia no rompa el bootstrap del tenant ni el flujo de auth.
- Agregar cobertura de frontend solo si el repo ya usa tests de UI para esta zona; si no, al menos asegurar build/lint.

### Project Structure Notes

- El dominio correcto para este cambio sigue siendo `backend/app/companies/` salvo que la decision tecnica exija un submodulo de assets.
- No crear un modulo generico nuevo de `settings` en backend para esta historia.
- En frontend, mantener el cambio dentro de `frontend/src/App.tsx` salvo una extraccion pequena y clara.
- Si se requiere estilo nuevo para previews o placeholders, reutilizar `frontend/src/styles.css` y `frontend/tailwind.config.ts`.

## References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 1, Historia 1.2, cobertura FR FR121, FR124-FR126]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - Product scope, tenant branding y asset requirements]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - App Shell, State Patterns, Sequence of Implementation]
- [Source: `_bmad-output/implementation-artifacts/spec-swaflow-visual-shell.md` - SWAFLOW branding, dark default shell, y token constraints]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/DESIGN.md` - Colors, Layout & Spacing, Components]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - Settings / navigation patterns, copy, y shell behavior]
- [Source: `backend/app/companies/models.py`]
- [Source: `backend/app/companies/routes.py`]
- [Source: `backend/app/companies/schemas.py`]
- [Source: `backend/app/companies/service.py`]
- [Source: `frontend/src/App.tsx` - `SettingsPage`, `getStoredTheme`, shell y account area]
- [Source: `frontend/src/styles.css`]
- [Source: `frontend/tailwind.config.ts`]

## Dev Agent Record

### Agent Model Used

GPT-5

### Referencias de depuración

- `backend/.venv/bin/pytest tests/test_tenant_and_orders.py`
- `npm run build`
- `npm run lint`

### Lista de notas de cierre

- Se extendio `Company` con `logo_url`, `banner_url` y `profile_url` como campos tenant-scoped.
- Se actualizaron `CompanyUpdate` y `CompanyRead` para leer y escribir branding visual sin romper el aislamiento.
- Se agrego la migracion Alembic `20260610_0011_company_branding_assets.py` compatible con MySQL.
- Se conecto `SettingsPage` para persistir branding visual y mostrar previews honestos o estados vacios.
- Se agregaron pruebas de lectura, escritura y aislamiento cross-tenant para los assets de branding.
- `npm run build`, `npm run lint` y la suite backend relevante pasaron.

### Lista de archivos

- `backend/app/companies/models.py`
- `backend/app/companies/schemas.py`
- `backend/app/companies/service.py`
- `backend/app/companies/routes.py`
- `backend/migrations/versions/20260610_0010_company_profile_fields.py`
- `backend/migrations/versions/20260610_0011_company_branding_assets.py`
- `backend/tests/test_tenant_and_orders.py`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `frontend/tailwind.config.ts`

### Registro de cambios

- 2026-06-10: Implementado branding visual del tenant con persistencia de URLs, previews honestos en Configuracion, migracion MySQL y pruebas de aislamiento.
- 2026-06-10: Validado el branding runtime del shell y sincronizacion inmediata tras guardar el perfil del tenant.
