# Auditoría de decisiones

## Resultado

Las decisiones de `.decision-log.md` estan capturadas en `prd.md`.

## Decisiones Capturadas En PRD

- PRD nuevo para Swaflow y alcance V1/V2.
- Uso de `project-context.md` y `proyecto_saas_ia_comercial_multitenant.md`.
- MySQL vigente y no PostgreSQL.
- Redis/n8n sin rol critico transaccional.
- Plataforma SaaS multi-tenant de ventas conversacionales por WhatsApp.
- SuperUsuario avanzado en V2, pero rol superadmin Swateck con acceso cross-tenant.
- Roles por tenant, usuarios adicionales, permisos por modulo y aviso de costo mensual.
- Dashboard, Inbox, WhatsApp, Productos, Inventario, Ordenes, Citas, Funnels, IA, Integraciones y Configuracion V1.
- WhatsApp V1 tecnico; popup/Embedded Signup en V2.
- Productos siempre creados en Meta; Swaflow no crea catalogo adicional.
- Disponibilidad base desde Meta, con reservas operativas en Swaflow.
- Ordenes con estados visibles en espanol, link de pago y webhook de pasarela.
- Citas con disponibilidad por calendario integrado o citas internas + horario operativo.
- Funnel de bienvenida obligatorio, datos iniciales y menus/listas.
- IA con configuracion integral, horarios, autonomia, politicas, escalamiento, modo prueba y publicacion.
- Integraciones nativas limitadas a pagos, calendario, correo/notificaciones y webhooks.
- Retencion indefinida mientras tenant activo y paquete de exportacion al retiro.

## Decisiones sustituidas / aclaradas

- Investigacion inicial sugeria Embedded Signup como flujo principal. El usuario corrigio alcance: V1 conserva configuracion tecnica actual; V2 tendra popup Meta.
- La disponibilidad de citas sin calendario se habia descrito como "horario del modulo Citas"; el usuario aclaro que el horario operativo es unico y compartido para IA y Citas.

## Acciones antes del pase de revisión

- Limpiar texto de Discovery ya resuelto.
- Reubicar FRs tardios en secciones correctas manteniendo IDs estables.
