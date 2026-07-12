# Propuesta de Epic 8

## Nombre

Epic 8: Estabilización Operativa y Endurecimiento del Inbox

## Objetivo

Cerrar las brechas de consistencia, permisos, auditoría y resiliencia que quedaron visibles después de las épicas fundacionales, sin introducir funcionalidades nuevas de negocio.

## Alcance

Esta épica agrupa hardening transversal sobre el workspace conversacional, integraciones críticas y seguridad backend.

No debe mezclarse con nuevas features de producto. Su propósito es estabilizar lo ya entregado.

## Historias propuestas

### Historia 8.1: Blindaje de Inbox contra estado obsoleto

- Evitar que el Inbox muestre un hilo viejo, un detalle desfasado o un composer incorrecto cuando llegan eventos fuera de orden.

### Historia 8.2: Locking y auditoría en asignación

- Evitar apropiación doble, eventos duplicados y cambios sin trazabilidad en autoasignación, toma y reasignación.

### Historia 8.3: Redacción de secretos y validación de contratos críticos

- Eliminar fugas de secretos y aceptar solo contratos válidos para integraciones, pagos y webhooks.

### Historia 8.4: Separación de estados humano, IA y clasificación

- Evitar que la UI mezcle responsable humano, estado de IA y clasificación comercial.

### Historia 8.5: Rehidratación de agenda desde snapshot persistido

- Asegurar que la intención de agenda se reconstruya desde backend y no desde memoria local.

### Historia 8.6: Permisos backend para acciones críticas

- Mantener el backend como barrera real para Inbox, IA, integraciones y mutaciones sensibles.

### Historia 8.7: Regresión automatizada continua

- Cubrir los puntos que ya mostraron fragilidad en reviews y evitar regresiones silenciosas.

## Dependencias

- Inbox y conversaciones ya entregados en Epic 2.
- Agenda y citas como dominio de referencia para la historia 8.5.
- Integraciones, pagos y seguridad ya entregadas en Epic 1.

## Criterios de éxito

- El Inbox queda estable bajo eventos concurrentes.
- Las asignaciones no duplican responsables ni auditoría.
- Los secretos no aparecen en texto claro.
- Los permisos se validan en backend.
- La agenda se rehidrata de forma determinista.
- La cobertura de pruebas protege las fragilidades conocidas.

## Orden sugerido

1. 8.1
2. 8.2
3. 8.3
4. 8.4
5. 8.5
6. 8.6
7. 8.7

## Nota

Si luego quieres formalizar esta propuesta dentro del plan oficial, la siguiente acción sería crear el epic en `epics.md` y luego generar las story files correspondientes.

