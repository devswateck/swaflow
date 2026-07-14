# baseline_commit: 595b380d6111b59e727b01d978cf27ebc2b6a335
# Story 5.3: Configurar reglas de horario y duracion de citas

Status: done

## Story

Como admin principal del tenant,
quiero definir el horario operativo compartido y la duracion por defecto de las citas desde el modulo Citas,
para que la agenda use reglas consistentes en IA y en Citas sin duplicar configuraciones.

## Acceptance Criteria

1. Dado que el admin configura el horario operativo, cuando guarda cambios en Citas, entonces el sistema persiste una sola configuracion compartida para IA y Citas, con zona horaria del tenant, franja de manana 08:00-12:00 y franja de tarde 14:00-18:00 por defecto.
2. Dado que el admin define la duracion por defecto, cuando guarda cambios en Citas, entonces el sistema persiste 1 hora como valor base y permite modificar ese valor sin dejarlo como una constante de frontend.
3. Dado que el sistema calcula disponibilidad o crea una cita, cuando usa reglas de agenda, entonces consume la misma configuracion compartida, respeta que las citas no se ofrezcan el mismo dia y mantiene el horizonte maximo de 7 dias.
4. Dado que el usuario abre el modulo Citas, cuando crea o edita una cita, entonces el formulario usa la duracion configurada como valor inicial y no un numero hardcodeado en la UI.
5. Dado que existe integracion de calendario o falla temporalmente, cuando se recalcula disponibilidad, entonces el comportamiento actual de sincronizacion y fallback sigue intacto y la configuracion de horario/duracion no rompe el flujo comercial.

## Tasks / Subtasks

- [x] Definir y persistir una unica fuente de verdad para horario operativo y duracion de cita. (AC: 1, 2, 3)
  - [x] Extender el contrato compartido usado por IA y Citas para incluir la duracion por defecto de cita y reutilizar el horario semanal existente.
  - [x] Normalizar y validar el nuevo campo en `backend/app/ai/operational.py` y su schema en `backend/app/ai/schemas.py`.
  - [x] Ajustar el servicio de agenda para leer la duracion configurada cuando construye defaults o valida slots.
- [x] Exponer la configuracion en Citas sin crear un segundo calendario de reglas. (AC: 1, 2, 4)
  - [x] Actualizar `frontend/src/App.tsx` para mostrar y editar la configuracion de horario/duracion desde la experiencia de Citas.
  - [x] Prefijar el input de duracion del formulario con el valor persistido y dejar de depender del 60 hardcodeado en la vista.
  - [x] Mantener la lectura de la misma configuracion compartida para IA y Citas; no duplicar la logica de ventanas en el frontend.
- [x] Conservar los guardrails de disponibilidad ya existentes. (AC: 3, 5)
  - [x] Mantener la regla de no ofrecer citas para hoy y el horizonte maximo de 7 dias.
  - [x] Preservar la validacion contra citas internas y calendario externo con fallback honesto si la integracion falla.
  - [x] Revalidar que cambios de duracion o franja invalida no permitan slots inconsistentes.
- [x] Cubrir la regresion con pruebas de backend y frontend. (AC: 1, 2, 3, 4, 5)
  - [x] Agregar pruebas para persistencia de la configuracion compartida y para el valor base de 1 hora.
  - [x] Agregar pruebas de disponibilidad con duracion personalizada y con valor por defecto.
  - [x] Agregar pruebas de horario manana/tarde, exclusion del mismo dia y horizonte de 7 dias.
  - [x] Mantener verdes las pruebas de calendario externo y fallback interno.

## Dev Notes

### Contexto de producto

- Epic 5, historia 5.3.
- FR relevantes: FR151, FR152, FR161, FR162, FR163, FR164, FR165, FR166.
- La regla clave es no duplicar configuracion de horario entre IA y Citas.
- La duracion por defecto debe ser 1 hora, pero el admin debe poder cambiarla desde Citas.

### Estado actual del codigo

- `backend/app/appointments/service.py` tiene `DEFAULT_APPOINTMENT_DURATION_MINUTES = 60` y usa `duration_minutes` directo en disponibilidad, creacion y validacion.
- `backend/app/appointments/schemas.py` expone `duration_minutes` con default 60 en create y availability.
- `backend/app/ai/operational.py` ya normaliza y evalua el horario operativo compartido: timezone, weekday, weekend, fuera/dentro de horario.
- `backend/app/ai/schemas.py` y `frontend/src/App.tsx` modelan ese contrato de horario, pero hoy no incluyen duracion de cita como parte de la configuracion compartida.
- `frontend/src/App.tsx` ya tiene:
  - un editor de horario operativo en la pagina IA,
  - un formulario de Citas que inicializa la duracion con `DEFAULT_APPOINTMENT_DURATION_MINUTES`,
  - una llamada a `/appointments/availability` que usa la duracion del formulario.
- No existe un campo persistido de duracion de cita en `Company`; hoy la duracion sigue siendo una constante de app y una entrada de formulario.

### Guardrails criticos

- No crear una segunda fuente de verdad para horario o duracion.
- No mover el calculo de disponibilidad al frontend.
- No romper la logica actual de `appointment.calendar_synced` / `appointment.calendar_sync_failed`.
- No cambiar el aislamiento por `company_id` ni el comportamiento `404` cross-tenant.
- Si falta una configuracion persistida, la UI debe caer a `60` minutos y a las franjas por defecto, no inventar valores.

### Arquitectura y estructura

- Backend por dominio: `routes.py`, `schemas.py`, `service.py`, `models.py`.
- Si el contrato compartido cambia, actualizar backend y frontend al mismo tiempo.
- Mantener MySQL-compatible cualquier migracion nueva.
- Usar `api<T>()` y el estado existente de React/Zustand; no introducir otro store para agenda.

### File Structure Notes

- Probables archivos a tocar:
  - `backend/app/ai/schemas.py`
  - `backend/app/ai/operational.py`
  - `backend/app/ai/service.py`
  - `backend/app/appointments/service.py`
  - `backend/app/appointments/schemas.py`
  - `backend/app/appointments/routes.py`
  - `frontend/src/App.tsx`
  - `backend/tests/test_inbox_realtime.py`
  - `backend/tests/test_tenant_and_orders.py`
- Si la implementacion introduce persistencia nueva, agregar migracion Alembic y registrar el modelo o campo en la ruta de carga correspondiente.

### Testing Requirements

- Probar que la duracion por defecto persiste y que el formulario de Citas la usa como valor inicial.
- Probar que la configuracion compartida respeta weekday/weekend y timezone del tenant.
- Probar que disponibilidad y creacion siguen excluyendo el mismo dia y respetan el horizonte de 7 dias.
- Probar que la integracion de calendario sigue funcionando y que el fallback interno no se rompe si la integracion falla.

### References

- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/epics.md - Epic 5, Historia 5.3, FR151-FR166]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md - seccion Citas y narrativa de horario operativo compartido]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md - frontend shell, no duplicar calculos, y uso de la arquitectura compartida]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md - Citas como superficie operativa del tenant]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/service.py - default duration, availability y validacion]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/schemas.py - payloads de citas y disponibilidad]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/ai/operational.py - normalizacion del horario operativo compartido]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/ai/schemas.py - contrato tipado del horario operativo]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx - editor actual de horario IA y formulario actual de Citas]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py - cobertura actual de availability]
- [Source: /Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py - cobertura actual de horario operativo, configuracion y calendarios]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- Se selecciono automaticamente la siguiente historia backlog del sprint actual: `5-3-configurar-reglas-de-horario-y-duracion-de-citas`.
- Se revisaron `sprint-status.yaml`, `epics.md`, `prd.md`, `DESIGN.md`, `EXPERIENCE.md`, la historia 5.2, la configuracion del proyecto y el codigo actual de citas y horario operativo.
- Se confirmo que el horario operativo ya es compartido para IA y agenda, pero la duracion por defecto sigue siendo una constante sin persistencia propia.
- Se confirmo que la UI de IA ya edita el horario operativo, mientras que la pagina de Citas usa una duracion local hardcodeada.

### Completion Notes List

- Se agrego `default_appointment_duration_minutes` al contrato operativo compartido y se normaliza junto al horario semanal.
- Citas ahora lee y guarda la misma configuracion compartida que IA, incluyendo la duracion base y la zona horaria del tenant.
- La pantalla de Citas expone reglas compartidas y usa la duracion persistida como valor inicial del formulario.
- Se agregaron pruebas dirigidas para persistencia de configuracion compartida y uso del valor por defecto al crear citas.
- Se resolvio el hallazgo de revision: la configuracion compartida de agenda ya no depende de que el agente IA este activo.

### File List

- `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/5-3-configurar-reglas-de-horario-y-duracion-de-citas.md`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/sprint-status.yaml`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/ai/schemas.py`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/ai/operational.py`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/schemas.py`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/service.py`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/app/appointments/routes.py`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/frontend/src/App.tsx`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_inbox_realtime.py`
- `/Users/camilosanchez/Documents/Swateck/SwaFlow/backend/tests/test_tenant_and_orders.py`

## Change Log

- 2026-07-12: Se unifico la duracion base de citas en el contrato operativo compartido, se expuso la configuracion desde Citas y se agregaron pruebas de regresion.
- 2026-07-12: Se corrigio el acceso a la configuracion compartida para no depender del flag `active` del agente IA.
