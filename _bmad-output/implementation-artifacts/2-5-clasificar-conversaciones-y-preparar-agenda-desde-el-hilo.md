---
baseline_commit: ee0b2c761a0873ae7b8b682ce757a43546222c48
---

# Story 2.5: Clasificar conversaciones y preparar agenda desde el hilo

Status: Done

## Story

Como usuario autorizado del tenant,
Quiero clasificar conversaciones con funnel y dejar lista la intención de agenda,
Para que pueda avanzar la oportunidad comercial sin salir del Inbox.

## Acceptance Criteria

1. Dado que la IA infiere un funnel y una etapa para la conversacion, cuando el usuario abre el hilo, entonces el sistema muestra el funnel y la etapa actuales, y esa clasificacion queda disponible para filtros y metricas.
2. Dado que el usuario autorizado quiere ajustar la clasificacion, cuando cambia manualmente el funnel o la etapa, entonces el sistema guarda el nuevo valor y mantiene el historial de la conversacion asociado a ese cambio.
3. Dado que el cliente expresa intencion de cita, cuando el usuario registra esa intencion desde el Inbox, entonces el sistema conserva el contexto de la conversacion para que la agenda se complete en el modulo de Citas, y refleja la accion en el historial de la conversacion.
4. Dado que el usuario quiere seguir el contexto comercial, cuando la conversacion avanza con mensajes nuevos, entonces el Inbox conserva el contexto suficiente para que la IA o el humano retomen el hilo, y la informacion permanece aislada al tenant correspondiente.
5. Dado que la clasificacion se modifica desde el hilo, cuando el backend responde, entonces el Inbox actualiza en realtime o refresh equivalente el funnel, la etapa y la etiqueta visible sin perder la seleccion del chat.
6. Dado que el usuario no tiene permiso o pertenece a otro tenant, cuando intenta cambiar la clasificacion o marcar la intencion de agenda, entonces el backend rechaza la accion con el error correcto y la UI no inventa cambios locales.

## Tasks / Subtasks

- [x] Auditar y reutilizar el flujo real de clasificacion ya existente.
  - [x] Revisar `backend/app/conversations/service.py`, `backend/app/conversations/routes.py`, `backend/app/conversations/schemas.py`, `backend/app/events/service.py`, `frontend/src/App.tsx`, `backend/tests/test_inbox_realtime.py` y `backend/tests/test_tenant_and_orders.py` para no duplicar mutaciones ni romper el Inbox.
  - [x] Confirmar que `assign_conversation_funnel()` siga siendo la mutacion canonica para funnel y etapa, y que siga publicando `conversation.funnel_assigned`, auditoria y realtime.
  - [x] Mantener `funnel_id`, `funnel_step_id` y `current_step` como fuente de verdad visible en la conversacion; no crear un segundo estado paralelo en frontend.

- [x] Completar la experiencia de clasificacion desde Inbox.
  - [x] Mostrar el funnel y la etapa actuales en el rail/contexto del hilo con labels claros en espanol.
  - [x] Permitir ajuste manual del funnel y la etapa desde el mismo hilo, usando la API existente y preservando el hilo seleccionado.
  - [x] Asegurar que el selector de etapa dependa del funnel elegido y que el backend reciba tanto `funnel_step_id` como `current_step` para no perder el codigo de etapa.

- [x] Preparar la intención de agenda sin adelantar la historia de creación de citas.
  - [x] Reemplazar o aislar cualquier mock de agenda local que invente citas de ejemplo; no usar datos falsos como salida operativa.
  - [x] Añadir una accion de Inbox para marcar o transferir la intencion de agenda como contexto comercial, no como cita persistida final.
  - [x] Conservar el contacto, la conversacion y la clasificacion del hilo al saltar al modulo de Citas o a un draft de agenda.
  - [x] Dejar claro en UI y backend que la creacion real de la cita pertenece a la historia 5.1; esta historia solo deja el contexto listo.

- [x] Reforzar filtros, metadatos y feedback visible.
  - [x] Mantener la clasificacion disponible para filtros del Inbox y para las metricas que ya consumen `funnel_name` y `funnel_step_name`.
  - [x] Mostrar feedback de carga/actualizacion al cambiar funnel, etapa o intencion de agenda.
  - [x] No perder la seleccion del hilo ni el draft del composer cuando falle la mutacion.

- [x] Agregar regresion automatizada.
  - [x] Cubrir asignacion de funnel y etapa con `conversation.funnel_assigned` y el refresh del Inbox.
  - [x] Cubrir clearing de funnel si la UI lo soporta, validando que el backend conserve error en espanol y aislamiento por tenant.
  - [x] Cubrir la accion de preparacion de agenda como handoff de contexto, verificando que no cree una cita falsa ni rompa el historial.
  - [x] Cubrir `404` cross-tenant y rechazo por permiso para no filtrar conversaciones ajenas.

## Dev Notes

### Contexto de negocio

- Esta historia cierra la parte de clasificación comercial del Inbox: funnel, etapa e intención de agenda deben quedar visibles y accionables sin salir del hilo.
- No es la historia de crear citas reales. La creación/edición de citas pertenece a la épica 5 y debe seguir siendo backend-driven.
- La intención de agenda aquí debe tratarse como contexto operativo para la siguiente pantalla o flujo, no como una cita inventada.
- El historial de la conversación y la trazabilidad de eventos deben seguir intactos para que IA y humano retomen el hilo con contexto real.

### Estado actual del código

- `backend/app/conversations/service.py` ya implementa `assign_conversation_funnel()` y publica `conversation.funnel_assigned` con auditoria y realtime.
- `backend/app/conversations/routes.py` ya expone `POST /conversations/{conversation_id}/assign-funnel`.
- `backend/app/conversations/schemas.py` ya define `ConversationFunnelAssign` con `funnel_id`, `funnel_step_id` y `current_step`.
- `frontend/src/App.tsx` ya carga funnels, muestra funnel/etapa en el Inbox y llama `assignConversationFunnel()` con `funnel_id`, `funnel_step_id` y `current_step`.
- `frontend/src/App.tsx` ahora tiene un boton `Preparar agenda` que crea un draft temporal de agenda desde Inbox y navega al modulo de Citas sin inventar una cita persistida.
- `backend/app/appointments/service.py` y `backend/app/appointments/routes.py` ya soportan citas reales, pero esa capacidad corresponde a la épica 5.
- `backend/app/events/service.py` ya reconoce `conversation.funnel_assigned` y el nuevo `conversation.appointment_intent_prepared`; el hilo puede leerlo en el timeline.
- `backend/tests/test_inbox_realtime.py` ya cubre eventos de funnel y realtime del Inbox; se agregaron regresiones para el nuevo evento de agenda y el bloqueo por permisos.

### Guardrails criticos

- No duplicar la mutacion de clasificacion: usar `assign_conversation_funnel()` como fuente canonica.
- No crear un router nuevo ni un store paralelo para manejar el estado de funnel o agenda.
- No usar mocks ni valores fijos de fecha/asesor para la agenda operativa.
- No convertir esta historia en creacion completa de cita; eso va en epic 5.
- Mantener el aislamiento por `company_id`; recursos de otro tenant deben seguir respondiendo `404`.
- Mantener los errores visibles en espanol y no inventar cambios locales si el backend rechaza la mutacion.
- No romper el orden por actividad reciente ni la seleccion del hilo en el Inbox.

### Guidance de implementacion

- Reusar el rail/contexto del Inbox para mostrar funnel, etapa y estado de preparacion de agenda.
- Si se requiere una marca de contexto adicional para la agenda, que sea una señal persistida/event-backed y tenant-scoped, no una variable local efimera.
- Si el frontend necesita preseleccionar Citas, debe hacerlo pasando contexto real de la conversacion, no un registro sintetico.
- Mantener el flujo de realtime: cambiar clasificacion debe refrescar la vista sin perder el hilo activo ni el draft del composer.
- Si se agrega evento nuevo para "intencion de agenda preparada", usar un nombre estable y agregarlo al conjunto de eventos de conversacion.

### Pruebas y calidad

- Probar que cambiar funnel o etapa publica evento, persiste y se ve en Inbox y filtros.
- Probar que la accion de agenda conserva el contexto de conversacion y no crea una cita real inventada.
- Probar que el backend sigue devolviendo `404` para conversaciones de otro tenant.
- Probar que usuarios sin permiso no pueden mutar la clasificacion.
- Mantener compatibilidad con SQLite de tests y con la semantica MySQL vigente del proyecto.

### Project Structure Notes

- Dominio principal de clasificacion: `backend/app/conversations/`.
- El flujo de agenda real vive en `backend/app/appointments/`; no moverlo a conversaciones.
- El shell de la experiencia sigue en `frontend/src/App.tsx`; extraer componentes solo si reduce complejidad real.
- Si se introduce un nuevo evento de agenda, tambien debe quedar reflejado en `backend/app/events/service.py` y en los tests de Inbox.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Historia 2.5, FR016, FR017, FR074, FR085, FR086, FR087]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - seccion Inbox, Citas y reglas de agenda, FR015, FR066-FR074, FR147-FR166]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - Inbox como workspace de lista, hilo y rail contextual; patrones de estado y clasificacion]
- [Source: `_bmad-output/project-context.md` - reglas criticas de multi-tenancy, backend como fuente de verdad, `404` cross-tenant y errores en espanol]
- [Source: `backend/app/conversations/service.py`]
- [Source: `backend/app/conversations/routes.py`]
- [Source: `backend/app/conversations/schemas.py`]
- [Source: `backend/app/events/service.py`]
- [Source: `backend/app/appointments/service.py`]
- [Source: `backend/app/appointments/routes.py`]
- [Source: `frontend/src/App.tsx` - Inbox rail, `assignConversationFunnel()`, `prepareAppointmentFromInbox()` y estado de conversacion]
- [Source: `backend/tests/test_inbox_realtime.py`]
- [Source: `backend/tests/test_tenant_and_orders.py`]

## Change Log

- 2026-07-02: se cerraron los ultimos hallazgos de review: el detalle del hilo ignora respuestas obsoletas, la seleccion perdida se limpia al recibir un `404`, y la preparacion de agenda devuelve exactamente el snapshot creado sin rehidratar desde otro evento concurrente.
- 2026-07-02: se corrigieron los hallazgos finales de review: `Nuevo borrador` ahora abre un borrador manual visible, el snapshot de agenda resuelve empates de forma estable y el timestamp del contexto se normaliza para compararlo por instante.
- 2026-07-02: se corrigieron nuevos hallazgos de review: el timestamp del contexto de agenda ahora coincide con el snapshot seleccionado, el handoff evita mutar una conversacion ya cambiada y el draft se limpia cuando el inbox deja de tener una conversacion seleccionable.
- 2026-07-02: se corrigieron los hallazgos de review restantes: la etiqueta de asignacion del draft de agenda ahora se recalcula con los usuarios cargados, la preparacion de agenda no sobrescribe un hilo ya cambiado y la rehidratacion de contexto prefiere el snapshot mas reciente de agenda.
- 2026-07-02: se corrigieron los hallazgos de code review: la seleccion del hilo ya no hereda un detalle obsoleto entre conversaciones y `StatusBadge` deja de clasificar `inactive` como `active`.
- 2026-07-02: implementacion completada para la preparacion de agenda desde Inbox, nuevo evento de conversacion, guardrails de permisos y regresion automatizada.
- 2026-07-02: se corrigio el handoff de agenda para rehidratar el draft desde el backend usando el evento persistido de conversacion y la seleccion de hilo guardada, evitando depender solo de memoria local.
- 2026-07-02: se endurecio la rehidratacion para usar el snapshot del evento de agenda y preservar la seleccion de conversacion aunque el Inbox quede filtrado.

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- `git log --oneline -5 -- frontend/src/App.tsx backend/app/conversations/service.py backend/app/appointments/service.py`
- `backend/app/conversations/service.py`: `assign_conversation_funnel()` ya publica `conversation.funnel_assigned` y persiste clasificacion; se agrego `prepare_conversation_appointment_intent()`.
- `backend/app/conversations/routes.py`: `assign-funnel` ahora exige acceso a `inbox`, se agrego `prepare-appointment` y se expone `GET /conversations/{conversation_id}/appointment-intent` para rehidratar el borrador.
- `frontend/src/App.tsx`: el Inbox ahora dispara `Preparar agenda`, persiste la seleccion del hilo y mantiene un snapshot local del detalle para que Citas pueda rehidratar el draft aunque el inbox quede filtrado.
- `frontend/src/App.tsx`: la seleccion visible del hilo ahora depende del `selectedConversationId` actual para no mostrar un detalle viejo al cambiar de conversacion, y `StatusBadge` evita marcar `inactive` como activo.
- `frontend/src/App.tsx`: la etiqueta de asignacion del borrador de agenda se calcula con el estado actual de usuarios y el disparo de preparacion evita sobrescribir un contexto ya cambiado por otro hilo.
- `backend/app/conversations/service.py`: el contexto de agenda ahora usa un sello `prepared_at` explicito para elegir el snapshot mas reciente de forma determinista.
- `frontend/src/App.tsx`: el borrador de agenda se limpia cuando el inbox deja de tener una conversacion seleccionable y la mutacion de preparacion sale antes de hacer el POST si el hilo ya cambio.
- `backend/app/conversations/service.py`: el timestamp devuelto por `/appointment-intent` coincide con el snapshot elegido.
- `frontend/src/App.tsx`: el boton `Nuevo borrador` crea un borrador manual visible y el efecto de agenda no lo borra al no haber conversacion seleccionada.
- `backend/app/conversations/service.py`: el desempate de snapshot usa `event.id` como ultima llave estable.
- `backend/tests/test_inbox_realtime.py`: se agregaron regresiones para el nuevo evento `conversation.appointment_intent_prepared`, la rehidratacion del contexto, el snapshot inmutable y el bloqueo por permisos.
- `backend/.venv/bin/pytest backend/tests/test_inbox_realtime.py -q`
- `backend/.venv/bin/pytest backend/tests/test_tenant_and_orders.py backend/tests/test_user_permissions.py -q`
- `npm run build`
- `npm run lint`

### Completion Notes List

- Se preservo el flujo canonico de clasificacion por funnel y etapa, y se endurecio el acceso de `assign-funnel` para usuarios con `inbox`.
- Se agrego el evento `conversation.appointment_intent_prepared` y la ruta `POST /conversations/{conversation_id}/prepare-appointment` para dejar listo el contexto de agenda.
- El Inbox ahora ofrece `Preparar agenda` y el modulo de Citas rehidrata un draft contextual desde el backend sin crear una cita persistida falsa.
- Se preserva la seleccion del hilo aun cuando un filtro lo oculte, y el draft se reconstruye desde el snapshot del evento de agenda.
- Se agrego cobertura automatizada para el nuevo evento, la autorizacion por modulo, el snapshot inmutable y la no regresion de permisos/tenant.
- Se corrigio la regresion visual de estados para que `inactive` no se pinte como estado activo.
- Se corrigio el riesgo de contexto de agenda obsoleto al recomputar la etiqueta de asignacion y proteger el handoff frente a cambios de seleccion durante la carga.
- Se hizo determinista la eleccion del contexto de agenda mas reciente para evitar devolver un snapshot anterior cuando dos preparaciones comparten timestamp de persistencia.
- Se alinio el timestamp mostrado por la agenda con el snapshot realmente seleccionado y se limpio el draft cuando el inbox ya no expone una conversacion valida.
- Se habilito un estado de borrador manual para que `Nuevo borrador` no deje la vista vacia.
- Se reforzo la regresion automatizada para cubrir el empate real de timestamps y validar que el contexto devuelto es estable.
- Validacion ejecutada: `backend/tests/test_inbox_realtime.py` 15 passed, `backend/tests/test_tenant_and_orders.py backend/tests/test_user_permissions.py` 101 passed, `npm run build` y `npm run lint` exitosos.

### File List

- `_bmad-output/implementation-artifacts/2-5-clasificar-conversaciones-y-preparar-agenda-desde-el-hilo.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `backend/app/conversations/schemas.py`
- `backend/app/conversations/routes.py`
- `backend/app/conversations/service.py`
- `backend/app/events/service.py`
- `backend/tests/test_inbox_realtime.py`
- `frontend/src/App.tsx`
