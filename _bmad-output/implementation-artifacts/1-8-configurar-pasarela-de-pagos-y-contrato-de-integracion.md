---
baseline_commit: 533ce87609109706230237ebe5629fd34c324fa9
---

# Historia 1.8: Configurar pasarela de pagos y contrato de integracion

Status: done

## Historia

Como admin principal del tenant,
Quiero configurar una pasarela de pagos compatible con el contrato tecnico de Swaflow,
para que pueda generar links de pago y recibir confirmaciones validas sin depender de un solo proveedor.

## Criterios de aceptación

1. Dado que el tenant tiene una pasarela disponible, when el admin registra sus credenciales y parametros, then el sistema cifra los secretos y valida que existan los datos minimos para operar.
2. Dado que la pasarela queda configurada, when el sistema crea un link de pago, then el adaptador comun permite generar el enlace, configurar expiracion, validar webhook y mapear estados.
3. Dado que la configuracion de expiracion de links es visible, when el admin define el tiempo de expiracion, then el sistema aplica el valor configurado al crear nuevos links y conserva el comportamiento por defecto de 120 minutos si no se cambia.

**FR cubiertos:** FR110, FR111, FR153, FR154, FR167, FR168, FR169, FR174

## Tareas / Subtareas

- [x] Formalize the payment integration contract in backend services.
  - [x] Keep `CompanyIntegration` as the canonical tenant-scoped record for pagos.
  - [x] Introduce a provider-agnostic adapter/validator shape for `create_payment_link`, webhook validation, status mapping y idempotency checks.
  - [x] Preserve Wompi as the first concrete adapter y do not fork a second payment subsystem.
- [x] Enforce minimum configuration y activation rules.
  - [x] Validate that credentials, provider metadata y webhook-mapping fields exist before marking a payment integration active.
  - [x] Keep secrets encrypted at rest y redacted in responses.
  - [x] Return tenant-safe errors (`404` for other tenant, `422` for invalid or incomplete config).
- [x] Make link generation use the adapter contract end to end.
  - [x] Reuse the existing order flow that stores `payment_provider`, `payment_reference`, `payment_link` y payment metadata.
  - [x] Apply the configured payment-link TTL to new links only.
  - [x] Preserve the default TTL of 120 minutes when no override is saved.
- [x] Keep webhook processing idempotent y backend-owned.
  - [x] Ensure webhook payloads map to a known order by reference or provider-specific link id.
  - [x] Prevent duplicate processing by reference or transaction identifier.
  - [x] Preserve current order, inventory y audit side effects on payment confirmation.
- [x] Update the existing Integrations UI rather than creating a new surface.
  - [x] Reuse the current payment integration section in `frontend/src/App.tsx`.
  - [x] Expose the provider, environment, redirect URL y expiration fields already used by the app.
  - [x] Make validation feedback clear without showing plaintext secrets after save.
- [x] Add regression coverage for the payment contract.
  - [x] Test tenant-scoped CRUD y `404` for other tenants.
  - [x] Test encrypted credential storage y readback through decrypt helpers.
- [x] Probar el TTL por defecto de 120 minutos y el TTL personalizado aplicado a nuevos enlaces de pago.
  - [x] Test webhook idempotency y order settlement still update inventory correctly.

## Notas de desarrollo

### Contexto de negocio

- Esta story cierra el contrato tecnico de pagos V1: el backend debe poder generar links de pago, aceptar confirmaciones validas y soportar mas de un proveedor sin depender de una implementacion ad hoc por pantalla o por webhook.
- El backend sigue siendo la fuente de verdad para ordenes, pagos, inventario y estados criticos. La UI solo configura y muestra estado.
- El contrato minimo debe cubrir creacion de link, expiracion, validacion de webhook, mapeo de estados e idempotencia por referencia/transaccion.
- No se debe inventar un flujo nuevo para pagos: el repo ya tiene un modulo `integrations`, un modulo `orders` y un modulo `payments` que deben seguir siendo los puntos de extension.

### Estado actual del codigo

- `backend/app/integrations/models.py` ya tiene `CompanyIntegration` con `type`, `credentials_encrypted`, `config` y `status`.
- `backend/app/integrations/service.py` ya cifra credenciales, registra auditoria y hace CRUD tenant-scoped para integraciones.
- `backend/app/orders/service.py` ya genera links de pago desde la orden, usa `CompanyIntegration.type == "payments"` y guarda `payment_provider`, `payment_reference`, `payment_link` y metadata de expiracion.
- `backend/app/payments/providers/wompi.py` ya encapsula la creacion de payment links y la validacion de checksum/evento de Wompi.
- `backend/app/payments/routes.py` ya procesa webhooks de Wompi y un webhook mock de Mercado Pago, pero el contrato general aun esta fragmentado entre ordenes, proveedores y rutas.
- `frontend/src/App.tsx` ya tiene la seccion de integraciones de pago con campos de proveedor, ambiente, moneda, llave publica, URL de retorno y TTL de link; no crear otra pantalla para esto.
- `backend/tests/test_tenant_and_orders.py` ya valida el flujo de crear orden, generar link y marcar pago; esta story debe ampliar esa cobertura sin romper el comportamiento existente.

### Reglas criticas a preservar

- Mantener aislamiento multi-tenant por `company_id` en lectura y escritura.
- Mantener secretos y credenciales cifrados y nunca exponerlos en texto plano en UI, logs o respuestas API.
- No permitir que un webhook o un payload de configuracion cambie estados criticos sin validacion backend.
- No romper el flujo actual de reserva de inventario, confirmacion de pago y auditoria de eventos.
- No introducir una cola, worker o dependencia nueva para resolver el contrato de pasarela.
- No cambiar la decision activa de MySQL.

### Inference explicita para la solucion

- La forma menos riesgosa de cerrar esta story es consolidar un contrato comun de pasarela dentro del dominio de pagos, y mantener `CompanyIntegration` como persistencia canonica para el tenant.
- El proveedor Wompi ya existe y debe servir como referencia del contrato; otros proveedores pueden quedar soportados por la misma interfaz si el repo ya los expone.
- Si se agrega una validacion de activacion o de preview, debe pasar por la misma logica de contrato que la ruta real usa para evitar bypasses.
- El TTL de `payment_link_ttl_minutes` debe aplicarse solo a links nuevos; no reescribir vencimientos ya emitidos salvo un flujo explicito del producto.

### Arquitectura y salvaguardas

- Seguir la frontera de dominio existente: `backend/app/integrations/`, `backend/app/orders/`, `backend/app/payments/` y `frontend/src/App.tsx`.
- Reusar `encrypt_secret` / `decrypt_secret` para cualquier credencial de pasarela.
- Preservar el comportamiento de `404` para recursos de otro tenant y `422` para payload/configuracion invalida.
- Si el adaptador requiere campos de contrato adicionales, mantenerlos en `config` JSON del integration y no en texto libre.
- Mantener el backend como fuente de verdad; n8n o webhooks auxiliares no deben confirmar pagos ni modificar inventario.

### File Structure Notes

- Backend candidato a tocar:
  - `backend/app/integrations/models.py`
  - `backend/app/integrations/schemas.py`
  - `backend/app/integrations/service.py`
  - `backend/app/integrations/routes.py`
  - `backend/app/orders/service.py`
  - `backend/app/payments/providers/wompi.py`
  - `backend/app/payments/routes.py`
  - `backend/app/payments/schemas.py`
  - `backend/app/main.py` solo si se agregan rutas nuevas
- Frontend candidato a tocar:
  - `frontend/src/App.tsx`
- Tests candidatos:
  - `backend/tests/test_tenant_and_orders.py`
  - un archivo nuevo de pruebas de pagos si el contrato crece demasiado para aislarlo bien

### Testing requirements

- Cubrir que un tenant pueda guardar, editar y activar configuracion de pasarela sin romper la base comercial ya existente.
- Cubrir que la lectura y escritura siguen siendo tenant-scoped y que un tenant ajeno recibe `404`.
- Cubrir que credenciales y secretos quedan cifrados en reposo.
- Cubrir que el contrato rechaza configuraciones incompletas o invalidas con `422`.
- Cubrir que el TTL por defecto sigue siendo 120 minutos y que una configuracion explicita solo afecta links nuevos.
- Cubrir que la confirmacion por webhook sigue siendo idempotente y conserva las reservas/consumo de inventario esperados.
- Cubrir que la UI de integraciones sigue mostrando el flujo de pago sin revelar credenciales.

### Previous story intelligence

- Historia 1.7 ya dejo claro que las capacidades operativas criticas deben vivir en backend como reglas ejecutables, no solo como texto de UI.
- Historia 1.7 tambien reforzo que no se debe crear una ruta paralela o un flujo de preview que se salte la validacion de guardrails.
- Para pagos, la misma regla aplica: cualquier validacion de activacion, contrato o simulacion debe usar la misma logica que el flujo real, o se corre el riesgo de aceptar configuraciones invalidas que rompan confirmaciones de pago.

### Latest technical notes

- El proyecto ya esta fijado a Python `>=3.12`, FastAPI `>=0.115`, SQLAlchemy `>=2.0`, Pydantic `>=2.4`, React `^18.3.1` y Vite `^8.0.13`.
- El stack actual ya usa `Session`, `select`, `model_dump`, `HTTPException` y `Field(...)`; mantener ese estilo.
- El servicio de pagos ya usa `httpx` para crear payment links de Wompi y `hmac`/`hashlib` para validacion de webhooks en otros dominios del repo; no introducir otro cliente HTTP sin motivo.
- No introducir SQL o migraciones que dependan de PostgreSQL.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` - Historia 1.8, FR110-FR111, FR153-FR154, FR167-FR174]
- [Source: `_bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md` - contrato de pagos, links, expiracion, idempotencia y guardrails]
- [Source: `_bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md` - pagos y adaptadores de pasarela, backend source of truth, outbox e idempotencia]
- [Source: `_bmad-output/project-context.md` - MySQL vigente, seguridad, tenant scoping y reglas criticas de implementacion]
- [Source: `backend/app/integrations/models.py` - `CompanyIntegration` y credenciales cifradas]
- [Source: `backend/app/integrations/service.py` - CRUD tenant-scoped y auditoria de integraciones]
- [Source: `backend/app/orders/service.py` - generacion de payment links, TTL y flujo de cierre]
- [Source: `backend/app/payments/providers/wompi.py` - enlace de pago y verificacion de evento Wompi]
- [Source: `backend/app/payments/routes.py` - webhooks de pago existentes]
- [Source: `frontend/src/App.tsx` - seccion de integraciones de pago ya presente]
- [Source: `_bmad-output/implementation-artifacts/1-7-configurar-seguridad-y-comportamiento-operativo-de-la-ia.md` - precedente de guardrails y backend source of truth]

## Dev Agent Record

### Agent Model Used

GPT-5

### Referencias de depuración

- 2026-06-25: agregado `backend/app/payments/contract.py` con helpers de adaptador agnosticos del proveedor, parseo de TTL, validacion de integracion y deduplicacion de eventos de pago.
- 2026-06-25: agregado `backend/app/payments/service.py` para centralizar el procesamiento de webhooks y reutilizar el contrato compartido de pagos desde las rutas.
- 2026-06-25: conectado `backend/app/integrations/service.py` para validar integraciones de pago antes de la activacion y preservar las credenciales cifradas en la actualizacion.
- 2026-06-25: refactorizado `backend/app/orders/service.py` para usar el contrato de pagos en la resolucion del proveedor, la generacion de enlaces con TTL y el comportamiento seguro de respaldo cuando no existe integracion.
- 2026-06-25: simplifico `backend/app/payments/routes.py` para que los webhooks de pago fluyan por el servicio compartido y la logica de idempotencia.
- 2026-06-25: agregadas pruebas de regresion para la validacion de configuracion de pago, el comportamiento de TTL, la idempotencia del webhook de Wompi, la deduplicacion por referencia mock y el flujo existente de orden/pago.
- 2026-06-25: validado con `python3 -m py_compile backend/app/payments/contract.py backend/app/payments/service.py backend/app/integrations/service.py backend/app/orders/service.py backend/app/payments/routes.py backend/tests/test_tenant_and_orders.py`, `cd backend && ./.venv/bin/pytest -q` (`91 passed`), `cd frontend && npm run lint`, y `cd frontend && npm run build`.

### Lista de notas de cierre

- El contrato de pagos quedo unificado sin introducir un segundo subsistema; Wompi permanece como adapter real y el resto de proveedores locales comparten la misma forma de contrato.
- La integracion de pagos activa ahora exige proveedor explicito y, para Wompi, `events_secret`; los borradores inactivos no quedan bloqueados por validaciones de activacion.
- El TTL de links de pago se respeta por tenant y conserva `120` minutos por defecto cuando no existe override.
- La confirmacion por webhook queda deduplicada por transaction id y, en flujos sin transaction id, por referencia de pago.
- La ruta existente de integraciones siguio siendo la superficie de UI y no requirio una pantalla nueva.
- La suite completa del backend y la compilacion/lint del frontend quedaron verdes al cierre de la historia.

### Lista de archivos

- `backend/app/payments/contract.py`
- `backend/app/payments/service.py`
- `backend/app/integrations/service.py`
- `backend/app/orders/service.py`
- `backend/app/payments/routes.py`
- `backend/tests/test_tenant_and_orders.py`
- `_bmad-output/implementation-artifacts/1-8-configurar-pasarela-de-pagos-y-contrato-de-integracion.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

## Registro de cambios

- 2026-06-25: completada la implementacion de la historia 1.8 y movida la historia a `review`.
- 2026-06-25: agregado el contrato de pagos del backend, el servicio de webhooks, el manejo de TTL y las pruebas de regresion.
- 2026-06-26: resueltos los hallazgos de code review y movida la historia a `done`.

### Hallazgos de revisión

- [x] [Review][Patch] Los logs de auditoria persistian secretos en texto plano durante la actualizacion de integraciones [backend/app/integrations/service.py:140] - `payload.model_dump(exclude_unset=True)` se escribe en `record_audit()` durante la actualizacion, por lo que `credentials` y `secret_token` podian almacenarse en texto claro dentro de los metadatos de auditoria. Esto tambien afectaba las actualizaciones de webhooks salientes en `backend/app/integrations/service.py:224`.
- [x] [Review][Patch] La busqueda de webhooks de pago aceptaba proveedores no coincidentes para la misma referencia de pago [backend/app/payments/contract.py:383] - `find_order_for_payment_event()` caia a una busqueda solo por referencia despues de un fallo especifico de proveedor, y `mark_paid_by_reference()` hacia lo mismo. Un webhook del proveedor equivocado podia resolver y cerrar una orden, lo que viola la regla de aislamiento por tenant/proveedor.
