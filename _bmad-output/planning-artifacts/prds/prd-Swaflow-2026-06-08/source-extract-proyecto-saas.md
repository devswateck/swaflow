# Source Extract: proyecto_saas_ia_comercial_multitenant.md

## Producto

- Plataforma SaaS multi-tenant para asistente comercial IA por WhatsApp.
- Enfoque inicial: resolver el proceso comercial conversacional, no clonar CRM/ERP/constructor omnicanal completo.
- Propuesta: atender clientes, calificar leads, consultar catalogo e inventario, generar links de pago, registrar ventas y agendar citas cuando no hay compra inmediata.

## Alcance MVP Historico

- Multi-tenant basico.
- Conexion WhatsApp Cloud API.
- Inbox de conversaciones.
- Motor conversacional IA e intencion del cliente.
- Catalogo, inventario, ordenes, links de pago y webhooks de pago.
- Citas, notificaciones humanas, integracion auxiliar con n8n y webhooks salientes.
- Fuera del MVP historico: builder visual avanzado, omnicanal completo, ERP, CRM avanzado, RAG, voz, multiagentes complejos y automatizaciones criticas en n8n.

## Reglas De Producto/Arquitectura Que Deben Sobrevivir En El PRD

- Si afecta dinero, inventario, pagos, pedidos o estados criticos, vive en backend.
- n8n solo automatiza periferia: correos, calendarios, sincronizaciones, resumenes, webhooks.
- Toda operacion de negocio debe aislarse por `company_id`.
- La IA conversa y orquesta, pero no decide precios, stock, pagos ni estados criticos sin backend.
- Si hay baja confianza o datos incompletos para accion critica, pedir aclaracion.

## Modulos Esperados

- Dashboard.
- Inbox/conversaciones.
- Productos y catalogo Meta.
- Inventario.
- Ordenes.
- Citas.
- Funnels.
- IA.
- WhatsApp.
- Integraciones.
- Configuracion.
- Superusuario/admin SaaS.

## Implementacion Real Ya Documentada En La Fuente

- Produccion existente en `https://swaflow.swateck.com`.
- Backend y frontend separados.
- Multi-tenancy activo por `company_id`.
- MySQL vigente en produccion segun bitacora y `project-context.md`.
- WhatsApp Cloud API operativo para recepcion/envio.
- Inbox funcional con realtime.
- IA por tenant con OpenAI, contexto de conversacion, catalogo, prompts, reglas y plantillas interactivas.
- Sincronizacion de catalogo Meta implementada.
- Productos, inventario, funnels, integraciones, Wompi y links de pago tienen base implementada o parcialmente implementada.

## Conflictos Con Decisiones Vigentes

- La fuente historica recomienda PostgreSQL y Celery/RQ; `project-context.md` declara MySQL vigente y Redis sin colas activas. El PRD debe describir capacidades de producto y dejar estas decisiones tecnicas vigentes como restricciones, no reabrirlas.

