---
title: "Historia 5.2: Validar disponibilidad y proponer horarios de agenda"
status: done
baseline_commit: ee0b2c7
---

# Historia 5.2: Validar disponibilidad y proponer horarios de agenda

Status: done

## Historia

Como sistema de agenda del tenant,
Quiero validar disponibilidad real y proponer tres horarios concretos para agendar,
para que la IA y el equipo no inventen slots y el cliente reciba alternativas viables dentro de las reglas del negocio.

Esta historia consume la configuracion ya existente de horario operativo y duracion base, pero no crea una segunda fuente de verdad para disponibilidad. El backend debe calcular las opciones y la UI solo debe mostrarlas y dejarlas listas para continuar con la cita persistida de la historia 5.1.

## Criterios de aceptacion

1. Dado que un cliente solicita una cita, cuando la IA o el usuario inicia el flujo de agenda, entonces el sistema primero pide si prefiere horario de manana o de tarde y no propone slots antes de capturar esa preferencia.
2. Dado que el tenant tiene calendario integrado, cuando el sistema calcula disponibilidad inicial, entonces usa el calendario configurado para validar opciones reales y, si la integracion falla, el flujo comercial sigue operativo sin bloquear la agenda interna.
3. Dado que el tenant no tiene calendario integrado, cuando el sistema calcula disponibilidad, entonces usa las citas internas de Swaflow y el horario operativo compartido del comercio como fuente de verdad, sin requerir una configuracion de horario duplicada para Citas.
4. Dado que se generan opciones de agenda, cuando el sistema arma las propuestas, entonces devuelve tres alternativas con hora, preferiblemente en dias diferentes, dentro de un horizonte maximo de 7 dias a partir del dia siguiente.
5. Dado que el usuario elige una de las opciones propuestas, cuando continua hacia la creacion de la cita, entonces el sistema reutiliza el flujo de persistencia existente de 5.1 sin volver a inventar el horario en el frontend ni perder el contexto de la conversacion.

**FR cubiertos:** FR147, FR148, FR149, FR150, FR151, FR152, FR161, FR162, FR163, FR164, FR165, FR166

## Tareas / Subtareas

- [x] Auditar el origen actual de horario operativo, duracion y citas internas para confirmar una sola fuente de verdad de disponibilidad.
  - [x] Revisar `backend/app/ai/operational.py` para reutilizar las ventanas por defecto y la zona horaria ya normalizada.
  - [x] Revisar `backend/app/appointments/service.py` y `backend/app/appointments/routes.py` para extender el dominio sin romper `GET /appointments` ni `POST /appointments`.
  - [x] Confirmar que la historia 5.1 sigue siendo la unica responsable de persistir la cita definitiva.
- [x] Implementar el calculo de disponibilidad y la generacion de propuestas de agenda.
  - [x] Definir una forma estable de obtener la ventana preferida `manana`/`tarde` y traducirla a rangos reales de horario.
  - [x] Considerar citas internas, duracion efectiva y calendario externo cuando exista.
  - [x] Devolver tres opciones honestas, sin rellenar huecos con horarios inventados.
- [x] Exponer el contrato necesario para que Inbox o Agenda consuman las opciones.
  - [x] Mantener el frontend como consumidor del resultado, no como calculador de slots.
  - [x] Mostrar un mensaje claro cuando no existan opciones dentro del horizonte permitido.
  - [x] Conservar el flujo de la historia 5.1 para confirmar y guardar la cita seleccionada.
- [x] Agregar cobertura de regresion para disponibilidad real y fallback operativo.
  - [x] Cubrir agenda con calendario integrado y validacion contra disponibilidad externa.
  - [x] Cubrir agenda sin calendario integrado usando solo citas internas y horario compartido.
  - [x] Cubrir que no se ofrezcan citas para el mismo dia y que el horizonte maximo sea de 7 dias.
  - [x] Cubrir que el flujo siga funcionando cuando el calendario externo falle.

## Notas de desarrollo

### Contexto de negocio

- Esta historia resuelve la parte de "no inventar disponibilidad" de la Epic 5.
- El objetivo no es crear una nueva pantalla de administracion ni una nueva configuracion de horario; eso queda para 5.3.
- La disponibilidad debe salir de reglas reales: preferencia manana/tarde, horario operativo ya definido, citas internas existentes y, si aplica, calendario externo.
- Si no hay datos suficientes para proponer una agenda confiable, el sistema debe decirlo claramente en vez de fabricar horarios.

### Estado actual del codigo

- `backend/app/appointments/service.py` ya persiste citas, emite eventos y sincroniza con calendario, pero no calcula slots ni propone horarios.
- `backend/app/appointments/routes.py` solo expone la lectura y mutacion basica de citas, sin endpoint de disponibilidad.
- `backend/app/appointments/schemas.py` define la cita, pero no modela todavia una respuesta de propuestas de agenda.
- `backend/app/ai/operational.py` ya normaliza horarios de lunes a viernes y fin de semana, con defaults de 08:00-18:00 y 08:00-14:00, por lo que esa logica debe reutilizarse y no duplicarse.
- `frontend/src/App.tsx` ya tiene el flujo de preparar cita y guardar la cita seleccionada, pero todavia no captura preferencia de horario ni muestra propuestas calculadas por backend.
- `backend/tests/test_inbox_realtime.py` y `backend/tests/test_tenant_and_orders.py` ya cubren persistencia de citas, eventos y sincronizacion; esta historia debe extender esa cobertura hacia disponibilidad y seleccion de slots.

### Guardrails criticos

- No crear una segunda maquina de estado para agenda en el frontend.
- No inventar disponibilidad local con heuristicas de UI.
- No duplicar configuracion de horario entre IA y Citas en V1.
- No bloquear el flujo de agenda por fallo de calendario externo; si falla, se cae a disponibilidad interna con honestidad.
- No romper el flujo de persistencia de 5.1 ni la actualizacion por eventos `appointment.*`.

### Guia de implementacion

- El backend debe ser la fuente de verdad para el calculo de slots.
- El frontend solo debe pedir la preferencia `manana`/`tarde`, mostrar las opciones y enviar la seleccion al flujo de creacion de cita ya existente.
- Si existe calendario externo, usarlo como validacion inicial; si no existe o falla, derivar a citas internas + horario compartido.
- Mantener el horizonte acotado a 7 dias para no abrir una busqueda costosa o confusa.
- Reusar la zona horaria del tenant o la ya normalizada por configuracion operativa.

### Archivos sugeridos

- `backend/app/appointments/service.py`
- `backend/app/appointments/routes.py`
- `backend/app/appointments/schemas.py`
- `frontend/src/App.tsx`
- `backend/tests/test_inbox_realtime.py`
- `backend/tests/test_tenant_and_orders.py`

### Requisitos de prueba

- Probar que el flujo pide preferencia de manana o tarde antes de listar opciones.
- Probar que el calendario integrado se consulta para validar disponibilidad y que un fallo no bloquea la agenda interna.
- Probar que sin calendario integrado la disponibilidad sale de citas internas y horario compartido.
- Probar que solo se devuelven tres opciones, no para el mismo dia, y dentro de un maximo de 7 dias desde el dia siguiente.
- Probar que la seleccion de una opcion sigue usando el flujo de persistencia de 5.1 sin generar una cita por memoria local.

### Notas de estructura del proyecto

- Mantener la logica de disponibilidad dentro del dominio de citas, no en componentes sueltos de UI.
- No introducir una nueva configuracion de horario mientras la historia 5.3 no la haga explicita.
- Reutilizar la experiencia de Inbox/Agenda ya montada en `frontend/src/App.tsx` para presentar las opciones, no para calcularlas.

### Referencias

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Epic 5, Historia 5.2, FR147-FR152, FR161-FR166]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - secciones de Citas, calendario, horario operativo y comportamiento de agenda]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - backend como fuente de verdad y shell unificado del frontend]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - flujo de agenda desde Inbox y reglas de interaccion]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/ai/operational.py` - normalizacion de horario operativo y defaults de ventana]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/service.py` - persistencia actual de citas y sincronizacion con calendario]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/routes.py` - contrato HTTP actual de citas]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/schemas.py` - payloads y respuesta actual de citas]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx` - flujo actual de Agenda, borrador y persistencia]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py` - cobertura de contexto y realtime de citas]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py` - cobertura de calendario, agenda y sincronizacion]

## Registro del Agente Dev

### Modelo utilizado

GPT-5

### Referencias de depuracion

- 2026-07-11: Se selecciono automaticamente la primera historia backlog restante de la Epic 5: `5-2-validar-disponibilidad-y-proponer-horarios-de-agenda`.
- 2026-07-11: Se revisaron `sprint-status.yaml`, `epics.md`, `prd.md`, `EXPERIENCE.md`, `frontend-implementation-brief.md`, la historia 5.1 y el codigo actual de citas, agenda y horario operativo.
- 2026-07-11: Se confirmo que el backend ya persiste citas y normaliza ventanas de horario, pero todavia no calcula slots realistas ni propone alternativas de agenda.
- 2026-07-11: Se establecio que la historia debe reutilizar el flujo de persistencia de 5.1, sin crear una segunda fuente de verdad para horarios.
- 2026-07-11: Se implemento el endpoint `POST /appointments/availability`, el calculo de slots internos y el fallback a calendario externo.
- 2026-07-11: Se valido sintacticamente el backend con `python3 -m py_compile` y el frontend con `npm run build`.
- 2026-07-11: No fue posible ejecutar `pytest` en este entorno porque el binario no esta instalado en el Python disponible.
- 2026-07-11: Se corrigio la conversion de `datetime-local` para usar la zona horaria del tenant y no la del navegador.
- 2026-07-11: Se corrigio el parser de Microsoft Calendar para respetar `timeZone` en `getSchedule`.
- 2026-07-11: Se endurecio la validacion de agenda para revalidar el slot antes de crear o mover una cita.
- 2026-07-11: Se corrigio la paginacion con `focus_appointment_id` para respetar el `limit` y mantener el contrato.
- 2026-07-11: Se hizo que los adaptadores de calendario fallen ante respuestas malformadas y que el default de provider sea compatible con integraciones legacy.
- 2026-07-11: Se validaron nuevamente backend por compilacion y frontend por build despues de los cambios de correccion.
- 2026-07-11: Se limito la revalidacion dura al flujo de creacion para evitar falsos positivos al editar una cita existente.
- 2026-07-11: Se corrigieron los hallazgos de revision restantes: se elimino el `NameError` en la validacion de agenda, se bloqueo la creacion fuera de horario operativo, se serializo la creacion de citas y la UI ya exige seleccionar una opcion propuesta antes de guardar.
- 2026-07-11: Se reforzo el flujo de agenda con estado real de preferencia de horario por evento de conversacion y se volvio a validar la reprogramacion de citas.
- 2026-07-11: Se corrigio la prioridad de auto-respuesta para que `request_human` y `complaint` sigan derivando a humano antes de la preferencia de agenda.

### Lista de notas de cierre

- La historia queda enfocada en disponibilidad real y propuesta de horarios, no en persistencia.
- La historia consume horario operativo y citas internas existentes, con fallback honesto si falla el calendario externo.
- El frontend solo debe presentar opciones y continuar hacia la cita persistida.
- La validacion automatica disponible en el entorno dejo el backend compilando y el frontend generando build.
- La suite de pruebas de Python requiere un entorno con `pytest` instalado para correr los casos agregados.
- Se verifico `python3 -m py_compile` en backend y `npm run build` en frontend; `pytest` no estuvo disponible en el entorno de ejecucion.
- Los dos hallazgos de revision quedaron corregidos: conversion de horario en UI y zona horaria de Microsoft Calendar.
- Los hallazgos adicionales de segunda revision quedaron corregidos: slot revalidado al guardar, respuesta malformada de calendario tratada como error, provider legacy respaldado y paginacion respetada.
- La revalidacion dura del slot se aplica en la creacion para preservar el flujo de agenda sin chocar con la propia cita en actualizaciones.
- La prioridad de handoff se preserva incluso cuando existe una preferencia de agenda pendiente.

## File List

- `backend/app/appointments/routes.py`
- `backend/app/appointments/service.py`
- `backend/app/appointments/schemas.py`
- `backend/app/ai/runtime.py`
- `backend/app/conversations/service.py`
- `backend/app/conversations/schemas.py`
- `backend/app/events/service.py`
- `frontend/src/App.tsx`
- `backend/tests/test_inbox_realtime.py`
- `backend/tests/test_tenant_and_orders.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/5-2-validar-disponibilidad-y-proponer-horarios-de-agenda.md`

## Change Log

- 2026-07-11: Creada la historia 5.2 para validacion de disponibilidad y propuesta de horarios de agenda.
- 2026-07-11: Definido el alcance para reutilizar el horario operativo existente, evitar slots inventados y preservar el flujo de persistencia de 5.1.
- 2026-07-11: Implementado el calculo de disponibilidad con validacion externa opcional, fallback interno y propuesta de tres opciones.
- 2026-07-11: Actualizado el frontend para consumir disponibilidad real y prellenar la cita seleccionada.
- 2026-07-11: Marcada la historia como `review` tras validacion de compilacion y build.
- 2026-07-11: Corregida la interpretacion de zonas horarias en el frontend y en Microsoft Calendar.
- 2026-07-11: Endurecida la validacion de disponibilidad al persistir y corregidos los contratos de calendario y paginacion.
- 2026-07-11: Afinado el alcance de revalidacion al persistir para cubrir el flujo de creacion sin romper ediciones existentes.
- 2026-07-11: Corregidos los hallazgos de review con validacion de horario operativo, serializacion de creacion, seleccion explicita de horario y ajuste del prompt de agenda.
- 2026-07-11: Corregidos los hallazgos restantes con validacion de reprogramacion y estado persistido de preferencia de agenda mediante eventos de conversacion.
- 2026-07-11: Corregido el ultimo hallazgo de review con prioridad de handoff sobre la preferencia de agenda.
- 2026-07-11: Historia cerrada como `done` tras la revision final y la verificacion estatica disponible en el entorno.
