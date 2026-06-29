# Addendum del PRD: Detalles técnicos

Este addendum conserva detalle tecnico que apoya el PRD, sin convertir el PRD
principal en documento de arquitectura.

## Contrato del adaptador de pasarela de pago

### Objetivo

Swaflow debe soportar pasarelas de pago mediante adaptadores o proveedores
configurados/certificados por Swateck. Ninguna pasarela debe integrarse como
codigo ad hoc sin cumplir este contrato minimo.

### Principios

- Backend Swaflow es fuente de verdad de ordenes, estados, inventario y eventos.
- La pasarela es fuente de verdad solo para el resultado del pago.
- La IA y el frontend nunca confirman pagos manualmente.
- Todo webhook de pago debe validarse antes de cambiar estado de orden.
- Todo procesamiento de webhook debe ser idempotente.
- Las credenciales se guardan cifradas y no se exponen completas en UI/logs.

### Capacidades obligatorias del adaptador

Cada adaptador debe implementar:

- Crear link de pago para una orden.
- Definir o respetar expiracion de link.
- Recibir webhook o evento equivalente de pago.
- Validar firma, checksum, token o secreto del proveedor.
- Extraer referencia de pago, ID de transaccion y estado del pago.
- Mapear estados del proveedor a estados normalizados de Swaflow.
- Evitar doble procesamiento por referencia/transaccion/event ID.
- Exponer errores entendibles para soporte/admin.

### Configuración por tenant

Cada integracion de pagos debe almacenar configuracion tenant-scoped:

```json
{
  "provider": "provider_key",
  "environment": "sandbox|production",
  "payment_link_ttl_minutes": 120,
  "redirect_url": "https://...",
  "webhook_url": "https://swaflow.../webhooks/payments/{provider}",
  "currency": "COP"
}
```

Credenciales cifradas esperadas, segun proveedor:

```json
{
  "private_key": "...",
  "public_key": "...",
  "events_secret": "...",
  "webhook_secret": "..."
}
```

El adaptador debe documentar cuales campos son obligatorios y cuales son
opcionales. Swaflow debe impedir activar una pasarela si faltan datos minimos
para crear links, validar webhooks y mapear estados.

### Crear enlace de pago

Entrada normalizada:

```json
{
  "tenant_id": "uuid",
  "order_id": "uuid",
  "payment_reference": "swaflow_xxx",
  "amount": "250000.00",
  "currency": "COP",
  "expires_in_minutes": 120,
  "redirect_url": "https://..."
}
```

Salida normalizada:

```json
{
  "provider": "provider_key",
  "payment_reference": "swaflow_xxx",
  "payment_link": "https://...",
  "provider_link_id": "external_link_id",
  "expires_at": "2026-06-09T15:30:00Z",
  "raw": {}
}
```

Reglas:

- `payment_reference` debe ser unica por orden y proveedor.
- El link debe ser de un solo uso si el proveedor lo soporta.
- El monto y moneda deben venir de la orden, no de la IA ni del frontend.
- El vencimiento por defecto es 120 minutos, configurable por tenant.

### Webhook de pago

Entrada esperada:

- Payload crudo del proveedor.
- Headers necesarios para validar firma/checksum/token.
- Identificador de evento cuando el proveedor lo entregue.

El adaptador debe extraer:

```json
{
  "provider": "provider_key",
  "event_id": "evt_xxx",
  "payment_reference": "swaflow_xxx",
  "provider_transaction_id": "txn_xxx",
  "provider_link_id": "link_xxx",
  "provider_status": "APPROVED",
  "normalized_status": "paid",
  "amount": "250000.00",
  "currency": "COP",
  "paid_at": "2026-06-09T15:30:00Z",
  "raw": {}
}
```

Reglas:

- Si la firma/secret/checksum falla, responder error y no cambiar la orden.
- Si no se puede correlacionar una orden, responder `ignored` y registrar
  evidencia suficiente para soporte.
- Si el evento ya fue procesado, responder `processed` o `ignored` sin aplicar
  cambios duplicados.
- Si el estado recibido no es terminal, actualizar metadata sin consumir
  inventario salvo que el estado normalizado lo requiera.

### Estados normalizados

El adaptador debe mapear estados del proveedor a:

- `pending`: pago creado o esperando accion.
- `waiting_payment`: link emitido y orden esperando pago.
- `paid`: pago aprobado/confirmado.
- `failed`: pago rechazado/fallido.
- `expired`: link o intento vencido.
- `cancelled`: pago u orden cancelada.
- `refunded`: reembolso confirmado, si el proveedor lo soporta.
- `unknown`: estado no mapeado; no debe ejecutar accion critica.

Reglas de negocio:

- Solo `paid` puede consumir reserva y marcar venta.
- `failed`, `expired` y `cancelled` pueden liberar reserva segun estado de orden.
- `unknown` debe quedar visible para soporte y no debe confirmar pago.

### Idempotencia

El adaptador debe usar uno o mas de estos identificadores:

- `payment_reference`.
- `provider_transaction_id`.
- `event_id`.
- `provider_link_id`.

Swaflow debe registrar identificadores procesados en metadata/eventos para evitar
doble descuento de inventario, doble venta o doble notificacion.

### Seguridad

- Credenciales siempre cifradas por tenant.
- No registrar llaves privadas ni secretos completos.
- Validar firma/checksum/token de webhook antes de parsear efectos de negocio.
- Rechazar webhooks de proveedor diferente al configurado para la orden.
- No aceptar cambios cross-tenant por referencia externa ambigua.

### Errores normalizados

El adaptador debe traducir errores a categorias:

- `missing_credentials`.
- `invalid_credentials`.
- `provider_unavailable`.
- `invalid_webhook_signature`.
- `unmatched_payment_reference`.
- `unsupported_currency`.
- `invalid_amount`.
- `unknown_provider_status`.
- `duplicate_event`.

### Lista de verificación de certificación de pasarela

Antes de habilitar una pasarela para un tenant real:

- Crear link exitoso en sandbox.
- Validar vencimiento configurable.
- Confirmar pago aprobado por webhook firmado.
- Confirmar rechazo/fallo.
- Confirmar vencimiento.
- Confirmar idempotencia con webhook duplicado.
- Confirmar que pago aprobado descuenta/libera reserva correctamente.
- Confirmar que fallo/vencimiento libera reserva cuando aplique.
- Confirmar que errores no exponen secretos.
- Confirmar eventos internos y notificaciones auxiliares.

### Referencias técnicas

- Stripe API docs: Idempotent requests — https://docs.stripe.com/api/idempotent_requests
- Stripe docs: Webhook signature verification — https://docs.stripe.com/webhooks/signature
- Wompi docs Colombia: Eventos, estructura de eventos, reintentos y checksum — https://docs.wompi.co/docs/colombia/eventos/
