# Resolución de revisión

## Hallazgos altos resueltos

### Provisionamiento de tenants insuficientemente especificado

Resolución:

- V1: Swateck crea cada tenant y su admin principal mediante proceso operativo/admin.
- El self-service signup de tenants queda fuera de V1.

Actualizado en:

- `prd.md` Product Scope / V2 / No objetivos V1 / FR-170 / FR-171.
- `.decision-log.md`.

### Abstracción de pasarela de pago insuficientemente especificada

Resolución:

- V1 soporta pasarelas mediante adaptadores o proveedores configurados/certificados por Swateck.
- Cada adaptador debe implementar el contrato común: crear enlace de pago, expiración, validación de webhook, mapeo de estados e idempotencia.

Actualizado en:

- `prd.md` Integraciones / FR-167 / FR-168 / FR-169.
- `.decision-log.md`.

## Hallazgo alto resuelto

### Autoasignación cuando existe exactamente un usuario adicional

Resolución:

- Se mantiene la autoasignación por defecto cuando existe exactamente un usuario adicional.
- El admin puede desactivar esa autoasignación para que los chats nuevos queden disponibles o sin asignar.
- El admin conserva la capacidad de ver, asignar y reasignar chats.

Actualizado en:

- `prd.md` Inbox / FR-172 / FR-173.
- `.decision-log.md`.
