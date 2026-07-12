# Backlog por Historias

Base:
- [backlog operativo](/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/backlog.md)

## Historia 1: Blindaje de Inbox contra estado obsoleto

### Objetivo

Evitar que el Inbox muestre un hilo viejo, un detalle desfasado o un composer en estado incorrecto cuando llegan eventos fuera de orden.

### Alcance

- Proteger selección del hilo.
- Proteger merge de eventos realtime.
- Evitar que `message.status` o `conversation.read` reescriban estado más nuevo.
- Mantener coherencia entre lista, detalle y timeline.

### Archivos base

- `backend/app/conversations/service.py`
- `backend/app/events/service.py`
- `backend/tests/test_inbox_realtime.py`
- `frontend/src/App.tsx`

### Criterio de aceptación

- El hilo seleccionado sigue siendo el correcto tras refresh y eventos concurrentes.
- La timeline no pierde mensajes ni duplica estados.
- El composer no se reinicia si la mutación falla.

## Historia 2: Locking y auditoría en asignación

### Objetivo

Evitar apropiación doble, eventos duplicados y cambios sin trazabilidad en autoasignación, toma y reasignación.

### Alcance

- Revisar locking de autoasignación.
- Revisar serialización de asignación manual.
- Confirmar auditoría única por cambio de responsable.
- Mantener permisos backend como fuente de verdad.

### Archivos base

- `backend/app/conversations/service.py`
- `backend/app/whatsapp/service.py`
- `backend/app/companies/service.py`
- `backend/tests/test_user_permissions.py`
- `backend/tests/test_whatsapp_setup.py`

### Criterio de aceptación

- Un chat no puede quedar asignado dos veces por concurrencia.
- Cada cambio de responsable queda registrado una sola vez.
- Los accesos sin permiso fallan con el error correcto.

## Historia 3: Redacción de secretos y validación de contratos

### Objetivo

Eliminar fugas de secretos y aceptar solo contratos válidos para integraciones, pagos y webhooks.

### Alcance

- Revisar auditoría y logs.
- Revisar validación de activación de integraciones.
- Confirmar deduplicación e idempotencia de pagos.
- Mantener fallos auxiliares no destructivos.

### Archivos base

- `backend/app/integrations/service.py`
- `backend/app/payments/contract.py`
- `backend/app/payments/routes.py`
- `backend/tests/test_tenant_and_orders.py`

### Criterio de aceptación

- Ningún secreto se persiste en texto claro en auditoría.
- Las configuraciones incompletas fallan antes de activarse.
- Un webhook equivocado no puede cerrar una orden ajena.

## Historia 4: Separación de estados humano, IA y clasificación

### Objetivo

Evitar que la UI mezcle responsable humano, estado de IA y clasificación comercial.

### Alcance

- Aclarar mutaciones y etiquetas.
- Separar handoff de asignación.
- Mantener funnel y agenda como contexto, no como cita inventada.

### Archivos base

- `backend/app/conversations/routes.py`
- `backend/app/conversations/schemas.py`
- `backend/app/ai/runtime.py`
- `frontend/src/App.tsx`

### Criterio de aceptación

- Cada estado tiene su propio contrato visible.
- Los permisos se validan en backend.
- La UI muestra labels honestos y no proxies ambiguos.

## Historia 5: Rehidratación de agenda desde snapshot persistido

### Objetivo

Asegurar que la intención de agenda se reconstruya desde backend y no desde memoria local.

### Alcance

- Revisar snapshot persistido.
- Revisar event timeline.
- Confirmar que el draft de agenda no se sobrescribe por carreras.

### Archivos base

- `backend/app/conversations/service.py`
- `backend/app/events/service.py`
- `frontend/src/App.tsx`
- `backend/tests/test_inbox_realtime.py`

### Criterio de aceptación

- El contexto rehidratado coincide con el snapshot más reciente.
- El estado de agenda no se pierde al filtrar o cambiar de hilo.
- El draft manual no desaparece por eventos concurrentes.

## Historia 6: Permisos backend para acciones críticas

### Objetivo

Mantener el backend como barrera real para Inbox, IA, integraciones y mutaciones sensibles.

### Alcance

- Revisar guards de rutas.
- Confirmar `404` cross-tenant.
- Confirmar permisos por módulo en acciones críticas.

### Archivos base

- `backend/app/users/permissions.py`
- `backend/app/conversations/routes.py`
- `backend/app/ai/routes.py`
- `backend/app/integrations/routes.py`

### Criterio de aceptación

- Ninguna mutación sensible depende solo del frontend.
- Cross-tenant siempre responde `404`.
- Falta de permiso bloquea la mutación antes de tocar estado.

## Historia 7: Regresión automatizada continua

### Objetivo

Cubrir los puntos que ya mostraron fragilidad en reviews y evitar regresiones silenciosas.

### Alcance

- Orden de eventos.
- Concurrencia.
- Redacción de secretos.
- Permisos.
- Coherencia de hilo.

### Archivos base

- `backend/tests/test_inbox_realtime.py`
- `backend/tests/test_user_permissions.py`
- `backend/tests/test_whatsapp_setup.py`
- `backend/tests/test_tenant_and_orders.py`

### Criterio de aceptación

- Las pruebas cubren los fallos ya observados en review.
- Cada item del backlog crítico tiene al menos una regresión asociada.
- El estado de Inbox y asignación queda estable bajo eventos concurrentes.

## Orden sugerido

1. Historia 1
2. Historia 2
3. Historia 3
4. Historia 4
5. Historia 5
6. Historia 6
7. Historia 7

