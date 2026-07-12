---
title: "Historia 2.4: Asignar, tomar y reasignar chats por usuario"
status: done
baseline_commit: ee0b2c761a0873ae7b8b682ce757a43546222c48
---

# Historia 2.4: Asignar, tomar y reasignar chats por usuario

Status: done

## Historia

Como admin o usuario autorizado del tenant,
Quiero tomar, asignar y reasignar conversaciones segun reglas operativas,
para que el equipo distribuya la atencion sin duplicar el trabajo ni perder control del responsable humano.

## Criterios de aceptación

1. Dado que existe un chat disponible y el usuario tiene acceso al Inbox, cuando lo toma desde el Inbox, entonces el chat queda asignado a ese usuario, se publica el cambio en realtime, se registra auditoria/evento y no queda disponible para gestion simultanea por otro usuario.
2. Dado que el tenant solo tiene usuario admin activo, cuando se listan los chats, entonces el admin puede gestionarlos todos sin asignacion adicional obligatoria y la UI no exige un responsable extra para operar.
3. Dado que el tenant tiene exactamente un usuario adicional activo, cuando la autoasignacion por defecto esta habilitada, entonces los chats nuevos se asignan a ese usuario por defecto; y cuando el admin la desactiva, los chats nuevos quedan disponibles/no asignados hasta que un usuario los tome o el admin los asigne manualmente.
4. Dado que un chat ya fue tomado o asignado, cuando el admin lo reasigna a otro usuario, entonces el sistema actualiza el responsable, conserva el historial del hilo, publica el cambio en realtime y registra el cambio para auditoria.
5. Dado que el usuario revisa la bandeja, cuando compara chats disponibles, chats asignados a el y chats asignados a otros, entonces el sistema los diferencia claramente y respeta permisos por usuario, modulo y aislamiento por tenant.
6. Dado que un usuario sin permiso o de otro tenant intenta tomar, asignar o reasignar un chat, cuando la accion llega al backend, entonces el sistema la bloquea con el error correcto y no inventa cambios locales en la UI.

**FR cubiertos:** FR019, FR020, FR021, FR022, FR023, FR024, FR025, FR026, FR172, FR173, NFR003, NFR010, NFR011, NFR012, NFR015, NFR018, NFR019, NFR022, NFR027, NFR028, NFR029

## Tareas / Subtareas

- [x] Auditar el flujo real de asignacion para separar responsable humano, permisos y autoasignacion del estado de IA.
  - [x] Revisar `backend/app/conversations/service.py`, `backend/app/conversations/routes.py`, `backend/app/conversations/models.py`, `backend/app/whatsapp/service.py`, `frontend/src/App.tsx` y `backend/app/users/routes.py` para no romper el flujo existente de Inbox.
  - [x] Confirmar que `assigned_user_id` siga siendo la unica fuente de verdad del responsable humano y que no se reutilice `ai_enabled`, `status` ni `waiting_human` como proxy.
  - [x] Identificar donde persistir la preferencia de autoasignacion por tenant sin crear un modulo paralelo ni un store local.
- [x] Persistir la regla de autoasignacion por tenant y aplicarla en la creacion/reuso de conversaciones.
  - [x] Extender el modelo `Company` o la configuracion tenant-scoped equivalente con un flag persistido para habilitar o deshabilitar la autoasignacion cuando exista un unico usuario adicional activo.
  - [x] Exponer ese flag en `CompanyRead` y `CompanyUpdate`, con default seguro alineado al comportamiento esperado del V1.
  - [x] Aplicar la regla en el camino caliente de WhatsApp, idealmente donde `get_or_create_open_conversation()` reusa o crea el hilo, para que el chat nuevo salga ya asignado cuando corresponda.
  - [x] Mantener auditoria/evento cuando la asignacion automatico-canonica cambie el responsable del hilo.
- [x] Endurecer backend de asignacion, toma y reasignacion.
  - [x] Reusar `POST /conversations/{conversation_id}/assign` para la mutacion canonica de responsable, pero ajustar permisos para que solo usuarios autorizados puedan tomar o reasignar segun su rol y modulo.
  - [x] Separar claramente el caso de "tomar chat" del caso de "reasignar a otro usuario" en reglas de servicio y en la UI.
  - [x] Garantizar que reasignar a otro usuario publique `conversation.assigned`, actualice `last_message_at` si el patron actual lo requiere y deje trazabilidad completa.
  - [x] Mantener el comportamiento cross-tenant en `404` y preservar la semantica actual de errores en espanol.
- [x] Mostrar el responsable correcto y las acciones correctas en el Inbox.
  - [x] Actualizar `conversation_to_inbox_item()` y/o el mapeo del frontend para distinguir `sin asignar`, `asignado a mi`, `asignado a otro usuario` y `tomado por mi`.
  - [x] Añadir UI de toma rapida para chats disponibles y, para owner/admin, selector de reasignacion a usuarios del tenant.
  - [x] Si el frontend necesita el nombre del responsable para no mostrar texto generico, obtenerlo desde la API sin introducir un store paralelo ni romper el aislamiento por tenant.
  - [x] Mantener la seleccion del hilo, el draft del composer y el refresh realtime cuando la mutacion falle o tarde.
- [x] Exponer y editar la preferencia de autoasignacion en Configuracion.
  - [x] Reusar `SettingsPage` en `frontend/src/App.tsx` para mostrar el toggle del tenant solo a quienes ya pueden administrar Configuracion.
  - [x] Guardar la preferencia con `api<T>()` en el mismo flujo de perfil del tenant o en el endpoint correcto del dominio `companies`.
  - [x] Mostrar copy honesto en espanol: si se desactiva, los chats nuevos quedan disponibles hasta que alguien los tome o un admin los asigne.
- [x] Agregar regresion automatizada.
  - [x] Cubrir toma de chat, reasignacion, autoasignacion por unico usuario adicional y desactivacion de autoasignacion.
  - [x] Cubrir permisos: usuario sin Inbox bloqueado, cross-tenant `404`, admin/owner con reasignacion, y usuario comun limitado a tomar lo que le corresponde.
  - [x] Cubrir que la UI no pierda el hilo ni invente responsable local cuando la mutacion falle.
  - [x] Verificar que el Inbox siga ordenando por actividad reciente y que la asignacion no rompa el realtime existente.

## Notas de desarrollo

### Contexto de negocio

- Esta historia completa la operacion humana del Inbox: el equipo necesita repartir chats sin duplicar trabajo y con trazabilidad de quien esta atendiendo cada hilo.
- El alcance no es crear un sistema nuevo de colas; el objetivo es formalizar la asignacion que hoy ya existe parcialmente en el dominio de conversaciones.
- La autoasignacion por unico usuario adicional es una regla de negocio del tenant, no una preferencia de UI. Debe quedar persistida y auditable.
- La IA y el responsable humano son estados distintos. Esta historia solo gobierna el responsable humano y las reglas de disponibilidad/asignacion.

### Estado actual del codigo

- `backend/app/conversations/service.py` ya tiene `assign_conversation()` y persiste `assigned_user_id`, `status`, evento `conversation.assigned`, realtime y auditoria.
- `backend/app/conversations/routes.py` ya expone `POST /conversations/{conversation_id}/assign`, pero hoy no tiene un contrato explicitamente separado entre tomar, asignar y reasignar ni una politica fina de permisos para Inbox.
- `backend/app/conversations/service.py` no implementa autoasignacion por tenant en `get_or_create_open_conversation()`; los hilos nuevos entran sin responsable por defecto.
- `backend/app/whatsapp/service.py` crea o reusa conversaciones desde el webhook, asi que cualquier autoasignacion real debe vivir ahi o en el helper llamado por ese camino.
- `backend/app/companies/models.py` y `backend/app/companies/service.py` no tienen aun un flag persistido para la autoasignacion del Inbox.
- `backend/app/conversations/service.py` ya arma el item de Inbox con `assigned_user_id`, `funnel_name`, `funnel_step_name` y `last_message`, pero el frontend hoy solo traduce el estado a "Asignada a un asesor" o "Sin asignar".
- `frontend/src/App.tsx` ya refresca el Inbox por realtime, conserva la seleccion del hilo y tiene mecanismos para no perder el composer cuando una mutacion falla; esa garantia debe mantenerse.
- `frontend/src/App.tsx` y `backend/app/users/routes.py` ya permiten obtener usuarios del tenant; eso puede reutilizarse para mostrar nombres de responsables o permitir reasignacion desde la UI.

### Guardrails criticos

- No usar `ai_enabled`, `status` ni `waiting_human` como sustituto del responsable humano.
- No crear una fuente nueva de verdad paralela para la asignacion.
- No romper la visibilidad realtime del Inbox ni el orden por actividad reciente.
- No permitir que un chat de otro tenant se trate como si existiera; debe seguir respondiendo `404`.
- No ampliar acceso cross-tenant salvo la excepcion explicita de superadmin ya existente.
- No perder el draft del composer ni la seleccion del hilo si falla la toma o la reasignacion.
- No exponer secrets, credenciales ni datos de otros usuarios del tenant en la UI.

### Guidance de implementacion

- Si se agrega un flag de autoasignacion en `Company`, debe ser tenant-scoped, migrado y expuesto por `CompanyRead`/`CompanyUpdate` antes de considerarse listo.
- La regla de "exactamente un usuario adicional activo" debe calcularse con datos reales del tenant y no con heuristicas del frontend.
- Para toma rapida de chat, la UX debe permitir que un usuario con Inbox tome un hilo disponible sin obligarlo a navegar a Configuracion.
- Para reasignar a otro usuario, el control debe estar limitado a owner/admin o al rol que el backend ya considere autorizado; no basta con ocultar el selector en UI.
- El frontend debe mostrar labels cortos y claros en espanol: `Sin asignar`, `Tomado por mi`, `Asignado a otro asesor`, `Reasignado`.
- Si se expone el responsable por nombre, el backend debe seguir respetando el aislamiento por `company_id` y no depender de datos de otro tenant.

### Pruebas y calidad

- Probar toma de chat, reasignacion y autoasignacion con el backend aislado por tenant.
- Probar que el permiso de Inbox se exige en las rutas y que la reasignacion administrativa no queda abierta a cualquier usuario autenticado.
- Probar el caso de un tenant con un solo usuario adicional activo y el caso con la autoasignacion desactivada.
- Probar que la mutacion publica el evento `conversation.assigned` y que la vista del Inbox se refresca sin perder contexto.
- Mantener compatibilidad con la suite SQLite en memoria y con las reglas MySQL del proyecto cuando haya migracion.

### Project Structure Notes

- El dominio correcto para la logica principal es `backend/app/conversations/`, con apoyo de `backend/app/whatsapp/` para el flujo de webhook.
- Si la preferencia de autoasignacion vive en `companies`, mantenerla ahi y no introducir un modulo de settings nuevo en backend.
- En frontend, mantener el shell del Inbox en `frontend/src/App.tsx`; extraer componentes solo si reduce complejidad real.
- Si se necesita un mapping de responsables, reutilizar `GET /users` o extender la respuesta de conversaciones, pero no crear una segunda API ad hoc para el mismo dato.
- No introducir dependencias nuevas para resolver esta historia.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Epic 2, Historia 2.4, FR019-FR026, FR172-FR173]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - seccion Inbox, roles y permisos, y NFR010, NFR011, NFR012, NFR015, NFR018, NFR019, NFR022, NFR027, NFR028, NFR029]
- [Source: `_bmad-output/project-context.md` - reglas criticas de multi-tenancy, permisos, backend como fuente de verdad y `404` cross-tenant]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - Inbox como workspace de lista, hilo y rail contextual; separacion entre estado de dominio y UI]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/EXPERIENCE.md` - Conversation list item, Handoff actions, estados IA activa/handoff humano, y filtros recomendados]
- [Source: `_bmad-output/planning-artifacts/ux-designs/ux-Swaflow-2026-06-09/DESIGN.md` - Conversation list item, Conversation context rail, estados y sistema visual Swa Tech]
- [Source: `backend/app/conversations/models.py`]
- [Source: `backend/app/conversations/routes.py`]
- [Source: `backend/app/conversations/schemas.py`]
- [Source: `backend/app/conversations/service.py`]
- [Source: `backend/app/whatsapp/service.py`]
- [Source: `backend/app/companies/models.py`]
- [Source: `backend/app/companies/schemas.py`]
- [Source: `backend/app/companies/service.py`]
- [Source: `backend/app/users/routes.py`]
- [Source: `backend/app/users/permissions.py`]
- [Source: `frontend/src/App.tsx` - `InboxPage`, `SettingsPage`, `mapApiConversation`, realtime refresh y composer state]
- [Source: `backend/tests/test_inbox_realtime.py`]
- [Source: `backend/tests/test_tenant_and_orders.py`]
- [Source: `backend/tests/test_user_permissions.py`]

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

- `backend/app/conversations/service.py`: helper de asignacion canonica, autoasignacion por unico usuario adicional y auditoria/realtime.
- `backend/app/whatsapp/service.py`: aplicacion de autoasignacion en el webhook entrante antes de persistir el mensaje.
- `backend/app/companies/service.py`: persistencia y validacion del flag tenant-scoped de autoasignacion.
- `frontend/src/App.tsx`: labels de asignacion en Inbox, toma rapida, reasignacion y toggle de configuracion.
- `frontend/src/App.tsx`: guard de obsolescencia para el detalle de conversacion y proteccion contra respuestas viejas.
- `backend/tests/test_tenant_and_orders.py`, `backend/tests/test_user_permissions.py`, `backend/tests/test_whatsapp_setup.py`: regresion de permisos, autoasignacion y webhook.
- `backend/tests/test_user_permissions.py`: regression para impedir que un usuario no privilegiado tome un hilo ya asignado a otro.
- `backend/.venv/bin/pytest backend/tests/test_tenant_and_orders.py backend/tests/test_user_permissions.py backend/tests/test_whatsapp_setup.py -q`
- `backend/.venv/bin/pytest backend/tests/test_user_permissions.py -q`
- `backend/.venv/bin/pytest backend/tests/test_inbox_realtime.py -q`
- `npm run build`
- `npm run lint`
- `backend/app/companies/service.py`: autoasignacion restringida a usuarios con acceso a Inbox.
- `backend/app/conversations/service.py`: bloqueo de self-take sobre hilo ya asignado, sin reordenar por acciones de estado.
- `frontend/src/App.tsx`: cancelacion del detalle de Inbox, limpieza del hilo anterior y filtrado de asignables por Inbox.
- `backend/tests/test_whatsapp_setup.py`: regresion para autoasignacion deshabilitada cuando el unico candidato no tiene Inbox.
- `backend/tests/test_inbox_realtime.py`: actualizacion del criterio de orden para que acciones de estado no alteren la recencia.
- `backend/tests/test_user_permissions.py`: regresion para impedir steal de un hilo ya tomado por otro usuario privilegiado.
- `backend/.venv/bin/pytest backend/tests/test_user_permissions.py backend/tests/test_whatsapp_setup.py backend/tests/test_inbox_realtime.py -q`
- `backend/.venv/bin/pytest backend/tests/test_tenant_and_orders.py -q`
- `cd frontend && npm run build`
- `cd frontend && npm run lint`
- `backend/app/whatsapp/service.py`: autoasignacion tambien aplicada en los envios salientes de WhatsApp antes de persistir el mensaje.
- `backend/tests/test_whatsapp_setup.py`: regresion para confirmar que un envio manual saliente autoasigna el unico usuario adicional con Inbox.
- `backend/.venv/bin/pytest backend/tests/test_whatsapp_setup.py backend/tests/test_inbox_realtime.py backend/tests/test_tenant_and_orders.py -q`

### Completion Notes List

- Se persistio `auto_assign_single_additional_user_chats` en `Company` con migracion Alembic y exposicion en `CompanyRead`/`CompanyUpdate`.
- La conversacion nueva por webhook o creacion manual ahora se autoasigna cuando existe exactamente un usuario adicional activo y el flag del tenant esta habilitado.
- La mutacion de asignacion exige Inbox, diferencia toma propia de reasignacion y mantiene eventos, realtime y auditoria.
- El Inbox ahora muestra el responsable con nombres reales cuando estan disponibles y expone acciones de toma/reasignacion desde la UI.
- La pantalla de Configuracion incluye el toggle de autoasignacion para roles privilegiados.
- Validacion ejecutada: `107 passed` en backend y `npm run build`/`npm run lint` en frontend.
- El worktree ya tenia cambios ajenos a esta historia; no se revertio ningun archivo fuera del alcance de esta implementacion.
- Se corrigio el caso de apropiacion de chats asignados: la accion de toma ahora solo aplica sobre conversaciones disponibles o ya propias.
- Se corrigio la carrera de carga del detalle de Inbox: respuestas viejas ya no pueden sobrescribir el hilo seleccionado.
- Se agrego regresion para el bloqueo de toma sobre un hilo asignado a otro usuario.
- Validacion adicional ejecutada: `backend/tests/test_user_permissions.py`, `backend/tests/test_inbox_realtime.py`, `backend/tests/test_tenant_and_orders.py backend/tests/test_whatsapp_setup.py`, `npm run build`, `npm run lint`.
- Se corrigio la autoasignacion para ignorar usuarios sin acceso a Inbox.
- Se elimino el reordenamiento del Inbox provocado por cambios de estado sin mensaje nuevo.
- Se agrego regresion para el takeover privilegiado sobre un hilo ya tomado y para un candidato unico sin Inbox.
- Validacion adicional ejecutada: `backend/tests/test_user_permissions.py backend/tests/test_whatsapp_setup.py backend/tests/test_inbox_realtime.py`, `backend/tests/test_tenant_and_orders.py -q`, `npm run build`, `npm run lint`.
- Se corrigio el flujo saliente de WhatsApp para que la autoasignacion canonica tambien se aplique al crear conversaciones desde mensajes enviados manualmente.
- Se agrego regresion para asegurar que un envio manual saliente autoasigna al unico usuario adicional con acceso a Inbox.
- Validacion adicional ejecutada: `backend/.venv/bin/pytest backend/tests/test_whatsapp_setup.py backend/tests/test_inbox_realtime.py backend/tests/test_tenant_and_orders.py -q`.
- Se cerraron los hallazgos de code review para el backfill de `message.status`, la auditoria de autoasignacion entrante y la serializacion de autoasignacion.
- Validacion final ejecutada: `backend/.venv/bin/pytest backend/tests/test_whatsapp_setup.py backend/tests/test_inbox_realtime.py backend/tests/test_tenant_and_orders.py -q`.

### File List

- `backend/app/companies/models.py`
- `backend/app/companies/schemas.py`
- `backend/app/companies/service.py`
- `backend/app/conversations/routes.py`
- `backend/app/conversations/service.py`
- `backend/app/whatsapp/service.py`
- `backend/migrations/versions/20260702_0020_company_auto_assign_single_additional_user_chats.py`
- `backend/tests/test_tenant_and_orders.py`
- `backend/tests/test_inbox_realtime.py`
- `backend/tests/test_user_permissions.py`
- `backend/tests/test_whatsapp_setup.py`
- `frontend/src/App.tsx`
- `frontend/src/lib/api.ts`

### Change Log

- 2026-07-02: implemented tenant-level autoasignacion, manual take/reassign flow, Inbox labels/actions, settings toggle, migration and regression tests.
- 2026-07-02: addressed review findings for stolen-thread take action and stale conversation detail race.
- 2026-07-02: addressed follow-up review findings for Inbox-only autoassign, privileged takeover conflict handling, and state-only inbox reordering.
- 2026-07-03: addressed code review findings for outbound status backfill, inbound autoassign auditability, and autoassign locking.

### Review Findings

- [x] [Review][Patch] El fallback de `message.status` consulta el tipo de evento equivocado [backend/app/whatsapp/service.py:1734]
- [x] [Review][Patch] La autoasignacion entrante no queda registrada en auditoria [backend/app/whatsapp/service.py:1564]
- [x] [Review][Patch] La autoasignacion usa un read-modify-write sin bloqueo y puede duplicar eventos [backend/app/conversations/service.py:227]

## Status

done
