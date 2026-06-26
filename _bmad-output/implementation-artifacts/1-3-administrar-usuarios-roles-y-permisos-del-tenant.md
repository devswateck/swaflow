---
title: "Historia 1.3: Administrar usuarios, roles y permisos del tenant"
status: done
baseline_commit: 533ce87609109706230237ebe5629fd34c324fa9
---

# Historia 1.3: Administrar usuarios, roles y permisos del tenant

Status: done

## Historia

Como admin principal del tenant,
Quiero crear y administrar usuarios adicionales con permisos modulables,
para que mi equipo opere la cuenta sin exponer modulos restringidos por defecto.

## Criterios de aceptación

1. Dado que el admin principal abre la gestion de usuarios, when crea o habilita un usuario adicional, then el sistema muestra un aviso resaltado de costo mensual antes o durante la accion y deja claro que el rol base no cambia.
2. Dado que un usuario adicional se crea o habilita, when se persiste su acceso inicial, then el sistema le asigna por defecto solo Dashboard, Inbox, Productos, Inventario, Ordenes y Citas.
3. Dado que el admin configura permisos por modulo, when habilita WhatsApp, IA, Funnels, Integraciones o Configuracion para un usuario adicional, then el sistema concede ese acceso sin cambiar el rol base del usuario.
4. Dado que un usuario sin permiso de un modulo restringido intenta entrar por navegacion directa o ejecutar una accion del backend, when llega al sistema, then la operacion se bloquea en backend aunque la opcion no se vea en la interfaz.
5. Dado que el tenant requiere operar con un solo admin principal, when se valida la estructura inicial de la cuenta, then el sistema conserva un usuario admin principal por tenant y Swateck puede seguir creando el tenant y su admin por proceso operativo interno, sin self-service signup en V1.
6. Dado que un usuario no pertenece al tenant o intenta acceder a datos ajenos, when consulta, actualiza o elimina un usuario de otra empresa, then el sistema responde `404` y no expone recursos entre tenants.
7. Dado que el admin necesita cambiar o resetear contrasenas, when usa la gestion de usuarios o el flujo de seguridad, then el sistema respeta permisos y mantiene intacto el flujo actual de cambio de contrasena propia.

**FR cubiertos:** FR127, FR128, FR129, FR130, FR131, FR132, FR133, FR134, FR135, FR136, FR137, FR138, FR139

## Tareas / Subtareas

- [x] Extender el modelo `User` para guardar permisos por modulo de forma tenant-scoped, sin alterar el rol base.
  - [x] Definir la forma persistida del permiso de modulo y su default seguro para usuarios adicionales.
  - [x] Mantener `owner`, `admin`, `agent`, `viewer` y `superadmin` como roles validos, con `superadmin` solo para Swateck.
- [x] Actualizar `UserCreate`, `UserUpdate`, `UserRead` y el payload de `/auth/me` para leer y exponer el estado necesario de permisos.
  - [x] Incluir la informacion minima para que la UI pinte accesos permitidos, bloqueos y estado activo/inactivo.
- [x] Reforzar `backend/app/users/service.py` y `backend/app/users/routes.py` con validaciones de acceso por modulo y aislamiento por `company_id`.
  - [x] Reusar el patron de `404` para otros tenants.
  - [x] Usar `403` para denegacion real de permisos dentro del mismo tenant.
- [x] Definir helpers de autorizacion reutilizables para la navegacion y las rutas sensibles.
  - [x] No confiar solo en ocultar items de la UI.
  - [x] Aplicar los checks en acciones de backend, no solo en el shell React.
- [x] Mantener el bootstrap del tenant y del owner principal sin romper la creacion de la cuenta inicial.
  - [x] No convertir esta story en self-service signup.
  - [x] No cambiar el flujo de login ni el cambio de contrasena propia.
- [x] Actualizar `frontend/src/App.tsx` para administrar usuarios desde `Configuracion`.
  - [x] Mostrar lista de usuarios del tenant, alta, edicion, desactivacion, reset de contrasena y permisos por modulo.
  - [x] Mostrar el aviso de costo mensual antes o durante la creacion/habilitacion de usuarios adicionales.
  - [x] Ocultar o bloquear accesos restringidos en la navegacion con un helper centralizado.
- [x] Agregar migracion Alembic compatible con MySQL para los campos nuevos.
  - [x] Evitar una migration que rompa SQLite en tests.
  - [x] Backfillear permisos por defecto para usuarios existentes.
- [x] Agregar pruebas de backend para permisos, CRUD de usuarios y aislamiento cross-tenant.
  - [x] Cubrir acceso permitido, acceso denegado y `404` para tenant ajeno.
  - [x] Cubrir default access matrix para usuarios adicionales.
- [x] Verificar `pytest`, `npm run build` y `npm run lint` al final del cambio.

## Notas de desarrollo

### Contexto de negocio

- Esta story aterriza la parte de Epic 1 que convierte la cuenta del tenant en una operacion de equipo, no solo de un admin unico.
- El alcance V1 exige que el admin principal pueda habilitar modulos restringidos por usuario sin tocar el rol base.
- El producto ya contempla que los usuarios adicionales no tengan acceso por defecto a WhatsApp, IA, Funnels, Integraciones ni Configuracion.
- La experiencia UX del proyecto ubica `Ajustes` como el area para tenant, usuarios, permisos, password y modo de negocio.

### Reglas criticas a preservar

- Mantener aislamiento multi-tenant por `company_id` en lectura y escritura.
- No ampliar permisos cross-tenant salvo la excepcion explicita de superadmin ya contemplada en backend.
- No romper `swaflow_theme` ni `swaflow_active_page`.
- No inventar accesos, usuarios ni permisos que no existan en backend.
- Mantener mensajes visibles en espanol.
- El backend sigue siendo la fuente de verdad para permisos; la UI solo refleja y bloquea de forma preventiva.

### Estado actual del codigo

- `backend/app/users/models.py` solo guarda `name`, `email`, `password_hash`, `role` y `status` por usuario.
- `backend/app/users/service.py` ya valida roles y hace CRUD basico, pero no tiene matriz de permisos por modulo.
- `backend/app/users/routes.py` ya expone listar, crear, ver, actualizar, resetear password y desactivar usuarios.
- `backend/app/auth/service.py` solo conoce `role` para el token y `require_roles`; no existe un helper de permisos por modulo.
- `backend/app/auth/schemas.py` y `build_current_user_payload()` no exponen permisos de modulo al frontend.
- `frontend/src/App.tsx` ya tiene `SettingsPage`, pero hoy solo maneja perfil del tenant, branding y cambio de contrasena propia.
- `frontend/src/App.tsx` ya usa `currentUser.role` para mostrar estado, pero no hay un helper centralizado de permisos por modulo.

### Que debe cambiar

- Se necesita persistir acceso por modulo para usuarios adicionales sin alterar el rol base.
- La UI de Configuracion debe incluir gestion operativa de usuarios, no solo perfil y seguridad individual.
- Las rutas del backend deben aplicar permisos reales para modulos restringidos, especialmente Configuracion y cualquier accion de administracion de usuarios.
- El frontend debe ocultar o bloquear las superficies restringidas, pero nunca depender solo de eso.

### Inference explicita para la solucion

- No existe hoy un modelo de permisos independiente, asi que la extension mas segura es agregar permisos por modulo al propio usuario o a un campo equivalente tenant-scoped.
- La forma esperada de permisos puede ser una lista o mapa JSON con llaves estables por modulo. Lo importante es que sea persistente, versionable y sencilla de validar en backend.
- Para V1, la matriz inicial debe alinearse con la UX aprobada: usuario adicional con acceso por defecto a Dashboard, Inbox, Productos, Inventario, Ordenes y Citas; el resto se concede de forma explicita.
- La habilitacion de permisos no debe cambiar el `role` base del usuario. El rol sigue sirviendo para la capacidad general; el permiso por modulo refina el acceso.
- El flujo de cambio de contrasena propia ya existe en `/auth/password` y debe mantenerse separado del reset administrado por owner/admin.

### Arquitectura y salvaguardas

- Seguir el patron de backend por dominio: `backend/app/users/`, `backend/app/auth/`, `backend/app/companies/`.
- No introducir un router nuevo ni un modulo generico de settings solo para esto.
- Si hace falta un helper, debe vivir en el dominio correspondiente y ser reutilizable por rutas y servicios.
- `404` sigue siendo la respuesta correcta para otros tenants.
- `403` sigue siendo la respuesta correcta para denegacion real de permisos dentro del tenant.
- Los checks de permisos deben existir tanto en la navegacion del frontend como en las rutas/servicios que mutan datos.
- Preservar el comportamiento de superadmin como excepcion explicita para Swateck, con auditoria donde aplique.

### File Structure Notes

- Backend candidato a tocar:
  - `backend/app/users/models.py`
  - `backend/app/users/schemas.py`
  - `backend/app/users/service.py`
  - `backend/app/users/routes.py`
  - `backend/app/auth/schemas.py`
  - `backend/app/auth/service.py`
  - `backend/migrations/versions/20260610_0012_*.py`
  - `backend/tests/test_tenant_and_orders.py` o un nuevo test module dedicado
- Frontend candidato a tocar:
  - `frontend/src/App.tsx`
- No tocar archivos ajenos si el cambio cabe en los dominios anteriores.

### Testing requirements

- Cubrir la creacion o edicion de usuarios adicionales con permisos por defecto.
- Cubrir la activacion de un modulo restringido para un usuario adicional sin modificar el rol base.
- Cubrir denegacion de backend cuando un usuario sin permiso intenta entrar a un modulo restringido.
- Cubrir `404` cross-tenant para lectura y escritura de usuarios.
- Cubrir que `owner/admin` mantengan la capacidad de gestionar usuarios del tenant y que `superadmin` conserve la excepcion ya existente.
- Mantener compatibilidad con SQLite en memoria para la suite de tests.
- Si se agrega una columna JSON o equivalente, verificar que la migracion y los defaults no rompan MySQL.

### Previous story intelligence

- La story 1.2 ya dejo listo el area de `Configuracion` para el perfil del tenant y el branding visual.
- `SettingsPage` ya carga el tenant por `currentUser.company_id` y usa `api<T>()`; conviene extender ese flujo en lugar de crear otro panel aislado.
- La historia anterior refuerza un patron importante: la UI debe mostrar estados honestos y nunca inventar recursos o accesos.
- No hay aprendizaje previo que justifique un nuevo router o una reestructura completa del shell.

### Project Structure Notes

- La UX del proyecto ubica `Ajustes` como area de administracion de tenant, usuarios y permisos, asi que esta story debe vivir ahi.
- No crear una superficie paralela de administracion solo para usuarios.
- El backend ya tiene el dominio `users`; esta story debe extenderlo, no reemplazarlo.
- Si la implementacion necesita un helper compartido de permisos, mantenerlo pequeno y proximo al dominio para no introducir abstracciones innecesarias.

## References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 1, Historia 1.3, cobertura FR FR127-FR139]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - Product scope, tenant administration y V1 access model]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - App Shell, state patterns, Inbox/Admin structure]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - Navigation groups y `Ajustes` placement for tenant, users, permissions y password]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/DESIGN.md` - Brand, layout y component guidance]
- [Source: `backend/app/users/models.py`]
- [Source: `backend/app/users/routes.py`]
- [Source: `backend/app/users/service.py`]
- [Source: `backend/app/users/schemas.py`]
- [Source: `backend/app/auth/service.py`]
- [Source: `backend/app/auth/schemas.py`]
- [Source: `backend/app/companies/service.py`]
- [Source: `frontend/src/App.tsx` - `SettingsPage`, `CurrentUser`, shell y account area]
- [Source: `backend/tests/test_tenant_and_orders.py`]
- [Source: `_bmad-output/implementation-artifacts/1-2-gestionar-branding-visual-del-tenant.md` - previous story learnings y SettingsPage pattern]

## Dev Agent Record

### Agent Model Used

GPT-5

### Referencias de depuración

- 2026-06-10: Cargada la historia, el sprint status y el contexto del proyecto; se identifico que la story estaba en `ready-for-dev`.
- 2026-06-10: Se implemento el modelo `module_permissions`, helpers de autorizacion, guards en rutas sensibles y la UI de administracion de usuarios en `Configuracion`.
- 2026-06-10: Se agrego la migracion Alembic para `users.module_permissions` con backfill de permisos seguros y se cubrio el comportamiento con pruebas de backend.
- 2026-06-10: Validacion final ejecutada con `pytest`, `npm run lint` y `npm run build`.
- 2026-06-12: Se endurecio la invariants de ultimo privilegiado activo con `status` tipado a `active|inactive` y locking de fila para evitar carreras concurrentes.
- 2026-06-12: Se agregaron pruebas para rechazo de `status` invalido, bloqueo del ultimo `owner/admin` y verificacion del uso de `FOR UPDATE`.
- 2026-06-12: Se reemplazo el lock sobre `users` por un lock serializado de `companies` para eliminar el riesgo de deadlock en operaciones concurrentes.
- 2026-06-12: Se ajusto la prueba de concurrencia para verificar el lock de tenant y se mantuvieron verdes las suites de backend.

### Lista de notas de cierre

- Se agrego permisos por modulo tenant-scoped a `User` sin alterar el rol base y con defaults seguros para usuarios adicionales.
- Se expuso el estado de permisos en `UserRead` y `/auth/me`, y se reforzaron rutas y servicios con `403` dentro del tenant y `404` cross-tenant.
- Se mantuvo el bootstrap de owner y superadmin, y se dejo intacto el flujo de login y cambio de contrasena propia.
- Se implemento administracion de usuarios dentro de `Configuracion` con alta, edicion, desactivacion, reset de contrasena y edicion de permisos por modulo.
- Se agrego la migracion `20260610_0012` y pruebas de backend para defaults, acceso restringido y aislamiento multi-tenant.
- Se restringio `status` de usuarios a `active|inactive` y se protegio la invariants del ultimo privilegio activo con locking transaccional.
- Se serializaron las operaciones sensibles por tenant mediante lock de `companies` para evitar deadlocks entre updates concurrentes.

### Lista de archivos

- `backend/app/users/models.py`
- `backend/app/users/schemas.py`
- `backend/app/users/service.py`
- `backend/app/users/routes.py`
- `backend/app/auth/schemas.py`
- `backend/app/users/permissions.py`
- `backend/app/auth/service.py`
- `backend/app/companies/service.py`
- `backend/app/companies/routes.py`
- `backend/app/ai/routes.py`
- `backend/app/funnels/routes.py`
- `backend/app/integrations/routes.py`
- `backend/app/whatsapp/routes.py`
- `backend/app/management.py`
- `backend/migrations/versions/20260610_0012_user_module_permissions.py`
- `backend/tests/test_tenant_and_orders.py`
- `backend/tests/test_user_permissions.py`
- `frontend/src/App.tsx`

### Registro de cambios

- 2026-06-10: Implementada administracion de usuarios con permisos por modulo tenant-scoped, enforcement en backend y UI de Configuracion con migration y pruebas.
- 2026-06-12: Corregidos los hallazgos de revision sobre `status` libre y carreras concurrentes al preservar el ultimo `owner/admin` activo.
