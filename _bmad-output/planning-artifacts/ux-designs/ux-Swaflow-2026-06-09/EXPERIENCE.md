---
name: SWAFLOW
status: final
sources:
  - DESIGN.md
  - imports/swa-tech-logo-reference.md
  - ../../prds/prd-Swaflow-2026-06-08/prd.md
  - ../../../../frontend/src/App.tsx
updated: 2026-06-10
---

# SWAFLOW - Experience Spine

Este spine gana en conflicto contra cualquier mockup, screenshot o borrador de implementacion. La identidad visual y tokens viven en `DESIGN.md`; este documento gobierna estructura, comportamiento, estados, interacciones, accesibilidad y flujos.

## Foundation

Web SaaS de escritorio construida con React, Vite, TypeScript, Tailwind CSS, Zustand, TanStack Query y lucide-react. El frontend actual esta concentrado en `frontend/src/App.tsx`, asi que la primera pasada de implementacion debe mantener comportamiento estable y extraer/estandarizar componentes solo donde reduzca complejidad real.

La experiencia es para admins de tenant y operadores comerciales que gestionan ventas por WhatsApp, asistencia IA, inventario, ordenes, citas, funnels, integraciones y ajustes de cuenta. `DESIGN.md` define la identidad Swa Tech, reemplaza la paleta verde rechazada y fija dark mode como tema por defecto.

Postura principal: consola operacional. El producto debe abrir directo al trabajo, no a una superficie de marketing.

No hay version mobile en este ciclo. La experiencia se diseña y valida para desktop/laptop solamente.

## Information Architecture

La navegacion sigue siendo una sola app, pero debe agruparse para reducir complejidad percibida.

| Grupo | Superficie | Acceso | Proposito |
|---|---|---|---|
| Operacion | Dashboard | Top del sidebar / post-login | Salud ejecutiva y operacional de ventas conversacionales. |
| Operacion | Inbox | Top del sidebar / actividad de dashboard / notificacion | Workspace diario de chats WhatsApp, handoff humano, funnel, ordenes y citas. |
| Comercio | Productos | Grupo sidebar | Catalogo sincronizado desde Meta y base visible de productos para IA. |
| Comercio | Inventario | Grupo sidebar | Stock, cantidad reservada y disponibilidad operativa. |
| Comercio | Ordenes | Grupo sidebar / contexto de Inbox | Ordenes, links de pago, estado de pago y expiracion. |
| Comercio | Citas | Grupo sidebar / contexto de Inbox | Citas creadas manualmente o desde conversaciones. |
| Automatizacion | IA | Grupo sidebar | Configuracion del agente, guardrails, FAQs, pruebas y publicacion. |
| Automatizacion | Funnels | Grupo sidebar / contexto de Inbox | Etapas comerciales y reglas de clasificacion IA/manual. |
| Automatizacion | WhatsApp | Grupo sidebar / panel de salud | Cloud API, webhook, verificacion y prueba de cuenta. |
| Automatizacion | Integraciones | Grupo sidebar / panel de salud | Pagos, calendario, email y webhooks salientes. |
| Administracion | Ajustes | Parte baja del sidebar / menu cuenta | Tenant, usuarios, permisos, password y modo de negocio. |

Sidebar desktop:

- Siempre visible en `lg+` y fijo/sticky mientras la pagina principal scrolla.
- Usa labels agrupados y estados activos compactos de `DESIGN.md`.
- Dashboard e Inbox quedan anclados arriba.
- Ajustes puede ir abajo como area de cuenta/admin.
- El panel izquierdo no cambia de posicion entre modulos; lo que cambia es el contenido central o derecho de cada vista.

Movil:

- Fuera de alcance en este ciclo.
- No se diseña ni valida version mobile.

## Voice and Tone

Microcopy en espanol, operacional y directa. La voz de marca vive en `DESIGN.md`; el copy de producto ayuda a actuar rapido.

| Do | Don't |
|---|---|
| "12 chats requieren accion" | "Tu equipo esta conquistando ventas" |
| "IA activa en esta conversacion" | "Bot encendido" sin contexto |
| "Pago pendiente. Link vence en 42 min." | "Esperando" solo |
| "No hay conversaciones activas" | "Aun no pasa nada por aqui!" |
| "No se pudo enviar. Reintentar." | "Error desconocido" |

Usar nombres de estado en espanol para usuarios, aunque los codigos internos esten en ingles.

## Component Patterns

Patrones de comportamiento. La visual vive en `DESIGN.md.Components`.

| Componente | Uso | Reglas de comportamiento |
|---|---|---|
| Sidebar agrupado | Shell global | Agrupa nav items. El activo tiene acento izquierdo persistente. La pagina actual se anuncia en el header. |
| Page header | Shell global | Muestra titulo, subtitulo, busqueda global, tema, notificaciones y cuenta. No sobrecargar con acciones especificas de pagina; esas viven dentro de la superficie. |
| KPI card | Dashboard | Muestra label, valor principal, delta de periodo y mini trend. Click navega al modulo fuente cuando el dato lo permite. |
| Chart panel | Dashboard | Usa Recharts para line charts, bar charts, areas, ejes, leyendas y tooltips. Debe tener labels reales, rango de fecha y estados vacio/cargando. |
| Activity list | Dashboard | Muestra conversaciones, ordenes, citas o eventos recientes. Click navega a la fuente cuando exista id. |
| Conversation list item | Inbox | Click abre chat. Muestra contacto, telefono, ultimo mensaje, no leidos, responsable, estado IA/humano, funnel/paso y tiempo. El seleccionado persiste visualmente. |
| Chat thread | Inbox | Mensajes muestran tipo de emisor, timestamp y metadata de entrega/fuente cuando exista. Auto-scroll solo si el operador ya estaba cerca del fondo. |
| Message composer | Inbox | Envio por boton. El comportamiento de `Enter` debe decidirse explicitamente despues. Deshabilitar al enviar. Mantener draft si falla. |
| Handoff actions | Inbox | Botones de "Retomar humano" y "Asignar a IA" visibles en el header del chat o rail de acciones. Deben reflejar el estado actual de la conversacion y no depender de hover. |
| Status badge | Todos | Mapea codigos internos a labels en espanol. El tono sigue estado semantico, no color arbitrario por modulo. |
| Data table | Productos, Ordenes, Citas | Escaneable: columnas estables, badges compactos, acciones de fila al final, estado vacio bajo header. |
| Notice / Toast | Global | Error usa `role="alert"`, success usa `role="status"`. Mensajes cortos y accionables. |

## State Patterns

| Estado | Superficie | Tratamiento |
|---|---|---|
| Carga fria | Global | Panel centrado de validacion con `{components.card}` y marca Swa Tech. Copy: "Validando sesion". |
| Dashboard sin datos | Dashboard | Mostrar KPIs en cero y checklist de setup/salud. No mostrar graficas falsas. |
| Dashboard cargando | Dashboard | Skeletons de KPI y paneles de grafica con el mismo layout final. |
| Dashboard desactualizado | Dashboard | Timestamp pequeno: "Actualizado hace N min". Refresh manual disponible. |
| Atencion requerida | Dashboard | Se muestra como bloque independiente debajo de Salud del sistema, no mezclado con la card de salud. |
| Sin conversaciones | Inbox | Estado vacio en lista: "No hay conversaciones activas". El detalle muestra siguiente accion de setup si WhatsApp no esta conectado. |
| Conversacion no seleccionada | Inbox | Prompt en detalle: "Selecciona una conversacion". En desktop, rail contextual oculto hasta seleccionar. |
| Enviando mensaje | Inbox | Composer deshabilitado, texto inline "Enviando". Draft visible hasta exito. |
| Envio fallido | Inbox | Error inline junto al composer: "No se pudo enviar. Reintentar." Draft preservado. |
| IA activa | Rail de Inbox | Mostrar estado, ultima decision de handoff si existe y accion "Pasar a humano". |
| Handoff humano | Rail de Inbox | Mostrar responsable y accion para reactivar IA donde aplique. |
| Actualizando funnel | Rail de Inbox | Deshabilitar selectores afectados y mostrar "Actualizando funnel...". |
| Pago pendiente | Inbox, Ordenes | Mostrar link, expiracion, copiar/abrir y warning cuando se acerque vencimiento. Nunca insinuar pagado sin backend. |
| Permiso denegado | Cualquier modulo | Ocultar acciones no autorizadas cuando sea posible. Si hay acceso directo, mostrar estado bloqueado conciso. |
| Offline/realtime desconectado | Global / Inbox | Banner o estado en header: "Conexion en tiempo real pausada". Refresh manual disponible. |

## Interaction Primitives

- Click/tap para navegar y actuar.
- Busqueda global permanece en el header; una futura command palette puede reutilizarla.
- `Esc` cierra dialogos, menus y limpia busqueda transitoria cuando este enfocada.
- Tab order va de sidebar a header y contenido de pagina.
- Hover puede revelar acciones secundarias en desktop, pero toda accion debe existir tambien en touch.
- Acciones de refresh usan icono lucide `RefreshCw` con title/label accesible y texto visible cuando no sea obvio.
- Botones solo-icono requieren `title` o accessible label.
- Acciones destructivas requieren confirmacion cuando afectan datos productivos.

Prohibido en esta pasada:

- Hero decorativo tipo landing dentro de la app.
- Cards anidadas.
- Acciones criticas de chat solo por hover.
- Infinite scroll para tablas operativas sin limite/cargando claro.
- Fondos con gradiente morado como superficie principal de la app.

## Accessibility Floor

El contraste visual vive en `DESIGN.md`. Piso de accesibilidad conductual:

- Objetivo WCAG 2.2 AA para superficies de app.
- Focus ring usa `{colors.focus-ring}` y debe verse en fondos claros y oscuros.
- Todo boton solo-icono necesita nombre accesible.
- El hilo de chat expone emisor, texto y timestamp en orden de lectura.
- Contadores no leidos no dependen solo del color.
- Graficas de Dashboard necesitan alternativa textual: titulo, periodo, resumen de valor y labels de leyenda.
- Errores de formulario aparecen junto al campo/composer y usan `role="alert"` cuando bloquean.
- Targets tactiles de al menos 40px en web.
- No truncar labels criticos como estado de pago, paso de funnel o alertas de inventario sin tooltip/title.

## Responsive & Platform

| Breakpoint | Comportamiento |
|---|---|
| `xl` y mayor | Dashboard usa fila KPI + grafica de ancho completo. Inbox usa lista + hilo, sin rail derecho. |
| `lg` | Sidebar visible. Inbox mantiene lista + hilo a ancho completo. |
| `md` | Fuera de alcance en este ciclo. |
| `< md` | Fuera de alcance en este ciclo. |

El producto es web de escritorio en este ciclo. No se define comportamiento mobile hasta una iteracion posterior.

## Inspiration & Anti-patterns

Inspiraciones utiles:

- **Intercom / Zendesk** para lista de conversaciones, hilo y contexto del cliente.
- **Linear** para disciplina de navegacion agrupada y busqueda de baja friccion.
- **Stripe** para densidad seria de KPIs, tablas y estados claros.
- **WhatsApp Business** para direccion de mensajes, handoff humano/IA y recencia de chats.

Rechazado:

- Estilo de chat consumidor con burbujas gigantes y metadata debil.
- Dashboard admin generico con graficas falsas sin conexion a acciones.
- Tratamiento cyberpunk neon en todas las superficies.
- Verde/teal como color primario de marca.

## Mejoras recomendadas adicionales

1. Agregar banda de setup/salud en Dashboard: WhatsApp conectado, IA publicada, catalogo sincronizado, pagos activos, calendario conectado.
2. Agregar cola "Atencion requerida" en Dashboard: chats no leidos, pagos pendientes, bajo stock, proximas citas, fallas de integracion.
3. Agregar filtros en Dashboard e Inbox: rango de fecha, responsable, estado, funnel, producto.
4. Agregar indicador de modo de negocio del tenant en Ajustes y opcionalmente header: productos, citas o mixto.
5. Agregar sistema reusable de estados vacio/cargando/error para que cada modulo se sienta terminado.
6. Convertir dark mode a sistema real de tokens y hacerlo el fallback por defecto cuando no exista preferencia guardada.
7. Extraer primitivos UI desde `App.tsx` antes de que crezca el rediseno: Button, Card, Badge, Table, PageHeader, Sidebar, Input, Notice.
8. Normalizar naming de marca: reemplazar el texto actual "Swatek Flow AI" por `SWAFLOW`.
9. Usar la tipografia Sora definida por el concepto del logo como familia tipografica principal de la aplicacion.

## Key Flows

### Flow 1 - Revision operacional de la manana (Laura, admin de tenant, 8:20am)

1. Laura abre SWAFLOW en su laptop.
2. Dashboard carga cuatro KPI: chats que requieren accion, pagos pendientes, ventas confirmadas, citas de hoy.
3. Ve la banda de salud: WhatsApp conectado, IA activa, catalogo sincronizado ayer, pagos activos.
4. La grafica principal muestra chats y ventas por dia para el rango seleccionado. Un panel lateral lista "Atencion requerida".
5. Laura hace click en "7 chats sin leer".
6. **Climax:** Inbox abre filtrado a chats no leidos, preservando el contexto operacional de Dashboard. Laura empieza a trabajar sin buscar entre modulos.

Falla: datos de grafica no disponibles. Dashboard mantiene KPIs y muestra estado vacio: "No pudimos cargar esta grafica. Reintentar." No hay valores falsos.

### Flow 2 - Asesor toma un chat de venta (Mateo, asesor comercial, medio dia)

1. Mateo abre Inbox.
2. La lista esta ordenada por actividad reciente y destaca no leidos.
3. Selecciona "Ana Martinez". El hilo abre al centro y el rail derecho muestra cliente, estado IA, paso de funnel, orden pendiente y accion de cita.
4. La IA esta activa, pero Ana pide una condicion especial de envio. Mateo hace click en "Pasar a humano".
5. El rail actualiza responsable y estado. El composer queda como accion principal.
6. Mateo responde manualmente.
7. **Climax:** El hilo muestra claramente la transicion de IA a Mateo y la lista ahora dice "Humano - Mateo", evitando doble gestion.

Falla: envio fallido. El draft queda en composer y el error inline dice "No se pudo enviar. Reintentar."

### Flow 3 - Seguimiento de pago desde chat (Diana, operadora, tarde)

1. Diana entra a Inbox desde alerta de Dashboard: "3 pagos por vencer".
2. La conversacion seleccionada muestra pago pendiente en el rail con tiempo de expiracion.
3. Abre la accion de pago, copia el link y envia recordatorio corto.
4. Luego backend marca la orden como pagada via webhook.
5. **Climax:** El rail del chat y Ordenes muestran "Pagado" desde estado backend, y Dashboard actualiza ventas confirmadas por refresh/realtime.

Falla: pago expira. El rail cambia a expirado/seguimiento pendiente. UI no confirma pago, no extiende inventario y no genera nuevo link sin servicio backend.

### Flow 4 - Admin revisa readiness de IA (Camilo, owner, antes de onboarding)

1. Camilo abre Dashboard y ve banda de salud con "IA requiere revision".
2. Abre IA desde la banda.
3. IA muestra completitud de configuracion: identidad, guardrails, FAQs, horario, funnel, plantillas interactivas y modo prueba.
4. Corrige campos faltantes y corre una clasificacion de muestra.
5. **Climax:** La banda de salud cambia a "IA lista para operar", e Inbox puede mostrar estado IA con mas confianza por conversacion.

Falla: la API de clasificacion falla. UI muestra resultado fallback separado como local/fallback, no como confianza productiva.
