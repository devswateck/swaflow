# Backlog Operativo

Fuente:
- [Epic 1 retrospective](/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/epic-1-retro-2026-07-03.md)
- [Epic 2 retrospective](/Users/camilosanchez/Documents/Swateck/SwaFlow/_bmad-output/implementation-artifacts/epic-2-retro-2026-07-03.md)

## Prioridad 1

### 1. Blindar Inbox contra estado obsoleto y carreras

- Objetivo: evitar que la UI muestre un hilo viejo, un detalle desfasado o un estado incorrecto cuando llegan eventos fuera de orden.
- Dependencias: `backend/app/conversations/service.py`, `backend/app/events/service.py`, `frontend/src/App.tsx`, `backend/tests/test_inbox_realtime.py`.
- Dueño sugerido: Amelia.
- Criterio de salida: el hilo seleccionado, la línea de tiempo y el composer permanecen consistentes al cambiar de conversación o al recibir `message.status`, `message.received` y eventos de asignación.

### 2. Endurecer locking y auditoría en autoasignación y reasignación

- Objetivo: impedir apropiación doble, eventos duplicados y cambios sin trazabilidad.
- Dependencias: `backend/app/conversations/service.py`, `backend/app/whatsapp/service.py`, `backend/app/companies/service.py`, `backend/tests/test_user_permissions.py`, `backend/tests/test_whatsapp_setup.py`.
- Dueño sugerido: Charlie.
- Criterio de salida: un hilo no puede quedar asignado a dos usuarios, la autoasignación se registra una sola vez y cada cambio queda auditado.

## Prioridad 2

### 3. Mantener redacción de secretos y validación de contratos críticos

- Objetivo: evitar que auditorías, logs o respuestas expongan secretos o acepten contratos inválidos.
- Dependencias: `backend/app/integrations/service.py`, `backend/app/payments/contract.py`, `backend/app/payments/routes.py`, `backend/tests/test_tenant_and_orders.py`.
- Dueño sugerido: Amelia.
- Criterio de salida: integraciones, pagos y webhooks fallan de forma segura ante payloads incompletos, y nunca persisten secretos en texto plano.

### 4. Separar con claridad estado humano, IA y clasificación comercial

- Objetivo: no mezclar responsable humano, pausa/reactivación de IA y funnel/etapa en UI ni en API.
- Dependencias: `backend/app/conversations/routes.py`, `backend/app/conversations/schemas.py`, `backend/app/ai/runtime.py`, `frontend/src/App.tsx`.
- Dueño sugerido: Amelia.
- Criterio de salida: cada estado tiene etiquetas y mutaciones propias, con permisos backend validados y sin proxies ambiguos.

### 5. Reforzar rehidratación de agenda desde snapshot persistido

- Objetivo: asegurar que la intención de agenda se reconstruya desde backend y no desde memoria local.
- Dependencias: `backend/app/conversations/service.py`, `backend/app/events/service.py`, `frontend/src/App.tsx`, `backend/tests/test_inbox_realtime.py`.
- Dueño sugerido: Dana.
- Criterio de salida: el draft de agenda siempre coincide con el snapshot persistido más reciente y no se sobrescribe por carreras.

## Prioridad 3

### 6. Mantener permisos críticos validados en backend

- Objetivo: evitar que el frontend sea la única barrera para Inbox, IA, asignación y acciones sensibles.
- Dependencias: `backend/app/users/permissions.py`, `backend/app/conversations/routes.py`, `backend/app/ai/routes.py`, `backend/app/integrations/routes.py`.
- Dueño sugerido: Charlie.
- Criterio de salida: los accesos cross-tenant devuelven `404` y los permisos insuficientes bloquean la mutación en backend.

### 7. Fortalecer regresión automatizada de Inbox e integraciones

- Objetivo: cubrir los puntos que ya mostraron fragilidad en reviews.
- Dependencias: `backend/tests/test_inbox_realtime.py`, `backend/tests/test_user_permissions.py`, `backend/tests/test_whatsapp_setup.py`, `backend/tests/test_tenant_and_orders.py`.
- Dueño sugerido: Dana.
- Criterio de salida: las pruebas cubren orden de eventos, locking, permisos, redacción de secretos y coherencia del hilo.

## Reglas de Ejecución

- No empezar una historia nueva si una prioridad 1 sigue abierta.
- Tratar las prioridades 2 y 3 como refuerzo continuo, no como limpieza opcional.
- Mantener cada item pequeño, verificable y con un dueño claro.
- Si un item toca backend y frontend, validar primero la semántica backend.

