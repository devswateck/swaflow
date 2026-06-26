---
title: "Historia 1.7: Configurar seguridad y comportamiento operativo de la IA"
status: done
baseline_commit: 533ce87609109706230237ebe5629fd34c324fa9
---

# Historia 1.7: Configurar seguridad y comportamiento operativo de la IA

Status: done

## Historia

Como admin principal del tenant,
Quiero definir las reglas de seguridad y ejecucion del agente,
para que la IA opere con limites claros en horario, autonomia y escalamiento.

## Criterios de aceptación

1. Dado que el admin abre la configuracion de seguridad del agente, cuando define reglas de seguridad, autonomia, politicas comerciales y escalamiento, entonces el sistema conserva esas reglas separadas del prompt general y el runtime las usa como guardrails aplicados, no solo como texto visible en la interfaz.
2. Dado que el tenant necesita horario de atencion, cuando el admin define horario para lunes a viernes y otro para sabado y domingo, entonces el sistema aplica el comportamiento dentro y fuera de horario segun el dia y la hora local del tenant.
3. Dado que el admin usa modo de prueba o versionado, cuando guarda la IA como borrador o publica una version activa, entonces el sistema distingue entre configuracion editable y configuracion publicada y puede simular conversaciones antes de activar cambios en produccion.
4. Dado que la IA enfrenta baja confianza, datos insuficientes o una situacion de escalamiento, cuando aplica las reglas configuradas, entonces debe pedir aclaracion o derivar a una persona humana en lugar de ejecutar una accion critica fuera de las reglas de autonomia configuradas.
5. Dado que un usuario privilegiado intenta desactivar guardrails obligatorios, cuando la solicitud llega a la validacion del backend, entonces el sistema rechaza cualquier configuracion que debilite las protecciones de tenant, pagos, inventario, seguridad o no invencion.

**FR cubiertos:** FR092, FR094, FR095, FR096, FR097, FR098, FR099, FR100, FR101, FR105, FR106, FR107, FR108

## Tareas / Subtareas

- [x] Extender el contrato de configuracion de IA para que los ajustes operativos tengan una forma de primer nivel y no vivan solo como texto libre del prompt.
  - [x] Mantener el registro existente `AiAgent` acotado por tenant como punto canonico de entrada de la configuracion.
  - [x] Representar reglas de seguridad, ventanas de horario, matriz de autonomia, reglas de escalamiento, politicas comerciales, categorias prioritarias/restringidas y metadatos de modo prueba en una carga estructurada.
  - [x] Preservar compatibilidad hacia atras con la carga JSON `rules` usada por el workspace de IA.
- [x] Introducir un manejo explicito del ciclo de vida borrador/publicado para la configuracion de IA.
  - [x] Mantener una unica fuente de verdad en runtime para las respuestas en vivo.
  - [x] Separar los datos editables del borrador de los datos publicados para que la vista previa o simulacion no modifique la configuracion viva.
  - [x] Asegurar que solo exista una configuracion publicada activa por tenant a la vez.
- [x] Hacer cumplir los guardrails operativos en el codigo de runtime del backend, no solo en el texto del prompt.
  - [x] Usar la hora local del tenant desde `Company.timezone` al evaluar horarios de dia habil y fin de semana.
  - [x] Aplicar de forma consistente el comportamiento fuera de horario antes de que el modelo ejecute acciones criticas.
  - [x] Bloquear cualquier intento de desactivar guardrails obligatorios en los payloads de administracion.
  - [x] Escalar o pedir aclaracion cuando baja confianza o datos faltantes hagan insegura una accion critica.
- [x] Actualizar la UI del workspace de IA para exponer los nuevos controles operativos.
  - [x] Mantener el workspace `/ai` como la superficie dedicada para configuracion de IA.
  - [x] Agregar secciones claras para seguridad, horario, autonomia, escalamiento, politicas y controles de prueba/publicacion.
  - [x] Preservar los campos existentes de configuracion base de IA y el flujo de plantillas interactivas de la historia 1.6.
- [x] Agregar cobertura regresiva para el ciclo de vida, los guardrails y el comportamiento de horario.
  - [x] Probar que las lecturas y escrituras acotadas por tenant siguen respondiendo `404` para otros tenants.
  - [x] Probar el comportamiento de borrador vs publicada y la ruta de simulacion.
  - [x] Probar el manejo de dias habil/fin de semana y dentro/fuera de horario usando la zona horaria del tenant.
  - [x] Probar el rechazo de guardrails cuando un payload intenta desactivar protecciones obligatorias.
  - [x] Probar el comportamiento de escalamiento/aclaracion ante baja confianza o datos insuficientes.

## Notas de desarrollo

### Contexto de negocio

- Historia 1.6 dejo cerrada la base comercial del agente. Esta story agrega el control operativo que pone limites reales a esa base.
- El objetivo no es reinventar la configuracion de IA, sino convertir el AI workspace en un panel seguro de ejecucion comercial.
- El backend sigue siendo la fuente de verdad. El frontend solo captura intenciones de configuracion y no decide reglas criticas por su cuenta.
- La historia debe proteger el flujo comercial de acciones indebidas: no confirmar pagos, no inventar disponibilidad, no saltarse reglas de horario y no ejecutar acciones criticas cuando falten datos.

### Reglas criticas a preservar

- Mantener aislamiento multi-tenant por `company_id` en lectura y escritura.
- Mantener el workspace `/ai` como superficie dedicada; no mover esto a un modulo generico de settings.
- No introducir un router nuevo ni una arquitectura paralela solo para IA.
- No romper la configuracion comercial ya existente de story 1.6, incluyendo FAQs e interactivos.
- No convertir el prompt general en la unica defensa de seguridad; las reglas deben existir en backend y en la configuracion persistida.
- No permitir que un tenant edite reglas para desactivar guardrails obligatorios sobre tenant, pagos, inventario, seguridad o no-invencion.
- No inventar datos para modo de prueba; la simulacion debe ser honesta sobre lo que sabe y lo que no sabe.

### Estado actual del codigo

- `backend/app/ai/models.py` ya define `AiAgent` como configuracion canonica por tenant, con `name`, `system_prompt`, `conversation_objective`, `conversation_guide`, `security_rules`, `tone`, `rules` y `active`.
- `AiAgent` ya tiene unicidad por `company_id`, asi que el runtime actual asume una unica configuracion activa por tenant.
- `backend/app/ai/runtime.py` ya compone el prompt con `system_prompt`, `tone`, `conversation_objective`, `conversation_guide`, `security_rules`, `rules_json`, FAQ, funnel y templates interactivos.
- El runtime actual ya respeta algunos guardrails como no inventar precios/stock y puede desactivar auto-reply via `rules.auto_reply_enabled`, pero no modela de forma explicita el comportamiento dentro/fuera de horario, el versionado o la simulacion.
- `backend/app/ai/routes.py` expone el espacio `/ai` con `require_module_access("ai")`, pero no existe un flujo separado para publicar, previsualizar o versionar la configuracion.
- `frontend/src/App.tsx` ya tiene la pagina de IA con campos para `securityRules`, `schedule`, `model`, `temperature`, `welcomeMessage`, `conversationObjective`, `conversationGuide`, `captureFields`, `handoffRule` y otros valores de `rules`, pero todavia no tiene un estado claro de borrador/publicado ni controles operativos especializados.
- `backend/tests/test_tenant_and_orders.py` ya cubre varios caminos del runtime de IA, el funnel de bienvenida y el contrato de no-invencion; esta story debe ampliar esa cobertura con reglas operativas y lifecycle.

### Inference explicita para la solucion

- La forma mas segura de cerrar esta story es mantener un unico punto canonico para lectura runtime y separar claramente la configuracion editable del estado publicado.
- El contrato puede seguir usando `rules` JSON para granularidad operativa, pero versionado, estado de publicacion y metadata de simulacion no deben quedar difusos dentro de texto libre.
- Si se introduce una tabla o modelo adicional para revisiones/versiones, el runtime no debe leer mezcla de borrador y publicada; solo debe leer la version publicada o una vista explicitamente dedicada a simulacion.
- `Company.timezone` debe usarse para evaluar horario local del tenant, porque el negocio ya tiene ese dato en el modelo de empresa.
- Las reglas de escalamiento y autonomia deben traducirse a comportamiento verificable, no solo a copy descriptivo.

### Arquitectura y salvaguardas

- Seguir el patron de backend por dominio: `backend/app/ai/`, `backend/tests/`, `frontend/src/App.tsx`.
- Mantener backend sincronico con `Session` y `company_id` explicito.
- Respetar la regla de `404` cuando el recurso exista en otro tenant.
- Si la UI necesita versionado o simulacion, reutilizar `api<T>()` y el store de auth existente; no duplicar el manejo de tokens.
- Si se agregan modelos o migraciones, mantener compatibilidad con MySQL y con el esquema de SQLAlchemy 2 usado por el proyecto.
- Cualquier cambio de comportamiento critico debe quedar cubierto por pruebas de servicio y no solo por snapshots del frontend.

### File Structure Notes

- Backend candidato a tocar:
  - `backend/app/ai/models.py`
  - `backend/app/ai/schemas.py`
  - `backend/app/ai/service.py`
  - `backend/app/ai/routes.py`
  - `backend/app/ai/runtime.py`
  - `backend/app/ai/operational.py`
  - `backend/app/ai/prompts.py`
  - `backend/app/models.py` si se agrega un modelo nuevo al descubrimiento global
  - `backend/migrations/versions/*` para cualquier cambio de schema
- Frontend candidato a tocar:
  - `frontend/src/App.tsx`
- Tests candidatos:
  - `backend/tests/test_tenant_and_orders.py` para ampliar el runtime existente
  - un archivo nuevo de pruebas si el volumen de casos operativos hace mas limpio aislar el dominio

### Testing requirements

- Cubrir que un tenant pueda guardar, editar y publicar configuracion operativa sin romper la base comercial ya existente.
- Cubrir que la lectura y escritura siguen siendo tenant-scoped y que un tenant ajeno recibe `404`.
- Cubrir que las reglas obligatorias no se puedan desactivar desde payloads del admin.
- Cubrir que el horario usa la timezone del tenant y distingue lunes-viernes de sabado-domingo.
- Cubrir que fuera de horario el runtime cambie de comportamiento segun la configuracion, sin ejecutar acciones criticas no permitidas.
- Cubrir que la simulacion usa la configuracion de borrador o una vista de preview y no altera la publicacion activa.
- Cubrir que baja confianza, falta de datos o situaciones de riesgo fuerzan aclaracion o handoff.
- Cubrir que la UI conserva los campos de story 1.6 y agrega el nuevo bloque operativo sin perder el flujo de FAQs e interactivos.

### Previous story intelligence

- Historia 1.6 ya resolvio la base del agente y dejo claro que la configuracion comercial vive en `/ai`, no en un settings generico.
- Historia 1.6 ya establecio que la IA usa FAQ, funnel e interactivos como contexto real, y que no debe inventar datos comerciales.
- Esta story debe extender ese contrato con limites de ejecucion y lifecycle, no reescribir la base comercial ni duplicar la fuente de verdad.
- La historia anterior tambien confirmo que `rules` JSON ya es el canal natural para metadatos de configuracion; usarlo donde tenga sentido, pero no mezclar lifecycle con texto libre.

### Latest technical notes

- El proyecto ya esta fijado a Python `>=3.12`, FastAPI `>=0.115`, SQLAlchemy `>=2.0`, Pydantic `>=2.4`, React `^18.3.1` y Vite `^8.0.13`.
- Usar las APIs actuales del stack ya presentes en el repo: `Session`, `select`, `model_dump`, `Field(pattern=...)`, `response_model` y `Depends`.
- No introducir colas, workers o async processing nuevo para resolver esta story.
- No cambiar la decision activa de MySQL ni introducir SQL que solo funcione en PostgreSQL.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Historia 1.7, FR092-FR101, FR105-FR108]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - IA operativa, horario, autonomia, escalamiento, versionado y guardrails]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - App Shell, Page Modules, Data y State]
- [Source: `_bmad-output/project-context.md` - stack, MySQL, multi-tenancy, guardrails y reglas de implementacion]
- [Source: `backend/app/ai/models.py` - estado actual de `AiAgent` y contractos persistidos]
- [Source: `backend/app/ai/runtime.py` - prompt assembly y guardrails actuales]
- [Source: `backend/app/ai/routes.py` - acceso al modulo AI y superficie actual]
- [Source: `backend/app/ai/operational.py` - contrato operativo, validacion y simulacion]
- [Source: `frontend/src/App.tsx` - formulario actual de IA, `rules` JSON y superficie `/ai`]
- [Source: `_bmad-output/implementation-artifacts/1-6-configurar-ia-comercial-base.md` - contexto previo y decisiones ya cerradas]

## Dev Agent Record

### Agent Model Used

GPT-5

### Referencias de depuración

- 2026-06-25: implemente el contrato operativo estructurado en backend para seguridad, horario, autonomia, escalamiento, politicas, prioridades y test mode.
- 2026-06-25: agregue endpoints de lectura, edicion, publicacion y simulacion para la configuracion operativa del agente.
- 2026-06-25: actualice el runtime para evaluar horario con timezone del tenant, aplicar handoff fuera de horario y bloquear acciones criticas cuando la autonomia no alcanza.
- 2026-06-25: amplie la UI de `/ai` con secciones operativas, estado de borrador/publicado, publicacion y simulacion, manteniendo la configuracion base de story 1.6.
- 2026-06-25: valide el backend con `python3 -m py_compile backend/app/ai/operational.py backend/app/ai/service.py backend/app/ai/routes.py backend/app/ai/runtime.py backend/app/ai/models.py backend/app/ai/schemas.py`, `cd backend && ./.venv/bin/pytest -q tests/test_tenant_and_orders.py` (`65 passed`), y el frontend con `cd frontend && npm run lint` y `cd frontend && npm run build`.
- 2026-06-25: corregi el origen de timezone para el panel de IA para usar `company_timezone` del current user y no un literal fijo, y habilite simulacion con preview del borrador enviado desde la UI.
- 2026-06-25: resolvi el hallazgo de review validando guardrails tambien en la ruta de simulacion preview y agregue cobertura regresiva para ese bypass.

### Lista de notas de cierre

- La configuracion operativa quedo persistida en una forma estructurada y sigue reutilizando `rules` como contrato compatible con la superficie AI existente.
- El runtime ya hace cumplir el comportamiento operativo antes de ejecutar respuestas criticas y usa la timezone del tenant para evaluar horario local.
- La UI del workspace `/ai` expone seguridad, schedule, autonomia, escalamiento, politicas, prioridades, modo de prueba y acciones de publicar/simular.
- El panel de IA toma la timezone del tenant desde el perfil actual y la simulacion usa el borrador local enviado por la UI, no solo el estado persistido.
- La cobertura de backend valida el roundtrip de la configuracion, la publicacion, el rechazo de guardrails obligatorios, el handoff fuera de horario y la simulacion con salida de aclaracion.
- La validacion automatizada termino limpia: `66 passed` en backend, `npm run lint` OK y `npm run build` OK en frontend.
- El hallazgo de review quedo resuelto y marcado como completado en el story file.

### Lista de archivos

- `backend/app/ai/models.py`
- `backend/app/ai/operational.py`
- `backend/app/auth/schemas.py`
- `backend/app/auth/service.py`
- `backend/app/ai/routes.py`
- `backend/app/ai/runtime.py`
- `backend/app/ai/schemas.py`
- `backend/app/ai/service.py`
- `backend/tests/test_tenant_and_orders.py`
- `frontend/src/App.tsx`
- `_bmad-output/implementation-artifacts/1-7-configurar-seguridad-y-comportamiento-operativo-de-la-ia.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Registro de cambios

- 2026-06-25: completada la implementacion de la seguridad y el comportamiento operativo de la IA, con contrato estructurado, lifecycle draft/publish, runtime enforceable y UI de control operativo.
- 2026-06-25: actualizada la historia a `review` con baseline commit, tareas cerradas y evidencia de validacion automatizada sin hallazgos bloqueantes.
- 2026-06-25: corregidos los dos hallazgos detectados en review: timezone del tenant consumida desde el current user y simulacion operativa con preview del borrador local.
- 2026-06-25: review adicional detecto un hallazgo pendiente: la ruta de simulacion operativa aun no valida guardrails obligatorios cuando recibe un borrador preview.

### Hallazgos de revisión

- [x] [Review][Patch] Operational simulation bypasses guardrail validation [backend/app/ai/service.py:624] — `simulate_operational_config()` accepts a preview payload y calls `simulation_summary()` without `validate_operational_config()`, so a privileged user can simulate an invalid configuration that would otherwise be rejected by create/update/publish paths.
