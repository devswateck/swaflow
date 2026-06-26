---
title: "Historia 1.6: Configurar IA comercial base"
status: done
baseline_commit: 533ce87609109706230237ebe5629fd34c324fa9
---

# Historia 1.6: Configurar IA comercial base

Status: done

## Historia

Como admin principal del tenant,
Quiero configurar la identidad, el contexto y el prompt base del agente,
para que la IA responda con una base comercial coherente con mi negocio.

## Criterios de aceptación

1. Dado que el admin abre la configuracion de IA, cuando define identidad, objetivo comercial, contexto del negocio, prompt, tono y guia conversacional, entonces el sistema guarda esa configuracion por tenant y la IA puede usarla como base antes de responder.
2. Dado que el admin configura la base del agente comercial, cuando guarda la configuracion, entonces el sistema conserva esa configuracion por tenant y la IA puede usarla como base antes de responder.
3. Dado que el sistema necesita preparar menus y respuestas iniciales, cuando la IA se configura para ventas, consultas o citas, entonces el sistema puede usar plantillas interactivas, campos de captura y contexto comercial.
4. Dado que la IA responde a un cliente, entonces no inventa precios, stock, disponibilidad, enlaces de pago, politicas comerciales ni citas.

**FR cubiertos:** FR088, FR089, FR090, FR091, FR093, FR103, FR104, FR109

## Tareas / Subtareas

- [x] Mantener `AiAgent` como el unico registro canonico de configuracion de IA por tenant.
  - [x] Preservar la persistencia de `name`, `system_prompt`, `conversation_objective`, `conversation_guide`, `security_rules`, `tone`, `rules` y `active` sin introducir una tabla paralela de settings.
  - [x] Reutilizar el JSON `rules` para los campos de contexto comercial que pertenecen a la configuracion base de la IA.
- [x] Alinear la superficie de configuracion de IA con el PRD y el flujo actual del tenant.
  - [x] Mantener el modulo de IA como su propia superficie bajo `/ai`; no moverlo a una pagina generica de Settings.
  - [x] Mantener las FAQs y las plantillas interactivas en el mismo workspace de IA para que el admin configure la base comercial en un solo lugar.
  - [x] Reutilizar `DEFAULT_SYSTEM_PROMPT` solo como linea base de respaldo, no como una segunda fuente de verdad.
  - [x] Dejar `FR102` de borrador/publicacion/versionado para la historia 1.7 para que esta historia se mantenga enfocada en la configuracion de base comercial.
- [x] Asegurar que la ensambladura del prompt en runtime consuma el contexto base configurado.
  - [x] Incluir `system_prompt`, `tone`, `conversation_objective`, `conversation_guide`, `security_rules`, contexto de FAQ, contexto de funnel y plantillas interactivas en el prompt de runtime.
  - [x] Mantener explicitos los guardrails de no invencion en el runtime para que el agente no fabrique hechos comerciales.
- [x] Cubrir con pruebas el comportamiento acotado por tenant.
  - [x] Probar la creacion y actualizacion del registro canonico del agente y la ruta de lectura por tenant.
  - [x] Probar que el prompt de runtime incluye el contexto base configurado, el contexto de FAQ y el contexto de plantillas interactivas.
  - [x] Probar que el acceso cross-tenant responde `404` en vez de filtrar la configuracion de IA de otro tenant.

## Notas de desarrollo

### Contexto de negocio

- Esta story cubre la base comercial de la IA, no las reglas operativas avanzadas.
- El PRD pide que el admin configure identidad, objetivo, contexto, prompt, tono, guia conversacional, FAQs, templates y el contexto que la IA necesita antes de responder.
- La IA debe responder con una base comercial coherente con el tenant y respetar la fuente de verdad del backend.
- La story 1.7 es la que debe profundizar en seguridad operativa, horarios, autonomia, escalation y versionado; no mezclar ese alcance aqui.

### Reglas criticas a preservar

- Mantener aislamiento multi-tenant por `company_id` en lectura y escritura.
- No crear un modulo generico de settings para resolver esto.
- No duplicar el prompt base en otra tabla o archivo si ya existe el contrato de `AiAgent`.
- No romper el shell global, `swaflow_theme` ni `swaflow_active_page`.
- No inventar precios, stock, disponibilidad, links de pago, politicas ni agenda.
- Mantener copy visible en espanol y estados honestos cuando falte configuracion.

### Estado actual del codigo

- `backend/app/ai/models.py` ya define `AiAgent`, `AiFaqEntry` y `AiInteractiveTemplate`.
- `backend/app/ai/service.py` ya hace CRUD del agente, FAQs e interactivos y mantiene un unico agente canonico por tenant.
- `backend/app/ai/routes.py` ya expone los endpoints `/ai/agents`, `/ai/faqs` y `/ai/plantillas interactivass`.
- `backend/app/ai/runtime.py` ya compone el prompt de salida con `system_prompt`, `tone`, `conversation_objective`, `conversation_guide`, `security_rules`, `rules_json`, FAQ, funnel y templates interactivos.
- `backend/app/ai/prompts.py` ya contiene un `DEFAULT_SYSTEM_PROMPT` que puede servir como fallback, pero no debe competir con la configuracion del tenant.
- `frontend/src/App.tsx` ya tiene la superficie `AiPage` con formulario, checklist, FAQ upload y biblioteca de interactivos.
- `backend/tests/test_tenant_and_orders.py` ya cubre parte del contexto de runtime y del funnel de bienvenida; la story debe ampliar la cobertura si toca la configuracion de IA base.

### Que debe cerrar esta story

- La configuracion base de la IA debe quedar persistida y visible por tenant de forma consistente.
- La IA debe usar esa configuracion como contexto base antes de responder.
- El admin debe poder configurar en un solo lugar la identidad, el objetivo comercial, el contexto del negocio, el prompt, el tono y el guion.
- FAQs e interactivos deben seguir siendo parte del mismo flujo de configuracion de IA.

### Inference explicita para la solucion

- El sistema ya tiene la mayoria de la superficie de IA; el riesgo principal no es crear CRUD nuevo sino mantener una unica fuente de verdad para el agente comercial.
- Si aparece una decision entre reutilizar `rules` JSON o crear una tabla nueva, la opcion correcta es reutilizar el contrato existente.
- El prompt base del tenant debe seguir siendo tenant-scoped y reutilizable por runtime; no debe quedar embebido en frontend o en un helper paralelo.
- La separacion de responsabilidades debe quedar asi: 1.6 para base comercial de la IA, 1.7 para seguridad, horarios, autonomia y escalamiento.

### Arquitectura y salvaguardas

- Seguir el patron de backend por dominio: `backend/app/ai/`, `backend/tests/`, `frontend/src/App.tsx`.
- No introducir un router nuevo ni un modulo generico de configuracion solo para IA.
- La UI debe seguir consumiendo `api<T>()` y el estado de auth existente.
- Mantener la regla de `404` para recursos de otro tenant y no ocultar problemas reales de configuracion.

### File Structure Notes

- Backend candidato a tocar:
  - `backend/app/ai/models.py`
  - `backend/app/ai/schemas.py`
  - `backend/app/ai/service.py`
  - `backend/app/ai/routes.py`
  - `backend/app/ai/runtime.py`
  - `backend/app/ai/prompts.py`
  - `backend/tests/test_tenant_and_orders.py`
- Frontend candidato a tocar:
  - `frontend/src/App.tsx`
- No tocar dominios ajenos si el cambio cabe en los archivos anteriores.

### Testing requirements

- Cubrir que un tenant nuevo o existente termina con un agente canonico editable y legible.
- Cubrir que save/load de la configuracion base conserva `system_prompt`, `tone`, `conversation_objective`, `conversation_guide` y el contexto de negocio.
- Cubrir que el runtime toma la configuracion base, FAQs y templates cuando arma el prompt.
- Cubrir `404` cross-tenant para lectura y escritura de IA.
- Mantener compatibilidad con la suite actual y con SQLite en memoria.

### Previous story intelligence

- La story 1.5 dejo claro que Funnels debe seguir siendo su propia superficie, no una seccion escondida dentro de Settings; esta story debe respetar la misma disciplina para IA.
- La story 1.5 ya establecio el contrato entre funnel y runtime; esta story debe reutilizar ese contexto en lugar de inventar una segunda capa de prompts.
- El proyecto ya usa mensajes en espanol, `api<T>()` y un shell operacional estable; esta story debe extender ese patron, no improvisar otro.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Historia 1.6, cobertura FR FR088-FR091, FR093, FR102-FR104, FR109]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - modulo IA V1, configuracion base, FAQs, menus/listas y no-invencion]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - App Shell, Page Modules, Frontend Layers]
- [Source: `backend/app/ai/models.py`]
- [Source: `backend/app/ai/schemas.py`]
- [Source: `backend/app/ai/service.py`]
- [Source: `backend/app/ai/routes.py`]
- [Source: `backend/app/ai/runtime.py`]
- [Source: `backend/app/ai/prompts.py`]
- [Source: `frontend/src/App.tsx` - `AiPage`, form state y config save flow]
- [Source: `backend/tests/test_tenant_and_orders.py` - AI runtime coverage y funnel context]
- [Source: `_bmad-output/implementation-artifacts/1-5-definir-funnel-de-bienvenida-y-captura-inicial.md` - precedente de no mover superficies propias a Settings]

## Dev Agent Record

### Agent Model Used

GPT-5

### Referencias de depuración

- 2026-06-25: Se valido la superficie existente del modulo de IA frente a los requisitos de la historia y se confirmo que `/ai` sigue siendo un workspace dedicado con CRUD acotado por tenant y ensamblado del prompt de runtime.
- 2026-06-25: Se agregaron pruebas de regresion del backend que cubren la persistencia canonica del agente, el acceso `404` acotado por tenant y la composicion del prompt de runtime con agente, FAQ y contexto de plantillas interactivas.
- 2026-06-25: Se ejecuto `./backend/.venv/bin/pytest -q backend/tests` y se confirmaron `78 passed`.
- 2026-06-25: Se ejecuto `./node_modules/.bin/eslint src/App.tsx` y `npm run build` en `frontend/`; ambos terminaron con exito.
- 2026-06-25: Se agrego una restriccion de unicidad por tenant para `AiAgent`, un endpoint del backend para el prompt base por defecto y el consumo desde frontend de esa linea base para eliminar la segunda fuente de prompt.
- 2026-06-25: Se agrego cobertura de regresion para la restriccion singleton y el contrato del prompt del backend; se volvio a ejecutar la validacion del backend y frontend con exito (`80 passed`, lint OK, build OK).
- 2026-06-25: Se cerraron los hallazgos de seguimiento de revision protegiendo `/ai/prompts/default-system-prompt` con acceso por modulo y eliminando la ruta visible de error en frontend cuando falla la lectura del prompt por defecto.
- 2026-06-25: Se cerraron los hallazgos del segundo seguimiento de revision haciendo que la pagina de IA cargue el prompt base y los agentes en un unico flujo de inicializacion, conservando un prompt de respaldo operacional y deshabilitando la edicion mientras dura la carga inicial.

### Lista de notas de cierre

- Verificado que el comportamiento canonico de `AiAgent` se preserva por tenant y que los creates/upserts repetidos no introducen filas paralelas de configuracion.
- Verificado que el aislamiento por tenant en lecturas y actualizaciones de IA responde `404` para otro tenant.
- Verificado que la composicion del prompt de runtime incluye la base configurada del agente, el contexto de FAQ y el contexto de plantillas interactivas, ademas de los guardrails explicitos de no invencion.
- La implementacion se mantuvo dentro del modulo de IA existente y no introdujo una superficie generica de settings.
- Aclarado que el versionado/publicacion de `FR102` se difiere de forma intencional a la historia 1.7 y no forma parte del alcance de la base comercial de la 1.6.
- Resueltos los hallazgos de revision endureciendo el registro singleton a nivel de base de datos, exponiendo el prompt por defecto del backend como fuente base del frontend y ampliando la cobertura del contrato de no invencion.
- Resueltos los hallazgos de seguimiento al exigir acceso de modulo para la ruta del prompt por defecto y hacer que la lectura de la linea base del frontend no bloquee sin un fallback codificado duplicado.
- Resueltos los hallazgos del segundo seguimiento al eliminar la carrera entre la carga de prompt y agente, conservar un prompt de respaldo seguro para crear nuevos agentes y bloquear ediciones hasta que termine la carga inicial de datos.

### Lista de archivos

- `_bmad-output/implementation-artifacts/1-6-configurar-ia-comercial-base.md`
- `backend/app/ai/models.py`
- `backend/app/ai/routes.py`
- `backend/app/ai/schemas.py`
- `backend/app/ai/service.py`
- `backend/tests/test_tenant_and_orders.py`
- `backend/tests/test_user_permissions.py`
- `backend/migrations/versions/20260625_0016_ai_agent_singleton_per_tenant.py`
- `frontend/src/App.tsx`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Registro de cambios

- 2026-06-25: Marcada Historia 1.6 lista para revision, registrado el baseline commit y agregadas pruebas de regresion para la persistencia canonica del agente, el acceso `404` acotado por tenant y la composicion del prompt de runtime con FAQ y contexto de plantillas interactivas.
- 2026-06-25: Resueltos los hallazgos de revision: 3 elementos (restriccion singleton, contrato base del prompt del backend, ampliacion de guardrails de no invencion).
- 2026-06-25: Resueltos los hallazgos de seguimiento: 2 elementos (endpoint del prompt por defecto protegido, eliminada la ruta visible de fallback/error en frontend para la lectura del prompt).
- 2026-06-25: Resueltos los hallazgos del segundo seguimiento: 2 elementos (eliminada la carrera de carga del prompt, conservado el prompt de respaldo para la creacion de nuevos agentes y bloqueadas las ediciones durante la carga inicial).
- 2026-06-25: Aclarado que el versionado/publicacion de `FR102` pertenece a la historia 1.7 y no forma parte del alcance de la base comercial de la 1.6.
