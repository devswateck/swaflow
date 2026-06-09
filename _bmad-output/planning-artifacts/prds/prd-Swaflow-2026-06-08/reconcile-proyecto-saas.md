# Reconcile: proyecto_saas_ia_comercial_multitenant.md

## Resultado

El PRD conserva el enfoque de producto del documento historico y aplica las decisiones vigentes posteriores.

## Capturado

- Propuesta de valor: ventas conversacionales por WhatsApp con IA.
- Alcance: WhatsApp, Inbox, IA, catalogo, inventario, ordenes, pagos, citas, n8n auxiliar y webhooks.
- Regla central: backend decide operaciones criticas; IA conversa y orquesta.
- Multi-tenancy obligatorio.
- n8n solo auxiliar.
- Estados criticos de ordenes/citas/conversaciones tratados como backend.
- Riesgos principales: alcance excesivo, IA inventando informacion, fuga tenant, pagos y stock.

## Conflictos Resueltos

- PostgreSQL/Celery del documento historico no se trasladan al PRD como decisiones actuales. Prevalece `project-context.md`: MySQL vigente y sin colas criticas.
- SuperUsuario completo se difiere a V2, aunque el rol superadmin existe como requisito transversal.

## Gaps

- Ningun gap bloqueante detectado.

