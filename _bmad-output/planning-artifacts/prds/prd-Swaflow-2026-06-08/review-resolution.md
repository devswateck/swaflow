# Review Resolution

## Resolved High Findings

### Tenant provisioning under-specified

Resolution:

- V1: Swateck crea cada tenant y su admin principal mediante proceso operativo/admin.
- Self-service signup de tenants queda fuera de V1.

Updated in:

- `prd.md` Product Scope / V2 / Non-Goals V1 / FR-170 / FR-171.
- `.decision-log.md`.

### Payment gateway abstraction under-specified

Resolution:

- V1 soporta pasarelas mediante adaptadores o proveedores configurados/certificados por Swateck.
- Cada adaptador debe implementar contrato comun: crear link de pago, expiracion, validacion de webhook, mapeo de estados e idempotencia.

Updated in:

- `prd.md` Integraciones / FR-167 / FR-168 / FR-169.
- `.decision-log.md`.

## Resolved High Finding

### Autoasignacion cuando existe exactamente un usuario adicional

Resolution:

- Se mantiene autoasignacion por defecto cuando existe exactamente un usuario adicional.
- El admin puede desactivar esa autoasignacion para que chats nuevos queden disponibles/no asignados.
- El admin conserva capacidad de ver, asignar y reasignar chats.

Updated in:

- `prd.md` Inbox / FR-172 / FR-173.
- `.decision-log.md`.
