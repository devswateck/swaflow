# Reconcile: project-context.md

## Resultado

`prd.md` respeta las restricciones tecnicas vigentes del contexto del proyecto.

## Capturado

- SaaS multi-tenant para asistente comercial IA por WhatsApp.
- Backend como fuente de verdad para acciones transaccionales.
- MySQL vigente; no se reintroduce PostgreSQL.
- Redis/n8n no son colas ni fuente de verdad para operaciones criticas.
- IA no inventa precios, stock, disponibilidad, links de pago, politicas ni agenda.
- WhatsApp Cloud API con credenciales cifradas.
- Catalogo e inventario usados como fuente controlada para IA.
- Eventos/webhooks como automatizacion auxiliar.
- Permisos y aislamiento por tenant.

## Gaps

- Ningun gap bloqueante detectado.

