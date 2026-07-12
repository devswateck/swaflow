---
title: "Historia 5.1: Crear citas desde conversaciones o manualmente"
status: done
baseline_commit: ee0b2c7
---

# Historia 5.1: Crear citas desde conversaciones o manualmente

Status: done

## Historia

Como usuario autorizado del tenant,
Quiero crear y persistir citas desde una conversacion o desde el modulo Agenda,
para que pueda registrar un compromiso comercial real con trazabilidad entre cliente, conversacion y calendario.

El contrato de esta historia separa claramente preparar contexto de crear cita persistida: `POST /conversations/{conversation_id}/prepare-appointment` solo arma un borrador, mientras que `POST /appointments` crea el registro real. La historia no debe convertir el borrador en una cita por memoria local ni inventar disponibilidad; eso queda para las historias 5.2 y 5.3.

## Criterios de aceptacion

1. Dado que el usuario abre la Agenda o parte desde una conversacion preparada, cuando confirma la cita, entonces el backend valida tenant, contacto, conversacion opcional, usuario asignado opcional, `scheduled_at`, `duration_minutes`, notas y permisos, y rechaza cualquier referencia cross-tenant o inexistente sin crear registros parciales.
2. Dado que la cita se confirma desde el Inbox o desde el formulario manual de Agenda, cuando el sistema persiste la accion, entonces la cita se crea a traves de `POST /appointments`, queda asociada al contacto y a la conversacion cuando exista, y aparece en la lista de Agenda sin depender de datos locales en memoria.
3. Dado que el backend emite `appointment.created`, cuando el usuario vuelve a la Agenda o al hilo relacionado, entonces la vista refleja el registro persistido y la trazabilidad queda disponible desde los eventos y el historial de negocio.
4. Dado que existe una integracion de calendario valida, cuando se crea la cita, entonces el backend intenta sincronizarla y registra honestamente `synced`, `failed` u `obsolete`; si no hay calendario o la sincronizacion falla, la cita sigue operativa dentro de Swaflow sin bloquear el flujo comercial.
5. Dado que el usuario no tiene permiso o intenta crear una cita sobre recursos de otro tenant, cuando ejecuta la accion, entonces el sistema responde con el status correcto (`404` o `403` segun corresponda) y no deja rastros de una cita parcial ni expone informacion ajena.

**FR cubiertos:** FR015, FR066, FR067, FR068, FR069, FR070, FR071, FR072, FR073, FR074, FR112, FR113, FR118

## Tareas / Subtareas

- [x] Auditar el dominio actual de citas y confirmar que existe una unica ruta de creacion.
  - [x] Revisar `backend/app/appointments/service.py`, `backend/app/appointments/routes.py`, `backend/app/appointments/schemas.py` y el flujo `prepare-appointment` en conversaciones.
  - [x] Confirmar que `prepare_conversation_appointment_intent()` sigue siendo solo un ayudante de contexto, no una persistencia encubierta.
- [x] Conectar la UI de Agenda para persistir citas reales.
  - [x] Reemplazar el uso de `initialAppointments` por lectura desde API.
  - [x] Agregar la accion de guardar cita en la pagina de Agenda usando `POST /appointments`.
  - [x] Mantener un unico formulario o flujo que sirva para el origen manual y para el contexto prellenado desde Inbox.
- [x] Mantener sincronizacion de calendario y visibilidad operacional alineadas con la cita persistida.
  - [x] Reusar los campos de estado de sync ya existentes en backend y exponerlos en la UI sin inventar estados nuevos.
  - [x] Confirmar que `appointment.created` refresca la Agenda y el contexto de conversacion relacionado.
- [x] Agregar cobertura de regresion para creacion e aislamiento.
  - [x] Cubrir creacion manual de cita con contacto valido y sin conversacion.
  - [x] Cubrir creacion desde contexto preparado de Inbox con conversacion vinculada.
  - [x] Cubrir `404` cross-tenant y `403` por permisos faltantes sin persistencia parcial.
  - [x] Cubrir que la falta de integracion de calendario no bloquea la cita interna y que el estado de sync sigue siendo honesto.
  - [x] Cubrir que el borrador no crea ningun registro hasta confirmar la accion.

## Notas de desarrollo

### Contexto de negocio

- Esta historia abre el flujo de la Epic 5: el sistema debe poder registrar una cita comercial real y rastrearla desde el Inbox o desde Agenda.
- El objetivo aqui es persistencia y trazabilidad, no busqueda de disponibilidad ni propuesta de horarios. La seleccion de opciones y reglas de horario viven en las historias 5.2 y 5.3.
- El backend sigue siendo la fuente de verdad para citas, estados y sincronizacion con calendarios externos.
- La integracion de calendario es auxiliar: si falla, la cita interna sigue viva y visible dentro de Swaflow.

### Estado actual del codigo

- `backend/app/appointments/service.py` ya valida contacto, conversacion opcional y usuario asignado opcional, persiste la cita, emite `appointment.created` e intenta sincronizacion con calendario.
- `backend/app/appointments/routes.py` ya expone `GET /appointments`, `POST /appointments`, `GET /appointments/{id}`, `PUT /appointments/{id}` y `POST /appointments/{id}/cancel`.
- `backend/app/appointments/schemas.py` ya define `AppointmentCreate`, `AppointmentUpdate` y `AppointmentRead`.
- `backend/app/conversations/service.py` ya expone `prepare_conversation_appointment_intent()` y `get_conversation_appointment_intent()` como contexto de borrador.
- `backend/app/integrations/calendar.py` ya normaliza proveedores Google y Microsoft y conserva estados honestos de sincronizacion.
- `frontend/src/App.tsx` ya tiene el workspace de Agenda y prepara un borrador de cita desde Inbox, pero aun usa `initialAppointments` en memoria y no persiste la cita desde la UI.
- `backend/tests/test_inbox_realtime.py` y `backend/tests/test_tenant_and_orders.py` ya contienen cobertura de contexto de cita, sincronizacion de calendario y eventos; esta historia debe extenderla, no duplicarla.

### Guardrails criticos

- No crear una segunda maquina de estados para citas.
- No convertir el borrador en cita persistida por estado local del frontend.
- No introducir reglas de disponibilidad, franjas horarias o busqueda de slots en esta historia; eso pertenece a 5.2 y 5.3.
- No bloquear la cita interna por fallo de calendario externo.
- No debilitar el aislamiento multi-tenant: `404` para otros tenants y `403` para permisos ausentes dentro del mismo tenant.

### Guia de implementacion

- El flujo mas seguro es: Inbox prepara contexto, Agenda confirma persistencia, backend es la verdad del registro.
- Si la UI necesita conservar una conversacion seleccionada como origen, debe tratarla solo como prefill y no como cita ya creada.
- Reusar los eventos de backend para refrescar la lista y el detalle; no crear una cache paralela de citas en frontend.
- Si se agrega formulario manual, debe compartir la misma forma de payload que usa la cita creada desde Inbox.

### Archivos sugeridos

- `backend/app/appointments/service.py`
- `backend/app/appointments/routes.py`
- `backend/app/appointments/schemas.py`
- `backend/app/conversations/service.py`
- `backend/app/integrations/calendar.py`
- `frontend/src/App.tsx`
- `backend/tests/test_inbox_realtime.py`
- `backend/tests/test_tenant_and_orders.py`

### Requisitos de prueba

- Probar creacion manual de cita con contacto valido y sin conversacion.
- Probar creacion desde contexto preparado de Inbox con conversacion vinculada.
- Probar que los recursos cross-tenant siguen respondiendo `404` o `403` segun corresponda y no crean citas parciales.
- Probar que `appointment.created` se emite y que la Agenda se refresca sobre el registro persistido.
- Probar que la falta de integracion de calendario no bloquea la cita interna y que el estado de sync es honesto.
- Probar que el borrador no genera persistencia hasta confirmar la accion.

### Notas de estructura del proyecto

- Mantener la logica de dominio en `backend/app/appointments/`.
- No mover la verdad de agenda al frontend.
- La disponibilidad de horarios, la duracion por defecto y la busqueda de opciones operativas se abordan en historias posteriores de la Epic 5.

### Referencias

- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md` - Epic 5, Historia 5.1, FR015, FR066-FR074, FR112-FR113, FR118]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - secciones de Citas, calendario, Inbox y backend source of truth]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - backend como fuente de verdad y shell unificado del frontend]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - agenda comercial y flujo desde Inbox]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/service.py` - persistencia de citas, eventos y sync con calendario]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/routes.py` - contrato HTTP actual de citas]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/schemas.py` - payloads `AppointmentCreate`, `AppointmentUpdate` y `AppointmentRead`]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/conversations/service.py` - contexto de cita preparado desde Inbox]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/integrations/calendar.py` - sincronizacion de calendario y normalizacion de proveedores]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx` - Agenda, borrador de cita y flujo actual de Inbox]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py` - cobertura de contexto de cita y realtime]
- [Source: `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py` - cobertura de calendario y sync de citas]

## Registro del Agente Dev

### Modelo utilizado

GPT-5

### Referencias de depuracion

- 2026-07-11: Se selecciono automaticamente el primer backlog de la Epic 5: `5-1-crear-citas-desde-conversaciones-o-manualmente`.
- 2026-07-11: Se revisaron `sprint-status.yaml`, `epics.md`, el estado actual del modulo de citas, el flujo de contexto preparado desde Inbox y el workspace de Agenda en el frontend.
- 2026-07-11: Se confirmo que `prepare_conversation_appointment_intent()` ya existe como borrador, y que la historia debe enfocarse en persistir la cita real sin duplicar disponibilidad ni reglas de horario.
- 2026-07-11: Se conecto la Agenda al backend real de citas, se protegieron las rutas con permisos del modulo y se agrego refresco por eventos `appointment.*`.
- 2026-07-11: Se agregaron pruebas de regresion para persistencia manual, contexto desde Inbox, aislamiento cross-tenant, permisos y ausencia de integracion de calendario.
- 2026-07-11: Se corrigio el flujo para conservar el contacto preparado desde Inbox aunque quede fuera de la pagina inicial de contactos.
- 2026-07-11: Se ajusto la Agenda para mantener visible la cita recien creada aunque el listado paginado no la devuelva en la primera consulta.
- 2026-07-11: Se corrigio la visibilidad de la cita nueva con una referencia temporal de agenda y se mantuvo el orden cronologico por fecha de cita en el backend.
- 2026-07-11: Se reemplazo la referencia temporal por una consulta enfocada de agenda para incluir la cita recien creada sin depender de memoria local.

### Lista de notas de cierre

- La Agenda ahora lee citas desde `GET /appointments` y crea registros reales con `POST /appointments`.
- El flujo manual y el contexto desde Inbox comparten el mismo formulario de persistencia, sin convertir el borrador en cita por estado local.
- La ruta de citas queda protegida por permisos del modulo, y la UI refresca la lista y el hilo relacionado cuando entra `appointment.created`.
- El formulario de Agenda conserva el contacto del borrador de Inbox aunque no aparezca en la pagina inicial de contactos.
- La lista de Agenda puede solicitar una cita enfocada para incluir un alta reciente fuera de pagina sin alterar el orden cronologico.

## File List

- `backend/app/appointments/routes.py`
- `backend/app/appointments/service.py`
- `backend/tests/test_inbox_realtime.py`
- `frontend/src/App.tsx`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/5-1-crear-citas-desde-conversaciones-o-manualmente.md`

## Change Log

- 2026-07-11: Agenda conectada a la API real de citas, con formulario unico para borrador manual e Inbox y refresco por eventos de backend.
- 2026-07-11: Agregada regresion para creacion manual, contexto vinculado, permisos, aislamiento tenant y ausencia de integracion de calendario.
- 2026-07-11: Corregidos los dos hallazgos de review sobre contactos fuera de pagina inicial y ocultamiento de citas recien creadas por paginacion.
- 2026-07-11: Eliminada la dependencia permanente del estado local para la cita recien creada, manteniendo el orden cronologico por fecha de cita y usando una consulta enfocada para el refresco inmediato.
