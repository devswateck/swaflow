---
title: "Historia 1.5: Definir funnel de bienvenida y captura inicial"
status: done
baseline_commit: 533ce87609109706230237ebe5629fd34c324fa9
---

# Historia 1.5: Definir funnel de bienvenida y captura inicial

Status: done

## Historia

Como admin principal del tenant,
Quiero configurar el funnel de bienvenida y sus reglas de captura,
para que las conversaciones nuevas entren con un punto de partida comercial consistente y la IA capture la informacion inicial correcta sin pedir datos que ya vienen desde WhatsApp.

## Criterios de aceptación

1. Dado que se crea un tenant nuevo, when el sistema inicializa sus funnels, then existe un funnel de bienvenida por defecto, activo y marcado como `is_default=true`, sin duplicarlo para el mismo tenant.
2. Dado que el funnel de bienvenida se edita, when el admin define los campos iniciales, then el sistema permite capturar Nombre, Correo y Ciudad, y toma el telefono desde WhatsApp sin pedirlo como campo obligatorio si ya esta disponible.
3. Dado que el admin define la logica de clasificacion, when guarda criterios y pasos del funnel, then cada paso admite prompt, objetivos, criterio de transicion, estado y configuracion, y la intencion del cliente se completa desde el funnel y la clasificacion conversacional, no como campo manual obligatorio.
4. Dado que el tenant necesita mas flujos, when el admin crea funnels adicionales, then puede definir nombre, descripcion, estado y criterios de asignacion, y usar pasos personalizables para distintos productos, servicios o intenciones sin afectar el funnel de bienvenida.
5. Dado que una conversacion nueva entra al sistema, when no existe una asignacion manual previa, then la IA usa el funnel de bienvenida como punto de entrada y el Inbox puede mostrar y filtrar el funnel y paso actual del hilo.

**FR cubiertos:** FR076, FR077, FR078, FR079, FR080, FR081, FR082, FR083, FR084, FR085, FR086, FR087, FR155, FR156, FR157

## Tareas / Subtareas

- [x] Extender el dominio `funnels` para persistir el funnel de bienvenida como entidad real del tenant y asegurar que solo exista un default por company.
  - [x] Definir el contrato de persistencia para mensaje inicial, campos a capturar y criterios de asignacion sin crear una segunda fuente de verdad en IA.
  - [x] Mantener la logica tenant-scoped y compatible con MySQL y SQLite en tests.
- [x] Actualizar `SalesFunnel` y `SalesFunnelStep` para soportar la configuracion operacional del funnel de bienvenida y de funnels adicionales.
  - [x] Reusar `is_default`, `steps` y `SalesFunnelStep.config` cuando sea posible antes de introducir nuevas tablas.
  - [x] Si hace falta metadata adicional, agregarla en el dominio `funnels`, no en un modulo generico nuevo.
- [x] Asegurar que el bootstrap del tenant deje un funnel de bienvenida disponible o que exista un helper de inicializacion idempotente para crearlo al primer uso.
  - [x] Evitar duplicados si el helper corre mas de una vez.
  - [x] Mantener la creacion del tenant y del owner funcional en V1.
- [x] Conectar el flujo de conversaciones e IA al funnel de bienvenida como entrada por defecto.
  - [x] Reusar el contrato existente que ya alimenta `welcome_message`, `capture_fields` y `funnel_steps` en la IA.
  - [x] No crear un prompt paralelo ni duplicar reglas de captura en otra superficie.
- [x] Actualizar `frontend/src/App.tsx` en `FunnelsPage` y en el rail de Inbox para editar y visualizar el funnel de bienvenida sin romper la experiencia existente.
  - [x] Mantener el modulo Funnels como superficie propia, no moverlo a Configuracion.
  - [x] Mostrar estados vacios y copy operativo en espanol.
- [x] Agregar pruebas de backend para bootstrap/backfill del funnel default, edicion del funnel de bienvenida, pasos configurables y aislamiento cross-tenant.
  - [x] Cubrir que el tenant no termine con dos funnels de bienvenida marcados como default.
  - [x] Cubrir `404` para otro tenant y comportamiento honesto cuando falte configuracion.
- [x] Verificar la implementacion con `pytest`, `npm run build` y `npm run lint`.

## Notas de desarrollo

### Contexto de negocio

- Esta es la primera story de la parte de funnels en Epic 1.
- El PRD fija que cada tenant debe tener un funnel inicial de bienvenida y que la IA debe iniciar las conversaciones nuevas desde ese punto salvo regla explicita distinta.
- El funnel de bienvenida no es solo una etiqueta visual: debe ser el punto de arranque comercial para capturar datos iniciales y orientar la conversacion.
- Los campos iniciales V1 son Nombre, Correo y Ciudad. El telefono ya viene desde WhatsApp y no debe solicitarse como campo obligatorio si esta disponible.
- La intencion del cliente no debe pedirse como campo manual obligatorio de bienvenida; debe completarse desde el funnel y la clasificacion conversacional.

### Reglas criticas a preservar

- Mantener aislamiento multi-tenant por `company_id` en lectura y escritura.
- No crear una nueva superficie generica de settings para funnels.
- No duplicar la configuracion de captura en IA si ya existe un contrato de funnel capaz de alimentar ese contexto.
- No romper el shell global, `swaflow_theme` ni `swaflow_active_page`.
- No inventar campos, pasos o mensajes que no esten persistidos.
- Mantener copy visible en espanol y estados honestos cuando falte configuracion.

### Estado actual del codigo

- `backend/app/funnels/models.py` ya tiene `SalesFunnel`, `SalesFunnelStep`, `is_default`, `steps` y un `config` JSON por paso.
- `backend/app/funnels/service.py` ya soporta CRUD por tenant, selection de default y sincronizacion completa de pasos.
- `backend/app/funnels/routes.py` ya expone lista, create, update y delete protegidos por permisos de modulo.
- `backend/app/conversations/service.py` ya resuelve funnels y pasos por `company_id` y expone `assign_conversation_funnel`.
- `backend/app/ai/runtime.py` ya consume `welcome_message`, `capture_fields` y `funnel_steps` en el contrato de salida del agente.
- `frontend/src/App.tsx` ya tiene `FunnelsPage` y un rail de Inbox que permite asignar funnel y paso a una conversacion.

### Que debe cambiar

- El sistema debe garantizar un funnel de bienvenida por tenant sin duplicados y con datos suficientes para arranque comercial.
- La configuracion de captura debe persistirse dentro del dominio `funnels`, no como texto suelto en otra area.
- La IA y el Inbox deben usar el funnel de bienvenida como entrada por defecto, respetando la asignacion manual cuando exista.
- La UI de Funnels debe dejar de ser solo CRUD basico y mostrar claramente el funnel de bienvenida, sus pasos y la edicion de campos iniciales.

### Que debe preservarse

- El comportamiento actual de CRUD y asignacion de funnels en conversaciones.
- La separacion entre configuracion de funnels y configuracion de IA comercial base.
- El funcionamiento actual del Inbox y de la clasificacion manual desde conversaciones.
- La disciplina de backend por dominio (`funnels`, `conversations`, `ai`, `companies`).

### Inference explicita para la solucion

- El dominio ya tiene `is_default` y `steps`, asi que la extension mas segura es reutilizar esos mecanismos antes de agregar estructuras nuevas.
- Si hace falta metadata para el funnel de bienvenida, debe quedar en `SalesFunnel` o en `SalesFunnelStep.config`; no debe vivir en una tabla paralela salvo necesidad tecnica demostrable.
- La IA no debe depender de un JSON improvisado distinto del contrato actual; si la story necesita un puente hacia `welcome_message`, `capture_fields` y `funnel_steps`, debe ser un puente estable y tenant-scoped.
- Para V1, el riesgo principal no es la ausencia de CRUD sino la ausencia de un default real y consistente; la story debe cerrar ese hueco.

### Arquitectura y salvaguardas

- Seguir el patron de backend por dominio: `backend/app/funnels/`, `backend/app/conversations/`, `backend/app/ai/`, `backend/tests/`.
- No introducir un router nuevo ni un modulo generico de configuracion solo para funnels.
- La UI debe seguir consumiendo `api<T>()` y el estado de auth existente.
- Mantener la regla de `404` para recursos de otro tenant y no ocultar problemas reales de configuracion.

### File Structure Notes

- Backend candidato a tocar:
  - `backend/app/funnels/models.py`
  - `backend/app/funnels/schemas.py`
  - `backend/app/funnels/service.py`
  - `backend/app/funnels/routes.py`
  - `backend/app/conversations/service.py`
  - `backend/app/ai/runtime.py`
  - `backend/app/companies/service.py` o el flujo que crea tenants, si hace falta asegurar el funnel inicial
  - `backend/migrations/versions/20260616_*.py` si se requiere persistencia nueva
  - `backend/tests/test_tenant_and_orders.py` o un test dedicado para funnels
- Frontend candidato a tocar:
  - `frontend/src/App.tsx`
- No tocar dominios ajenos si el cambio cabe en los archivos anteriores.

### Testing requirements

- Cubrir que un tenant nuevo termina con un funnel de bienvenida disponible y marcado como default.
- Cubrir que no se crean dos welcome funnels por tenant si el helper de inicializacion corre mas de una vez.
- Cubrir edicion de mensaje inicial, campos de apertura y pasos del funnel.
- Cubrir `404` cross-tenant para lectura/escritura de funnels.
- Cubrir que la IA o el flujo de conversaciones pueden resolver el funnel de bienvenida como entrada por defecto cuando no hay asignacion manual previa.
- Mantener compatibilidad con la suite actual y con SQLite en memoria.

### Previous story intelligence

- La story 1.4 dejo claro que la superficie de WhatsApp debe quedarse en su pagina propia; esta story debe respetar la misma disciplina de no mover Funnels a Settings.
- La story 1.3 establecio el patron de permisos por modulo y el uso de `404`/`403` segun contexto; este modulo debe seguir ese mismo criterio.
- El proyecto ya usa mensajes en espanol, `api<T>()` y un shell operacional estable; esta story debe extender ese patron, no improvisar otro.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 1, Historia 1.5, cobertura FR FR076-FR087, FR155-FR157]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - Funnel de bienvenida, captura inicial, IA y modo de negocio]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - App Shell, Page Modules, Sequence of Implementation]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - Funnel en Inbox, rail contextual y configuracion del modulo Funnels]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/DESIGN.md` - identidad visual, comportamiento operacional y estados]
- [Source: `backend/app/funnels/models.py`]
- [Source: `backend/app/funnels/routes.py`]
- [Source: `backend/app/funnels/schemas.py`]
- [Source: `backend/app/funnels/service.py`]
- [Source: `backend/app/conversations/service.py`]
- [Source: `backend/app/ai/runtime.py`]
- [Source: `frontend/src/App.tsx` - `FunnelsPage`, rail de Inbox y asignacion de funnel]
- [Source: `_bmad-output/implementation-artifacts/1-4-configurar-whatsapp-cloud-api-del-tenant.md` - aprendizaje previo sobre no mover superficies propias a Settings]
- [Source: `_bmad-output/implementation-artifacts/1-3-administrar-usuarios-roles-y-permisos-del-tenant.md` - permisos por modulo y fronteras de acceso]

## Dev Agent Record

### Agent Model Used

GPT-5

### Referencias de depuración

- 2026-06-16: extendi `SalesFunnel` y `SalesFunnelStep` con `welcome_message`, `capture_fields` y `assignment_criteria`, y agregue migracion de persistencia para el dominio de funnels.
- 2026-06-16: implemente `ensure_welcome_funnel()` como bootstrap idempotente por tenant, y lo conecte en la creacion de compania y en la resolucion de conversaciones abiertas/nuevas.
- 2026-06-16: actualice `generate_auto_reply()` para consumir contexto del funnel de bienvenida y reutilizar el mensaje/campos/pasos cuando falte configuracion de agente.
- 2026-06-16: retrabaje `FunnelsPage` para editar el funnel de bienvenida, sus campos de captura, criterios de asignacion y pasos configurables sin romper el CRUD existente.
- 2026-06-16: valide con `backend/.venv/bin/pytest backend/tests -q`, `npm run build` y `npm run lint`.
- 2026-06-24: movi `record_audit()` dentro de la transaccion de alta de compania para evitar commits parciales si falla la auditoria, y agregue cobertura de rollback para ese caso.
- 2026-06-24: impedi que el funnel de bienvenida pueda dejar de ser el default del tenant y agregue cobertura de regresion para ese caso.
- 2026-06-24: reemplace la proteccion basada en `name` por `system_key='welcome'`, agregue migracion de backfill y bloquee que funnels no bienvenida asuman el rol de default desde backend y frontend.
- 2026-06-24: agregue una heuristica de recuperacion para tenants legacy sin `system_key` ni `is_default`, usando la firma operativa del funnel de bienvenida para evitar duplicados.
- 2026-06-25: cierre los hallazgos de review que permitian desactivar el funnel de bienvenida y que hacian commit desde `get_default_funnel()`, reforzando el invariant de funnel activo y eliminando el efecto secundario de persistencia en la resolucion del default.
- 2026-06-25: movi la reparacion de funnels legacy al camino de escritura de conversaciones para mantener `get_default_funnel()` puro y aun asi persistir el estado activo cuando la transaccion externa commitea.
- 2026-06-25: elimine la posibilidad de borrar el funnel de bienvenida por API, localice mensajes visibles de funnels en espanol y enderece la reparacion legacy para no fabricar un tercer funnel cuando existen candidatos duplicados.
- 2026-06-25: traduje los 404 visibles del flujo de conversaciones a espanol y elimine la entrada duplicada del `Lista de archivos`.

### Lista de notas de cierre

- El tenant nuevo queda bootstrappeado con un funnel de bienvenida por defecto, y el helper es idempotente para evitar duplicados.
- La IA y el flujo de conversaciones usan el funnel de bienvenida como contexto operativo cuando no existe una asignacion manual previa.
- La UI de Funnels ahora expone edicion de mensaje inicial, campos de captura, criterios de asignacion y pasos con configuracion operativa.
- La suite de backend y frontend paso completa tras los cambios.
- La creacion de companias ahora mantiene auditoria, funnel y owner dentro de una sola transaccion para evitar estados parcialmente confirmados.
- El funnel de bienvenida permanece como default estable del tenant y no puede desmarcarse desde la UI o la API.
- El rol de bienvenida ahora depende de `system_key='welcome'`, con backfill en migracion, y los funnels regulares no pueden asumir ni liberar el default del tenant.
- Valide la correccion con `backend/.venv/bin/pytest backend/tests -q`, `npm run build` y `npm run lint`.
- Los tenants legacy con el funnel renombrado y desmarcado quedan reparados por heuristica sin generar un segundo funnel de bienvenida.
- El funnel de bienvenida no puede quedar inactivo y `get_default_funnel()` ya no hace commit, asi que el bootstrap de conversaciones y WhatsApp mantiene atomicidad en la transaccion externa.
- La reparacion de tenants legacy ahora se persiste desde el flujo de conversaciones al momento del commit externo, sin introducir commits internos en el helper de lectura.
- La API de funnels ya bloquea el borrado del funnel de bienvenida y devuelve mensajes visibles en espanol.
- La reparacion legacy ahora selecciona un candidato exacto de forma determinista si hay mas de uno, evitando crear un tercer funnel de bienvenida.
- El flujo de conversaciones tambien devolvio errores de 404 en espanol para recursos ausentes y validacion de funnel/paso.

### Lista de archivos

- `backend/app/funnels/models.py`
- `backend/app/funnels/schemas.py`
- `backend/app/funnels/service.py`
- `backend/migrations/versions/20260624_0015_welcome_funnel_system_key.py`
- `backend/app/companies/service.py`
- `backend/app/conversations/service.py`
- `backend/app/ai/runtime.py`
- `backend/migrations/versions/20260616_0014_welcome_funnel_fields.py`
- `backend/tests/test_tenant_and_orders.py`
- `frontend/src/App.tsx`
- `_bmad-output/implementation-artifacts/1-5-definir-funnel-de-bienvenida-y-captura-inicial.md`

## Registro de cambios

- 2026-06-16: implementacion completa del funnel de bienvenida, bootstrap idempotente por tenant, integracion con conversaciones/IA, UI de Funnels renovada y pruebas de backend/frontend validadas.
- 2026-06-24: cerrado el riesgo de commit parcial en la creacion de companias al incluir la auditoria dentro de la misma transaccion.
- 2026-06-24: reforzada la invariancia del funnel de bienvenida para que no pueda dejar de ser el default del tenant.
- 2026-06-24: reemplazado el check por nombre visible con el marcador persistente `system_key='welcome'`, con migracion de backfill y bloqueo de default para funnels no bienvenida.
- 2026-06-24: reparados los tenants legacy que habian renombrado y desmarcado el funnel de bienvenida, usando heuristica estructural para evitar la recreacion de un segundo funnel.
- 2026-06-25: endurecido el invariant del funnel de bienvenida para mantenerlo activo y eliminar commits inesperados desde la resolucion del funnel por defecto.
- 2026-06-25: trasladada la persistencia de reparacion legacy al flujo de conversaciones para mantener `get_default_funnel()` side-effect free.
- 2026-06-25: cerrado el gap de borrado, el idioma visible y la duplicacion legacy detectados en review.
- 2026-06-25: traducidos los errores visibles de conversaciones a espanol y limpiada la trazabilidad duplicada del `Lista de archivos`.

### Hallazgos de revisión

- [x] [Review][Patch] Company creation still has a partial-commit path after the bootstrap fix [backend/app/companies/service.py:68] — `create_company_with_owner()` now keeps the company/funnel y owner in one transaction, y the audit write now happens before the single commit so a failure rolls back the full bootstrap.
