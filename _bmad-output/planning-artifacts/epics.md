---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
inputDocuments:
  - _bmad-output/project-context.md
  - _bmad-output/planning-artifacts/prds/prd-Swaflow-2026-06-08/prd.md
  - _bmad-output/planning-artifacts/architecture/swaflow-frontend-architecture.md
---

# Swaflow - Desglose de épicas

## Resumen general

This document provides the complete epic y story breakdown for Swaflow, decomposing the requirements from the PRD, UX Design if it exists, y Architecture requirements into implementable stories.

## Inventario de requisitos

### Requisitos funcionales

- **FR-001:** El sistema debe mostrar tarjetas resumen con chats totales, chats pendientes por leer, ventas y agendamientos del tenant.
- **FR-002:** El sistema debe mostrar graficos de ventas, agendamientos y chats en el tiempo.
- **FR-003:** El sistema debe permitir filtrar las metricas del Dashboard por rango de fechas.
- **FR-004:** El sistema debe permitir filtrar las metricas del Dashboard por asesor/usuario cuando existan usuarios adicionales en el tenant.
- **FR-005:** El sistema debe permitir filtrar las metricas del Dashboard por estado de chat.
- **FR-006:** El sistema debe permitir filtrar las metricas del Dashboard por funnel o etapa cuando la conversacion tenga clasificacion comercial.
- **FR-007:** El sistema debe permitir filtrar las metricas del Dashboard por producto cuando existan ordenes o interacciones asociadas a productos.
- **FR-008:** El sistema debe respetar aislamiento multi-tenant en todos los calculos del Dashboard; ningun usuario debe ver metricas de otra empresa.
- **FR-009:** El sistema debe mostrar un listado de conversaciones del tenant con contacto, ultimo mensaje, fecha/hora de ultima actividad, estado, conteo de no leidos y clasificacion de funnel cuando exista.
- **FR-010:** El sistema debe mostrar el detalle de una conversacion con el historial de mensajes entrantes, respuestas de IA, mensajes de asesores, mensajes interactivos y eventos relevantes.
- **FR-011:** El sistema debe permitir enviar mensajes manuales desde el Inbox usando la cuenta WhatsApp conectada del tenant.
- **FR-012:** El sistema debe permitir desactivar la intervencion de IA por conversacion individual.
- **FR-013:** La desactivacion de IA por conversacion debe ser reversible desde el mismo contexto operativo del chat.
- **FR-014:** Cuando la IA se reactive en una conversacion, debe poder usar el historial de mensajes del humano y del cliente como contexto para continuar de forma natural, respetando reglas del agente, catalogo, inventario y seguridad.
- **FR-015:** El sistema debe permitir agendar una cita desde una conversacion, conservando relacion entre cita, contacto y chat.
- **FR-016:** El sistema debe mostrar el funnel y etapa asignados a la conversacion cuando hayan sido inferidos por IA.
- **FR-017:** El sistema debe permitir que un usuario autorizado seleccione o ajuste manualmente el funnel y etapa de una conversacion.
- **FR-018:** El sistema debe actualizar en tiempo real, o de forma equivalente perceptible, mensajes nuevos, conteos no leidos y cambios de estado relevantes del Inbox.
- **FR-019:** Las acciones del Inbox deben respetar permisos por usuario y aislamiento por tenant.
- **FR-020:** Si el tenant solo tiene usuario admin activo, el admin debe poder gestionar todos los chats del tenant sin asignacion adicional obligatoria.
- **FR-021:** Si el tenant tiene exactamente un usuario adicional activo, el sistema debe asignar todos los chats a ese usuario por defecto, salvo ajuste manual del admin.
- **FR-022:** Si el tenant tiene mas de un usuario adicional activo, los chats no asignados deben poder ser tomados por un usuario.
- **FR-023:** Cuando un usuario toma un chat, el chat debe quedar asignado a ese usuario y no debe estar disponible para que otro usuario lo gestione simultaneamente.
- **FR-024:** El admin del tenant debe poder asignar manualmente chats a un usuario especifico.
- **FR-025:** El Inbox debe permitir distinguir chats disponibles, chats asignados al usuario actual y chats asignados a otros usuarios, respetando los permisos del usuario autenticado.
- **FR-026:** El admin del tenant debe poder reasignar un chat a otro usuario aunque el chat ya haya sido tomado o este asignado, dejando registro del cambio de responsable.
- **FR-172:** El admin debe poder desactivar la autoasignacion por defecto cuando el tenant tenga exactamente un usuario adicional activo.
- **FR-173:** Si la autoasignacion esta desactivada, los chats nuevos deben quedar disponibles/no asignados hasta que un usuario los tome o el admin los asigne manualmente.
- **FR-027:** El sistema debe permitir configurar una cuenta WhatsApp Cloud API por tenant con los datos tecnicos requeridos por la integracion actual.
- **FR-028:** El sistema debe mostrar la URL de callback/webhook, verify token, version de Graph API y estado de configuracion necesario para completar la conexion en Meta.
- **FR-029:** El sistema debe almacenar tokens y credenciales de WhatsApp de forma cifrada y nunca exponerlos en texto plano despues de guardarlos.
- **FR-030:** El sistema debe permitir probar la cuenta WhatsApp configurada para validar que puede enviar y recibir mediante Cloud API.
- **FR-031:** El sistema debe recibir mensajes entrantes desde el webhook de WhatsApp y asociarlos al tenant, contacto y conversacion correctos.
- **FR-032:** El sistema debe enviar mensajes salientes desde Inbox, IA o acciones autorizadas usando la cuenta WhatsApp del tenant.
- **FR-033:** El sistema debe procesar mensajes interactivos y respuestas de clientes preservando metadata suficiente para que Inbox e IA entiendan el contexto.
- **FR-034:** El sistema debe validar firma o secreto de webhooks de WhatsApp cuando la configuracion disponible lo permita.
- **FR-035:** El sistema debe contemplar para V2 un flujo de conexion menos tecnico basado en autenticacion con popup de Meta/Embedded Signup.
- **FR-036:** El sistema debe sincronizar productos existentes desde el catalogo Meta conectado al tenant.
- **FR-037:** El sistema debe guardar localmente los datos necesarios para operar ventas conversacionales: nombre, descripcion, precio, moneda, estado, catalogo Meta, retailer ID y metadata relevante devuelta por Meta.
- **FR-038:** El sistema debe permitir visualizar el catalogo sincronizado desde Meta dentro de Swaflow.
- **FR-039:** El sistema no debe permitir crear productos nuevos en Swaflow que no existan previamente en Meta.
- **FR-040:** El sistema no debe permitir que la IA ofrezca productos que no esten sincronizados desde Meta y disponibles segun inventario local.
- **FR-041:** El sistema debe advertir claramente cuando el catalogo Meta no este asociado a la WABA activa o cuando Meta permita leer productos pero no permita enviarlos como cards nativas.
- **FR-042:** El sistema debe conservar el `whatsapp_product_retailer_id` para enviar cards nativas de WhatsApp cuando corresponda.
- **FR-043:** El sistema debe manejar errores comunes de Meta con mensajes entendibles para el admin, incluyendo el uso de IDs incorrectos de catalogo o conjuntos de productos.
- **FR-044:** El sistema debe crear o actualizar registros de inventario local solo para productos sincronizados desde Meta.
- **FR-045:** El sistema debe reflejar la disponibilidad base recibida desde Meta para cada producto sincronizado.
- **FR-046:** El sistema debe mostrar, por producto, disponibilidad base, reservas operativas en Swaflow y disponibilidad operativa calculada.
- **FR-047:** La disponibilidad operativa debe calcularse considerando la disponibilidad base de Meta menos las reservas vigentes generadas por ordenes en proceso dentro de Swaflow.
- **FR-048:** El sistema no debe permitir inventario para productos inexistentes en Meta o no sincronizados en el catalogo del tenant.
- **FR-049:** La IA y el Inbox deben usar la disponibilidad operativa para decidir si un producto puede ofrecerse, reservarse o enviarse como card nativa.
- **FR-050:** El sistema debe liberar reservas cuando una orden sea cancelada, expirada o pase a un estado terminal que no requiere retener inventario.
- **FR-051:** El sistema debe descontar o marcar como consumida la reserva cuando una orden sea confirmada como pagada por la pasarela.
- **FR-052:** El sistema debe advertir cuando la disponibilidad de Meta no pueda leerse o sincronizarse, evitando que la IA ofrezca productos con disponibilidad incierta.
- **FR-053:** El sistema debe crear ordenes desde una conversacion cuando exista intencion de compra y datos suficientes para una accion critica.
- **FR-054:** La creacion de una orden debe validar tenant, contacto, conversacion, productos sincronizados desde Meta, disponibilidad operativa, cantidades y moneda.
- **FR-055:** Al crear una orden pendiente de pago, el sistema debe reservar la cantidad correspondiente para evitar sobreventa operativa.
- **FR-056:** El sistema debe generar link de pago mediante la pasarela configurada para el tenant cuando la orden este lista para pago.
- **FR-057:** El sistema debe almacenar y mostrar referencia de pago, link de pago, estado de pago, fecha de vencimiento cuando aplique, total y moneda.
- **FR-058:** El sistema debe actualizar el estado de pago de la orden con base en webhooks validos de la pasarela, no por confirmacion manual de IA o frontend.
- **FR-059:** El sistema debe listar ordenes de la mas reciente a la mas antigua.
- **FR-060:** La vista de Ordenes debe agrupar visualmente las ordenes por mes y anio.
- **FR-061:** El sistema debe mostrar estados visibles en espanol para admin/usuarios, aunque internamente use codigos estables.
- **FR-062:** El sistema debe permitir filtrar ordenes por rango de fechas, estado, cliente/contacto, producto y usuario/conversacion cuando la relacion exista.
- **FR-063:** Cuando una orden sea pagada, el sistema debe registrar el evento de venta, consumir o confirmar la reserva de inventario y reflejar la venta en el Dashboard.
- **FR-064:** Cuando una orden sea cancelada o expirada, el sistema debe liberar reservas y registrar el evento correspondiente.
- **FR-065:** El sistema debe evitar duplicidad o doble procesamiento de webhooks de pago mediante identificadores de referencia/transaccion.
- **FR-153:** Los links de pago deben expirar por defecto a los 120 minutos.
- **FR-154:** El admin debe poder configurar el tiempo de expiracion de links de pago dentro de la configuracion de la integracion de pagos.
- **FR-145:** Cuando un link de pago expire sin confirmacion, el sistema debe permitir seguimiento comercial por IA para preguntar si el cliente desea continuar con el pago, generar un nuevo flujo de pago por backend o agregar otro producto.
- **FR-146:** El seguimiento de pagos expirados no debe confirmar pagos, extender vencimientos ni retener inventario sin pasar por reglas y servicios backend autorizados.
- **FR-178:** La IA debe ejecutar como maximo un seguimiento automatico despues de que expire un link de pago.
- **FR-179:** Si el cliente responde al seguimiento de link expirado, la IA puede continuar el flujo comercial segun reglas del agente y backend.
- **FR-180:** Si el cliente no responde al seguimiento de link expirado, la IA no debe insistir nuevamente de forma automatica en V1.
- **FR-066:** El sistema debe permitir crear citas desde una conversacion por accion de IA cuando el cliente exprese intencion de agendar y existan datos suficientes.
- **FR-067:** El sistema debe permitir crear citas manualmente desde el Inbox por un usuario autorizado.
- **FR-068:** Cada cita debe guardar cliente/contacto, conversacion relacionada cuando exista, fecha, hora, estado, motivo de agendamiento y notas opcionales.
- **FR-069:** Los estados visibles de cita deben mostrarse en espanol para admin/usuarios.
- **FR-070:** El modulo Citas debe listar todas las citas del tenant, independientemente de si existe o no integracion con calendario externo.
- **FR-071:** Si el tenant tiene calendario integrado, el sistema debe intentar sincronizar la cita con el calendario configurado.
- **FR-072:** Si no hay calendario integrado, la cita debe quedar registrada y operable dentro de Swaflow sin bloquear el flujo comercial.
- **FR-073:** El sistema debe permitir filtrar citas por rango de fechas, estado, usuario/asesor, cliente/contacto y origen cuando aplique.
- **FR-074:** El sistema debe reflejar citas creadas o actualizadas en el Dashboard y en el historial/contexto de la conversacion relacionada.
- **FR-075:** La IA no debe confirmar disponibilidad de agenda si no tiene datos suficientes o integracion/reglas configuradas; debe pedir aclaracion o derivar a humano segun reglas del agente.
- **FR-147:** Cuando un cliente solicite una cita, la IA debe preguntar si prefiere horario de manana o tarde antes de proponer opciones.
- **FR-148:** Si el tenant tiene calendario integrado, el sistema debe validar disponibilidad inicial contra ese calendario para proponer citas.
- **FR-149:** Si el tenant no tiene calendario integrado, el sistema debe validar disponibilidad contra las citas internas de Swaflow y el horario operativo compartido del comercio.
- **FR-150:** El sistema debe proponer al cliente tres opciones de agenda posibles con hora, preferiblemente en dias diferentes, segun disponibilidad y preferencia manana/tarde.
- **FR-151:** El sistema debe usar el mismo horario operativo configurado para IA y para validar disponibilidad de citas cuando no exista calendario integrado.
- **FR-152:** El sistema no debe requerir configuraciones de horario duplicadas entre IA y Citas para V1.
- **FR-161:** La duracion por defecto de una cita debe ser 1 hora.
- **FR-162:** El cliente/admin debe poder configurar la duracion de las citas en el modulo Citas.
- **FR-163:** La franja de manana debe interpretarse por defecto como 08:00-12:00.
- **FR-164:** La franja de tarde debe interpretarse por defecto como 14:00-18:00.
- **FR-165:** El sistema debe ofrecer citas como minimo desde el dia siguiente, no para el mismo dia.
- **FR-166:** El sistema debe buscar las tres opciones de agenda dentro de un horizonte maximo de los proximos 7 dias.
- **FR-076:** El sistema debe garantizar que cada tenant tenga un funnel inicial de bienvenida.
- **FR-077:** El funnel de bienvenida debe permitir configurar el mensaje inicial al cliente.
- **FR-078:** El funnel de bienvenida debe permitir configurar datos a capturar del cliente durante la apertura de la conversacion.
- **FR-079:** El admin debe poder crear funnels adicionales para distintos flujos, intenciones, productos, servicios o etapas comerciales.
- **FR-080:** Cada funnel debe permitir definir nombre, descripcion, estado y criterios/caracteristicas de asignacion.
- **FR-081:** Cada funnel debe permitir configurar pasos o apartados personalizables.
- **FR-082:** Cada paso de funnel debe permitir definir prompt/instruccion, objetivos y criterio de transicion.
- **FR-083:** La IA debe iniciar nuevas conversaciones en el funnel de bienvenida, salvo que existan reglas explicitas que indiquen otro punto de entrada.
- **FR-084:** A partir del funnel de bienvenida, la IA debe poder asignar la conversacion a cualquier funnel activo segun intencion del cliente y criterios configurados.
- **FR-085:** El Inbox debe mostrar el funnel y paso actual asignado por IA.
- **FR-086:** Un usuario autorizado debe poder ajustar manualmente el funnel y paso de una conversacion.
- **FR-087:** La asignacion de funnel, automatica o manual, debe quedar disponible para filtros, metricas de Dashboard y contexto de IA.
- **FR-155:** El funnel de bienvenida debe capturar como campos iniciales Nombre, Correo y Ciudad.
- **FR-156:** El sistema debe tomar el telefono del cliente desde el chat de WhatsApp y no pedirlo como campo obligatorio inicial si ya esta disponible.
- **FR-157:** La intencion del cliente debe completarse desde el funnel y la clasificacion conversacional, no como campo manual obligatorio de bienvenida.
- **FR-088:** El sistema debe permitir configurar identidad/nombre del agente.
- **FR-089:** El sistema debe permitir configurar el objetivo comercial del agente, por ejemplo vender, agendar, calificar lead, soporte inicial o derivar a asesor.
- **FR-090:** El sistema debe permitir configurar contexto del negocio, productos/servicios declarados y descripcion comercial del tenant.
- **FR-091:** El sistema debe permitir configurar prompt del sistema, tono, objetivo conversacional y guia conversacional.
- **FR-092:** El sistema debe permitir configurar reglas de seguridad del agente separadas del prompt general.
- **FR-093:** El sistema debe permitir configurar FAQs del tenant y cargarlas desde archivo cuando el formato sea soportado.
- **FR-094:** El sistema debe permitir configurar campos a capturar del cliente, especialmente durante el funnel de bienvenida.
- **FR-095:** El sistema debe permitir configurar plantillas interactivas de WhatsApp, como botones o listas, asociadas a `action_key` y reglas de uso.
- **FR-096:** El sistema debe permitir configurar horario de atencion y comportamiento dentro/fuera de horario.
- **FR-097:** El sistema debe permitir configurar reglas de autonomia que definan que acciones puede ejecutar la IA sin humano y que acciones requieren intervencion.
- **FR-098:** El sistema debe permitir configurar politicas comerciales verificadas, incluyendo envios, garantias, cambios, devoluciones, tiempos y medios de pago.
- **FR-099:** El sistema debe permitir configurar reglas de escalamiento a humano por baja confianza, queja, reclamo, cliente molesto, pago fallido, stock incierto o solicitud explicita.
- **FR-100:** El sistema debe permitir configurar productos o categorias prioritarias, restringidas o que requieren asesor.
- **FR-101:** El sistema debe ofrecer un modo de prueba para simular conversaciones antes de activar cambios de configuracion en produccion.
- **FR-102:** El sistema debe permitir guardar configuracion de IA como borrador y publicar una version activa.
- **FR-103:** La IA debe usar catalogo Meta sincronizado, disponibilidad operativa, FAQs, reglas de seguridad, funnels y contexto reciente de conversacion antes de responder.
- **FR-104:** La IA no debe inventar precios, stock, disponibilidad, links de pago, politicas comerciales, agenda ni confirmaciones de pago.
- **FR-105:** La IA debe pedir aclaracion o escalar a humano cuando la confianza sea baja o falte informacion para una accion critica.
- **FR-106:** El sistema debe impedir que configuraciones del admin desactiven guardrails obligatorios sobre tenant, pagos, inventario, seguridad y no invencion.
- **FR-107:** La configuracion de horario de atencion debe permitir definir un horario para lunes a viernes y un horario diferente para sabado y domingo.
- **FR-108:** La IA debe aplicar el comportamiento configurado para fuera de horario segun el dia y hora local del tenant.
- **FR-109:** El flujo inicial de IA debe poder capturar datos principales del cliente y presentar opciones configurables como comprar producto, consultar productos o agendar cita mediante menus, botones o listas.
- **FR-110:** El sistema debe permitir configurar una pasarela de pagos por tenant para generar links de pago y recibir confirmaciones por webhook, sin quedar limitado como producto a un unico proveedor.
- **FR-111:** El sistema debe cifrar credenciales de pasarela y validar webhooks de pago segun el mecanismo de seguridad del proveedor.
- **FR-112:** El sistema debe permitir configurar una integracion de calendario por tenant para sincronizar citas cuando este disponible.
- **FR-158:** La integracion de calendario V1 debe contemplar Google Calendar y Microsoft Calendar como opciones esperadas por clientes.
- **FR-113:** La ausencia de integracion de calendario no debe bloquear la creacion ni visualizacion de citas dentro de Swaflow.
- **FR-114:** El sistema debe permitir configurar correo/notificaciones para avisos operativos como compra aprobada, cita creada o eventos relevantes.
- **FR-115:** El sistema debe permitir configurar webhooks salientes por tenant para eventos relevantes.
- **FR-116:** Los webhooks salientes deben poder filtrar por tipo de evento, estar activos/inactivos y usar firma o secreto cuando se configure.
- **FR-117:** Las fallas de webhooks salientes o automatizaciones de n8n no deben romper transacciones criticas ya confirmadas en backend.
- **FR-118:** El sistema debe mantener el backend como fuente de verdad para ordenes, pagos, inventario, citas, permisos y estados criticos.
- **FR-119:** Integraciones perifericas como CRM, hojas de calculo, mensajeria interna, reportes avanzados o automatizaciones personalizadas deben resolverse inicialmente por n8n mediante webhooks/eventos, no como integraciones nativas V1.
- **FR-167:** Las pasarelas deben soportarse mediante adaptadores o proveedores configurados/certificados por Swateck, no como integraciones arbitrarias sin contrato.
- **FR-168:** Todo adaptador de pasarela debe implementar un contrato comun que permita crear link de pago, configurar expiracion, validar webhook, mapear estados de pago y manejar idempotencia por referencia/transaccion.
- **FR-169:** El sistema debe impedir activar una pasarela si no cuenta con los datos minimos para validar webhooks y mapear estados de forma confiable.
- **FR-174:** El contrato tecnico detallado para adaptadores de pasarela debe mantenerse en el addendum del PRD y servir como base para arquitectura e implementacion.
- **FR-120:** El sistema debe permitir editar datos basicos de empresa del tenant, incluyendo nombre comercial y datos de contacto relevantes.
- **FR-121:** El sistema debe permitir configurar logo o marca visual del tenant.
- **FR-122:** El sistema debe permitir configurar zona horaria del tenant.
- **FR-123:** El sistema debe permitir configurar moneda principal del tenant para visualizacion y reportes.
- **FR-143:** El sistema debe permitir configurar el modo de negocio del tenant como venta de productos, agendamiento de citas o mixto.
- **FR-144:** Los menus, listas, funnels y comportamiento inicial de IA deben poder adaptarse al modo de negocio configurado para mostrar opciones relevantes como comprar, consultar productos o agendar.
- **FR-124:** El sistema debe permitir cargar una imagen de banner del tenant.
- **FR-125:** El sistema debe permitir cargar una imagen de profile/perfil del tenant.
- **FR-126:** Las imagenes de banner y profile deben poder usarse en la generacion de correos electronicos enviados a clientes.
- **FR-127:** El sistema debe permitir al admin gestionar usuarios adicionales del tenant.
- **FR-128:** Antes o durante la creacion/habilitacion de usuarios adicionales, el sistema debe mostrar un mensaje resaltado indicando que cada usuario adicional tendra costo mensual.
- **FR-129:** El sistema debe permitir al admin habilitar por usuario acceso a modulos restringidos mediante checks, sin cambiar el rol base del usuario.
- **FR-130:** El sistema debe permitir cambio o reseteo de contrasena segun permisos del usuario y reglas de seguridad.
- **FR-131:** El sistema debe impedir que usuarios adicionales gestionen Configuracion salvo que el admin les conceda acceso explicito a ese modulo.
- **FR-132:** El sistema debe aplicar permisos configurados en la navegacion, rutas y acciones de backend, no solo ocultando elementos visuales.
- **FR-133:** El sistema debe crear o mantener un usuario admin principal por tenant.
- **FR-134:** El admin principal del tenant debe tener acceso a todos los modulos V1 de su tenant.
- **FR-135:** El sistema debe permitir usuarios adicionales por tenant.
- **FR-136:** Los usuarios adicionales deben tener acceso por defecto solo a Dashboard, Inbox, Productos, Inventario, Ordenes y Citas.
- **FR-137:** Los usuarios adicionales no deben tener acceso por defecto a WhatsApp, IA, Funnels, Integraciones ni Configuracion.
- **FR-138:** El admin debe poder habilitar acceso a modulos restringidos por usuario mediante checks en Configuracion.
- **FR-139:** Habilitar un modulo restringido a un usuario adicional no debe cambiar su rol base.
- **FR-140:** El sistema debe reconocer un rol superadmin de Swateck con acceso ilimitado a todos los tenants para soporte y operacion interna.
- **FR-141:** El acceso superadmin debe tratarse como excepcion explicita al aislamiento tenant normal y debe quedar sujeto a auditoria.
- **FR-142:** El panel avanzado de SuperUsuario SaaS, incluyendo consumos por tenant y reseteo centralizado de admins, queda fuera de V1 y debe planearse para V2.
- **FR-170:** En V1, Swateck debe crear cada tenant y su admin principal mediante un proceso operativo/admin.
- **FR-171:** El sistema no debe requerir self-service signup de tenants para el lanzamiento V1.
- **FR-159:** Mientras el tenant este activo, el sistema debe conservar de forma indefinida mensajes, eventos, archivos y gestiones realizadas en la plataforma, salvo que una politica posterior indique lo contrario.
- **FR-160:** Cuando un cliente/tenant se retire, Swaflow debe poder entregar un paquete de exportacion con todas las gestiones realizadas en la plataforma.
- **FR-175:** El paquete de exportacion al retiro del tenant debe entregarse como archivo ZIP.
- **FR-176:** El ZIP de exportacion debe incluir un archivo TXT por modulo.
- **FR-177:** Cada TXT de exportacion debe listar las interacciones/gestiones del modulo delimitadas por pipe `|`, con encabezado de columnas.

### NonFunctional Requirements

- **NFR-001:** La navegacion principal y carga de vistas comunes debe responder en menos de 2 segundos bajo condiciones normales de operacion.
- **NFR-002:** Las listas principales como Inbox, Ordenes, Citas, Productos e Inventario deben cargar o refrescar resultados visibles en menos de 3 segundos bajo volumen normal de tenant V1.
- **NFR-003:** El Inbox debe reflejar mensajes nuevos, conteos no leidos y cambios de estado en menos de 2 segundos desde que el backend los procesa, cuando la conexion realtime este activa.
- **NFR-004:** La respuesta automatica de IA por WhatsApp debe apuntar a enviarse dentro de 10 segundos desde la recepcion del mensaje entrante en backend, excluyendo latencias externas de Meta/OpenAI fuera del control directo de Swaflow.
- **NFR-005:** Si la IA no puede responder por error, falta de configuracion o timeout, el sistema debe evitar loops y dejar el chat disponible para gestion humana.
- **NFR-006:** El Dashboard debe cargar metricas iniciales en menos de 5 segundos bajo volumen normal de tenant V1.
- **NFR-007:** Cambios de filtros del Dashboard deben devolver resultados en menos de 5 segundos bajo volumen normal de tenant V1.
- **NFR-008:** Un webhook de pago valido debe reflejar el estado actualizado de la orden en menos de 5 segundos desde que es recibido y validado por backend.
- **NFR-009:** Webhooks salientes y eventos hacia n8n deben ejecutarse de forma auxiliar; su latencia no debe bloquear la respuesta de operaciones criticas al usuario.
- **NFR-010:** Toda consulta o accion sobre datos de negocio debe estar aislada por `company_id` o mecanismo equivalente de tenant.
- **NFR-011:** Cuando un recurso exista en otro tenant, el sistema debe tratarlo como no encontrado para usuarios sin acceso cross-tenant.
- **NFR-012:** El acceso superadmin debe ser una excepcion explicita, limitada a usuarios Swateck autorizados y auditable.
- **NFR-013:** Tokens, llaves privadas, secretos de webhooks, credenciales de pasarela, calendario, correo y WhatsApp deben almacenarse cifrados.
- **NFR-014:** Secretos y tokens no deben exponerse completos en UI, logs, respuestas API, errores ni documentacion generada.
- **NFR-015:** Las rutas autenticadas deben aplicar autorizacion en backend, ademas de cualquier restriccion visual en frontend.
- **NFR-016:** Webhooks publicos deben validar token, firma o secreto cuando el proveedor lo permita.
- **NFR-017:** Pagos deben validarse con firma/secreto del proveedor y manejarse con idempotencia.
- **NFR-018:** La IA debe usar backend, catalogo sincronizado, inventario operativo y configuracion del tenant como fuentes de verdad para acciones comerciales.
- **NFR-019:** La IA no debe ejecutar acciones criticas cuando falten datos requeridos o exista baja confianza.
- **NFR-020:** La IA no debe confirmar pagos, alterar inventario ni modificar estados criticos sin pasar por servicios backend autorizados.
- **NFR-021:** El sistema debe evitar respuestas automatizadas repetitivas o loops cuando fallen OpenAI, WhatsApp o configuracion del agente.
- **NFR-022:** Ordenes, pagos, inventario y citas deben mantener consistencia transaccional en backend.
- **NFR-023:** Reservas de inventario deben liberarse en cancelaciones, expiraciones o estados terminales que no retengan producto.
- **NFR-024:** Mensajes entrantes de WhatsApp deben manejar duplicados mediante identificadores externos cuando Meta los provea.
- **NFR-025:** Operaciones criticas no deben depender de n8n ni de webhooks salientes para confirmarse.
- **NFR-026:** Fallas de integraciones auxiliares deben registrarse y hacerse visibles para soporte/admin sin revertir transacciones ya confirmadas.
- **NFR-027:** El sistema debe registrar eventos relevantes de negocio como mensajes recibidos/enviados, cambios de estado de orden, pagos, citas, asignaciones de chat y cambios de configuracion critica.
- **NFR-028:** Reasignaciones de chat hechas por admin deben quedar registradas con usuario, fecha/hora y nuevo responsable.
- **NFR-029:** Cambios de permisos, integraciones, credenciales, IA y funnels deben quedar disponibles para auditoria operativa.
- **NFR-030:** Datos personales de contactos y conversaciones deben limitarse al uso operativo del tenant y no compartirse entre tenants.
- **NFR-031:** El PRD V1 debe contemplar una politica configurable o documentada de retencion de mensajes, eventos, archivos y gestiones. La politica V1 es retencion indefinida mientras el tenant este activo.
- **NFR-032:** Activos de marca cargados por el tenant, como banner y profile, deben almacenarse de forma asociada al tenant y no estar disponibles para otros tenants.
- **NFR-033:** El sistema debe exponer una verificacion de salud backend para monitoreo operativo.
- **NFR-034:** La perdida temporal de OpenAI no debe impedir gestion humana del Inbox.
- **NFR-035:** La perdida temporal de calendario externo no debe impedir crear citas internas en Swaflow.
- **NFR-036:** La perdida temporal de webhooks salientes/n8n no debe impedir crear ordenes, confirmar pagos recibidos por pasarela, gestionar inventario o operar conversaciones.

### Additional Requirements

- La aplicacion de frontend debe seguir siendo una superficie React/Vite unica, sin introducir un router nuevo en esta fase.
- Debe preservarse el estado y utilidades existentes: `Zustand`, `api<T>()`, `swaflow_theme` y `swaflow_active_page`.
- El dark mode debe permanecer como valor por defecto cuando no exista preferencia guardada.
- Los tokens de Tailwind deben ser semanticos; `styles.css` debe resolver dark/light mode y fallback visual.
- La identidad de marca debe moverse a acentos magenta y violeta, con neutros profesionales; el verde/teal deja de ser color de marca.
- Dashboard puede usar Recharts sin reescribir toda la superficie de frontend.
- Inbox debe modelarse como un workspace de tres zonas en desktop, con lista de conversaciones, hilo de mensajes y rail contextual de acciones.
- No se deben introducir datos falsos o mocks para contenido operativo.

### UX Design Requirements

- No se encontró un documento UX independiente entre los artefactos analizados.

### FR Coverage Map

FR27: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR28: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR29: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR30: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR35: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR76: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR77: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR78: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR79: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR80: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR81: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR82: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR83: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR84: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR85: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR86: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR87: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR88: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR89: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR90: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR91: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR92: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR93: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR94: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR95: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR96: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR97: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR98: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR99: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR100: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR101: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR102: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR103: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR104: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR105: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR106: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR107: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR108: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR109: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR110: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR111: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR112: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR113: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR114: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR115: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR116: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR117: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR118: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR119: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR120: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR121: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR122: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR123: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR124: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR125: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR126: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR127: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR128: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR129: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR130: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR131: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR132: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR133: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR134: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR135: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR136: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR137: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR138: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR139: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR143: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR144: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR155: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR156: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR157: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR170: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR171: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR172: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR173: Epic 1 - Base del Tenant, Roles y Configuracion del Asistente
FR9: Epic 2 - Inbox y Operacion Conversacional
FR10: Epic 2 - Inbox y Operacion Conversacional
FR11: Epic 2 - Inbox y Operacion Conversacional
FR12: Epic 2 - Inbox y Operacion Conversacional
FR13: Epic 2 - Inbox y Operacion Conversacional
FR14: Epic 2 - Inbox y Operacion Conversacional
FR15: Epic 2 - Inbox y Operacion Conversacional
FR16: Epic 2 - Inbox y Operacion Conversacional
FR17: Epic 2 - Inbox y Operacion Conversacional
FR18: Epic 2 - Inbox y Operacion Conversacional
FR19: Epic 2 - Inbox y Operacion Conversacional
FR20: Epic 2 - Inbox y Operacion Conversacional
FR21: Epic 2 - Inbox y Operacion Conversacional
FR22: Epic 2 - Inbox y Operacion Conversacional
FR23: Epic 2 - Inbox y Operacion Conversacional
FR24: Epic 2 - Inbox y Operacion Conversacional
FR25: Epic 2 - Inbox y Operacion Conversacional
FR26: Epic 2 - Inbox y Operacion Conversacional
FR31: Epic 2 - Inbox y Operacion Conversacional
FR32: Epic 2 - Inbox y Operacion Conversacional
FR33: Epic 2 - Inbox y Operacion Conversacional
FR34: Epic 2 - Inbox y Operacion Conversacional
FR36: Epic 3 - Catalogo e Inventario Comercial
FR37: Epic 3 - Catalogo e Inventario Comercial
FR38: Epic 3 - Catalogo e Inventario Comercial
FR39: Epic 3 - Catalogo e Inventario Comercial
FR40: Epic 3 - Catalogo e Inventario Comercial
FR41: Epic 3 - Catalogo e Inventario Comercial
FR42: Epic 3 - Catalogo e Inventario Comercial
FR43: Epic 3 - Catalogo e Inventario Comercial
FR44: Epic 3 - Catalogo e Inventario Comercial
FR45: Epic 3 - Catalogo e Inventario Comercial
FR46: Epic 3 - Catalogo e Inventario Comercial
FR47: Epic 3 - Catalogo e Inventario Comercial
FR48: Epic 3 - Catalogo e Inventario Comercial
FR49: Epic 3 - Catalogo e Inventario Comercial
FR50: Epic 3 - Catalogo e Inventario Comercial
FR51: Epic 3 - Catalogo e Inventario Comercial
FR52: Epic 3 - Catalogo e Inventario Comercial
FR53: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR54: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR55: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR56: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR57: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR58: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR59: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR60: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR61: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR62: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR63: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR64: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR65: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR145: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR146: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR153: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR154: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR167: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR168: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR169: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR174: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR178: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR179: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR180: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR66: Epic 5 - Citas y Calendario
FR67: Epic 5 - Citas y Calendario
FR68: Epic 5 - Citas y Calendario
FR69: Epic 5 - Citas y Calendario
FR70: Epic 5 - Citas y Calendario
FR71: Epic 5 - Citas y Calendario
FR72: Epic 5 - Citas y Calendario
FR73: Epic 5 - Citas y Calendario
FR74: Epic 5 - Citas y Calendario
FR75: Epic 5 - Citas y Calendario
FR147: Epic 5 - Citas y Calendario
FR148: Epic 5 - Citas y Calendario
FR149: Epic 5 - Citas y Calendario
FR150: Epic 5 - Citas y Calendario
FR151: Epic 5 - Citas y Calendario
FR152: Epic 5 - Citas y Calendario
FR158: Epic 5 - Citas y Calendario
FR161: Epic 5 - Citas y Calendario
FR162: Epic 5 - Citas y Calendario
FR163: Epic 5 - Citas y Calendario
FR164: Epic 5 - Citas y Calendario
FR165: Epic 5 - Citas y Calendario
FR166: Epic 5 - Citas y Calendario
FR1: Epic 6 - Dashboard y Visibilidad Operativa
FR2: Epic 6 - Dashboard y Visibilidad Operativa
FR3: Epic 6 - Dashboard y Visibilidad Operativa
FR4: Epic 6 - Dashboard y Visibilidad Operativa
FR5: Epic 6 - Dashboard y Visibilidad Operativa
FR6: Epic 6 - Dashboard y Visibilidad Operativa
FR7: Epic 6 - Dashboard y Visibilidad Operativa
FR8: Epic 6 - Dashboard y Visibilidad Operativa
FR140: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR141: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR142: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR159: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR160: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR175: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR176: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR177: Epic 7 - Superadmin, Auditoria y Retiro del Tenant


## Lista de épicas

### Epic 1: Base del Tenant, Roles y Configuracion del Asistente
El tenant queda preparado para operar con identidad, usuarios, permisos, horarios, WhatsApp, IA, funnels e integraciones, de forma que el admin pueda dejar la cuenta lista para ventas conversacionales sin depender de configuraciones dispersas.
**FR cubiertos:** FR027, FR028, FR029, FR030, FR035, FR076, FR077, FR078, FR079, FR080, FR081, FR082, FR083, FR084, FR085, FR086, FR087, FR088, FR089, FR090, FR091, FR092, FR093, FR094, FR095, FR096, FR097, FR098, FR099, FR100, FR101, FR102, FR103, FR104, FR105, FR106, FR107, FR108, FR109, FR110, FR111, FR112, FR113, FR114, FR115, FR116, FR117, FR118, FR119, FR120, FR121, FR122, FR123, FR124, FR125, FR126, FR127, FR128, FR129, FR130, FR131, FR132, FR133, FR134, FR135, FR136, FR137, FR138, FR139, FR143, FR144, FR155, FR156, FR157, FR170, FR171, FR172, FR173

### Epic 2: Inbox y Operacion Conversacional
Los usuarios del tenant pueden recibir, leer, responder, asignar y clasificar conversaciones en un Inbox realtime, con handoff humano y control de contexto para continuar la atencion sin perder trazabilidad.
**FR cubiertos:** FR009, FR010, FR011, FR012, FR013, FR014, FR015, FR016, FR017, FR018, FR019, FR020, FR021, FR022, FR023, FR024, FR025, FR026, FR031, FR032, FR033, FR034

### Epic 3: Catalogo e Inventario Comercial
El tenant sincroniza productos desde Meta, visualiza su catalogo y opera disponibilidad y reservas con stock real, para que la IA y el Inbox solo ofrezcan productos validos y disponibles.
**FR cubiertos:** FR036, FR037, FR038, FR039, FR040, FR041, FR042, FR043, FR044, FR045, FR046, FR047, FR048, FR049, FR050, FR051, FR052

### Epic 4: Ordenes, Pagos y Seguimiento Comercial
El tenant convierte conversaciones en ordenes, genera links de pago, confirma cobros por webhook, libera o consume inventario segun el estado, y gestiona seguimiento de expiraciones sin romper la verdad del backend.
**FR cubiertos:** FR053, FR054, FR055, FR056, FR057, FR058, FR059, FR060, FR061, FR062, FR063, FR064, FR065, FR145, FR146, FR153, FR154, FR167, FR168, FR169, FR174, FR178, FR179, FR180

### Epic 5: Citas y Calendario
El tenant agenda citas desde conversaciones o de forma manual, valida disponibilidad con o sin calendario externo y mantiene las citas visibles y operables dentro de Swaflow.
**FR cubiertos:** FR066, FR067, FR068, FR069, FR070, FR071, FR072, FR073, FR074, FR075, FR147, FR148, FR149, FR150, FR151, FR152, FR158, FR161, FR162, FR163, FR164, FR165, FR166

### Epic 6: Dashboard y Visibilidad Operativa
El admin y usuarios autorizados obtienen una lectura rapida del estado comercial del tenant mediante metricas, graficas y filtros que reflejan actividad real sin mezclar datos entre empresas.
**FR cubiertos:** FR001, FR002, FR003, FR004, FR005, FR006, FR007, FR008

### Epic 7: Superadmin, Auditoria y Retiro del Tenant
Swateck puede operar soporte interno con acceso superadmin auditado, y cuando un tenant se retira el sistema conserva y exporta sus gestiones de forma trazable y completa.
**FR cubiertos:** FR140, FR141, FR142, FR159, FR160, FR175, FR176, FR177

## Epic 1: Base del Tenant, Roles y Configuracion del Asistente

### Historia 1.1: Configurar perfil base del tenant
Como admin principal del tenant,
Quiero editar los datos basicos y operativos de mi empresa,
Para que la plataforma refleje correctamente la identidad administrativa del tenant.

**Criterios de aceptación:**

**Dado** que el admin principal esta autenticado en Configuracion
**Cuando** abre la vista de perfil del tenant
**Entonces** el sistema muestra los datos actuales de la empresa y no inventa valores faltantes

**Dado** que el admin edita nombre comercial, datos de contacto, moneda, zona horaria y modo de negocio
**Cuando** guarda los cambios
**Entonces** el sistema persiste la informacion en el tenant correcto y la vuelve a mostrar al recargar

**Dado** que otro tenant o un usuario sin acceso intenta leer o modificar esa configuracion
**Cuando** llega al backend
**Entonces** el sistema responde `404` para mantener el aislamiento multi-tenant

**Dado** que el tenant no ha cargado un campo
**Cuando** se renderiza la UI
**Entonces** se muestra un estado vacio o placeholder honesto, nunca datos falsos

**FR cubiertos:** FR120, FR122, FR123, FR143, FR144

### Historia 1.2: Gestionar branding visual del tenant
Como admin principal del tenant,
Quiero configurar los activos visuales de mi empresa,
Para que la plataforma y las comunicaciones operativas usen la marca correcta del tenant.

**Criterios de aceptación:**

**Dado** que el admin principal esta autenticado en Configuracion
**Cuando** carga o actualiza logo, banner y profile visual
**Entonces** el sistema guarda los assets asociados solo al `company_id` del tenant

**Dado** que otro tenant intenta leer o modificar esos activos
**Cuando** llega al backend
**Entonces** el sistema responde `404` y no expone recursos entre empresas

**Dado** que el tenant tiene assets configurados
**Cuando** se generan correos operativos o se renderizan vistas asociadas
**Entonces** los assets guardados pueden reutilizarse sin introducir mocks ni datos de otra empresa

**Dado** que el tenant no ha cargado un asset
**Cuando** se renderiza la UI
**Entonces** se muestra un placeholder honesto o estado vacio

**FR cubiertos:** FR124, FR125, FR126

### Historia 1.3: Administrar usuarios, roles y permisos del tenant
Como admin principal del tenant,
Quiero crear y administrar usuarios adicionales con permisos modulables,
Para que mi equipo opere la cuenta sin exponer modulos restringidos por defecto.

**Criterios de aceptación:**

**Dado** que el admin principal abre la gestion de usuarios
**Cuando** crea o habilita un usuario adicional
**Entonces** el sistema muestra un aviso resaltado de costo mensual antes o durante la accion
**Y** el usuario adicional recibe acceso por defecto solo a Dashboard, Inbox, Productos, Inventario, Ordenes y Citas

**Dado** que el admin principal configura permisos por modulo
**Cuando** habilita WhatsApp, IA, Funnels, Integraciones o Configuracion para un usuario adicional
**Entonces** el sistema concede ese acceso sin cambiar el rol base del usuario
**Y** los permisos se aplican en navegacion, rutas y backend

**Dado** que existe un usuario adicional sin permiso de Configuracion
**Cuando** intenta entrar al modulo o ejecutar una accion restringida
**Entonces** el sistema bloquea la operacion en backend aunque la opcion no se vea en la interfaz

**Dado** que el tenant requiere operar con un solo admin principal
**Cuando** se valida la estructura inicial de la cuenta
**Entonces** el sistema conserva un usuario admin principal por tenant
**Y** Swateck puede crear el tenant y su admin mediante un proceso operativo interno, sin self-service signup en V1

**FR cubiertos:** FR127, FR128, FR129, FR130, FR131, FR132, FR133, FR134, FR135, FR136, FR137, FR138, FR139

### Historia 1.4: Configurar WhatsApp Cloud API del tenant
Como admin principal del tenant,
Quiero registrar y probar la configuracion tecnica de WhatsApp Cloud API,
Para que mi empresa pueda conectar Meta y comenzar a operar conversaciones reales.

**Criterios de aceptación:**

**Dado** que el tenant no tiene WhatsApp configurado
**Cuando** el admin abre el modulo de WhatsApp
**Entonces** el sistema muestra la URL de callback, verify token, version de Graph API y el estado necesario para completar la conexion

**Dado** que el admin guarda credenciales o tokens de WhatsApp
**Cuando** la informacion se persiste
**Entonces** el sistema la almacena cifrada y no la expone en texto plano en la UI ni en respuestas posteriores

**Dado** que el tenant quiere validar la conexion
**Cuando** el admin ejecuta la prueba de cuenta
**Entonces** el sistema verifica que la cuenta puede enviar y recibir mediante Cloud API
**Y** informa errores comunes con mensajes entendibles para el admin

**Dado** que el flujo V2 de Embedded Signup aun no esta activo en V1
**Cuando** se revisa la configuracion de WhatsApp
**Entonces** el sistema deja claro que el onboarding simplificado por popup de Meta queda reservado para V2

**FR cubiertos:** FR027, FR028, FR029, FR030, FR031, FR032, FR033, FR034, FR035

### Historia 1.5: Definir funnel de bienvenida y captura inicial
Como admin principal del tenant,
Quiero configurar el funnel de bienvenida y sus reglas de captura,
Para que las conversaciones nuevas entren con un punto de partida comercial consistente.

**Criterios de aceptación:**

**Dado** que se crea un tenant nuevo
**Cuando** el sistema inicializa sus funnels
**Entonces** existe un funnel de bienvenida por defecto y puede configurarse con mensaje inicial y campos de apertura

**Dado** que el funnel de bienvenida se edita
**Cuando** el admin define los campos iniciales
**Entonces** el sistema permite capturar Nombre, Correo y Ciudad
**Y** toma el telefono desde WhatsApp sin pedirlo como campo obligatorio si ya esta disponible

**Dado** que el admin define la logica de clasificacion
**Cuando** guarda criterios y pasos del funnel
**Entonces** cada paso admite prompt, objetivos y criterio de transicion
**Y** la intencion del cliente se completa desde el funnel y la clasificacion conversacional, no como campo manual obligatorio

**Dado** que el tenant necesita mas flujos
**Cuando** el admin crea funnels adicionales
**Entonces** puede definir nombre, descripcion, estado y criterios de asignacion
**Y** puede usar pasos personalizables para distintos productos, servicios o intenciones

**FR cubiertos:** FR076, FR077, FR078, FR079, FR080, FR081, FR082, FR083, FR084, FR085, FR086, FR087, FR155, FR156, FR157

### Historia 1.6: Configurar IA comercial base
Como admin principal del tenant,
Quiero configurar la identidad, el contexto y el prompt base del agente,
Para que la IA responda con una base comercial coherente con mi negocio.

**Criterios de aceptación:**

**Dado** que el admin abre la configuracion de IA
**Cuando** define identidad, objetivo comercial, contexto del negocio, prompt, tono y guia conversacional
**Entonces** el sistema guarda esa configuracion por tenant
**Y** la IA puede usarla como base antes de responder

**Dado** que el admin configura la base del agente comercial
**Cuando** guarda la configuracion
**Entonces** el sistema conserva esa configuracion por tenant
**Y** la IA puede usarla como base antes de responder

**Dado** que el sistema necesita preparar menus y respuestas iniciales
**Cuando** la IA se configura para ventas, consultas o citas
**Entonces** el sistema puede usar plantillas interactivas, campos a capturar y contexto comercial
**Y** la IA no inventa precios, stock, disponibilidad, links de pago, politicas ni agenda

**FR cubiertos:** FR088, FR089, FR090, FR091, FR093, FR102, FR103, FR104, FR109

### Historia 1.7: Configurar seguridad y comportamiento operativo de la IA
Como admin principal del tenant,
Quiero definir las reglas de seguridad y ejecucion del agente,
Para que la IA opere con limites claros en horario, autonomia y escalamiento.

**Criterios de aceptación:**

**Dado** que el admin abre la configuracion de seguridad del agente
**Cuando** define reglas de seguridad, autonomia, politicas comerciales y escalamiento
**Entonces** el sistema conserva esas reglas separadas del prompt general
**Y** no permite desactivar guardrails obligatorios de tenant, pagos, inventario, seguridad o no invencion

**Dado** que el tenant necesita horario de atencion
**Cuando** el admin define lunes a viernes y sabado/domingo
**Entonces** el sistema aplica el comportamiento dentro y fuera de horario segun el dia y la hora local del tenant

**Dado** que el admin usa modo de prueba o versionado
**Cuando** guarda la IA como borrador o publica una version activa
**Entonces** el sistema distingue entre configuracion editable y configuracion publicada
**Y** puede simular conversaciones antes de activar cambios en produccion

**FR cubiertos:** FR092, FR094, FR095, FR096, FR097, FR098, FR099, FR100, FR101, FR105, FR106, FR107, FR108

### Historia 1.8: Configurar pasarela de pagos y contrato de integracion
Como admin principal del tenant,
Quiero configurar una pasarela de pagos compatible con el contrato tecnico de Swaflow,
Para que pueda generar links de pago y recibir confirmaciones validas sin depender de un solo proveedor.

**Criterios de aceptación:**

**Dado** que el tenant tiene una pasarela disponible
**Cuando** el admin registra sus credenciales y parametros
**Entonces** el sistema cifra los secretos y valida que existan los datos minimos para operar
**Y** no permite activar la pasarela si faltan datos para validar webhooks o mapear estados

**Dado** que la pasarela queda configurada
**Cuando** el sistema crea un link de pago
**Entonces** el adaptador comun permite generar el enlace, configurar expiracion, validar webhook y mapear estados
**Y** la solucion mantiene idempotencia por referencia o transaccion

**Dado** que la configuracion de expiracion de links es visible
**Cuando** el admin define el tiempo de expiracion
**Entonces** el sistema aplica el valor configurado al crear nuevos links
**Y** conserva el comportamiento por defecto de 120 minutos si no se cambia

**FR cubiertos:** FR110, FR111, FR153, FR154, FR167, FR168, FR169, FR174

### Historia 1.9: Configurar calendario del tenant
Como admin principal del tenant,
Quiero sincronizar citas con el calendario externo cuando exista,
Para que el sistema mantenga el flujo comercial aunque la integracion falle o no exista.

**Criterios de aceptación:**

**Dado** que el tenant quiere sincronizar citas
**Cuando** el admin configura una integracion de calendario
**Entonces** el sistema contempla Google Calendar y Microsoft Calendar como opciones esperadas
**Y** la ausencia de calendario no bloquea el uso interno de citas en Swaflow

**Dado** que el tenant ya usa citas en Swaflow
**Cuando** el sistema crea o actualiza una cita
**Entonces** intenta sincronizarla con el calendario configurado
**Y** la falla temporal de la integracion no bloquea la cita interna

**Dado** que el sistema debe proponer agenda
**Cuando** el tenant no tiene calendario integrado o esta disponible de forma parcial
**Entonces** usa la configuracion de horario operativo y las citas internas para validar disponibilidad
**Y** respeta duracion por defecto, franja manana/tarde y horizonte de busqueda

**FR cubiertos:** FR112, FR113, FR147, FR148, FR149, FR150, FR151, FR152, FR158, FR161, FR162, FR163, FR164, FR165, FR166

### Historia 1.10: Configurar notificaciones por correo y webhooks salientes
Como admin principal del tenant,
Quiero habilitar notificaciones y automatizaciones auxiliares,
Para que el negocio reciba soporte operativo sin convertir estas integraciones en fuente de verdad.

**Criterios de aceptación:**

**Dado** que el tenant quiere avisos operativos
**Cuando** el admin configura correo o notificaciones
**Entonces** el sistema puede usar la marca del tenant en correos generados
**Y** conserva la configuracion asociada al tenant

**Dado** que el tenant quiere automatizaciones externas
**Cuando** el admin configura webhooks salientes
**Entonces** el sistema permite filtrar por tipo de evento, activar o desactivar el webhook y usar firma o secreto
**Y** las fallas de n8n o de integraciones auxiliares no rompen transacciones ya confirmadas en backend

**Dado** que el backend debe seguir siendo la fuente de verdad
**Cuando** una integracion auxiliar falla
**Entonces** el sistema registra el incidente para soporte o administracion
**Y** no delega en esa integracion la confirmacion de ordenes, pagos, inventario o citas

**FR cubiertos:** FR114, FR115, FR116, FR117, FR118, FR119

### Historia 1.11: Operar acceso superadmin y auditoria transversal
Como operador de Swateck,
Quiero acceder a todos los tenants con un rol superadmin auditado,
Para que pueda dar soporte interno sin romper el aislamiento normal entre empresas.

**Criterios de aceptación:**

**Dado** que un usuario tiene rol superadmin de Swateck
**Cuando** accede a un tenant
**Entonces** el sistema le permite operar como excepcion explicita al aislamiento normal
**Y** registra el acceso con fines de auditoria

**Dado** que un usuario no tiene rol superadmin
**Cuando** intenta cruzar a otro tenant
**Entonces** el sistema lo trata como no encontrado o sin acceso segun la regla de aislamiento
**Y** no expone datos de otra empresa

**Dado** que el producto esta en V1
**Cuando** se revisa el panel avanzado de SuperUsuario SaaS
**Entonces** queda claro que consumos por tenant y reseteo centralizado de admins se reservan para V2
**Y** la plataforma conserva solo la capacidad operativa transversal requerida para soporte

**FR cubiertos:** FR140, FR141, FR142, FR170, FR171, FR172, FR173

## Epic 2: Inbox y Operacion Conversacional

### Historia 2.1: Ver y actualizar conversaciones en tiempo real
Como usuario autorizado del tenant,
Quiero ver la lista y el detalle de las conversaciones con actualizacion en tiempo real,
Para que pueda atender el inbox con contexto completo y sin perder actividad reciente.

**Criterios de aceptación:**

**Dado** que el usuario tiene acceso al Inbox
**Cuando** abre la bandeja de conversaciones
**Entonces** el sistema muestra contacto, ultimo mensaje, fecha y hora de ultima actividad, estado, no leidos y funnel cuando exista
**Y** la lista prioriza la actividad reciente

**Dado** que el usuario abre una conversacion
**Cuando** revisa el detalle
**Entonces** el sistema muestra el historial de mensajes entrantes, respuestas de IA, mensajes de asesores, mensajes interactivos y eventos relevantes
**Y** el contexto respeta el tenant y los permisos del usuario autenticado

**Dado** que entra un mensaje nuevo o cambia un estado relevante
**Cuando** el backend procesa el evento
**Entonces** el Inbox refleja el cambio de forma en tiempo real o equivalente perceptible
**Y** el conteo de no leidos se actualiza sin recargar toda la vista

**Dado** que llega un mensaje desde WhatsApp
**Cuando** el webhook lo entrega al backend
**Entonces** el sistema lo asocia al tenant, contacto y conversacion correctos
**Y** preserva metadata suficiente para entender el contexto del hilo

### Historia 2.2: Responder manualmente desde el Inbox
Como asesor o admin del tenant,
Quiero enviar mensajes manuales y ver respuestas interactivas dentro del Inbox,
Para que pueda continuar una conversacion sin depender de la IA.

**Criterios de aceptación:**

**Dado** que el usuario tiene permiso para responder conversaciones
**Cuando** escribe y envia un mensaje manual desde el Inbox
**Entonces** el sistema usa la cuenta WhatsApp conectada del tenant para enviarlo
**Y** registra el mensaje como parte del historial de la conversacion

**Dado** que la conversacion contiene botones, listas o respuestas interactivas
**Cuando** el cliente responde por un medio interactivo
**Entonces** el sistema conserva la metadata necesaria para que Inbox e IA entiendan el contexto
**Y** el evento queda visible en el historial

**Dado** que el envio manual falla por una condicion tecnica
**Cuando** la operacion no se completa
**Entonces** el sistema no pierde el borrador ni el contexto de la respuesta
**Y** deja la conversacion disponible para reintento o gestion humana

### Historia 2.3: Desactivar, reactivar y continuar la IA en una conversacion
Como asesor o admin del tenant,
Quiero pausar y reactivar la IA por conversacion sin perder contexto,
Para que pueda tomar el control humano cuando sea necesario y devolverlo luego al agente.

**Criterios de aceptación:**

**Dado** que una conversacion esta activa en Inbox
**Cuando** el usuario desactiva la intervencion de IA
**Entonces** la conversacion queda marcada como gestion humana
**Y** la desactivacion aplica solo a ese hilo

**Dado** que la IA esta desactivada en una conversacion
**Cuando** el usuario la reactiva desde el mismo contexto
**Entonces** la IA puede continuar usando el historial del cliente y del humano como contexto
**Y** respeta reglas del agente, catalogo, inventario y seguridad

**Dado** que la IA no tiene confianza suficiente o faltan datos para una accion critica
**Cuando** intenta responder
**Entonces** el sistema la obliga a pedir aclaracion o escalar a humano
**Y** evita loops o respuestas automatizadas repetitivas

**Dado** que la IA falla por timeout, error o falta de configuracion
**Cuando** el sistema no puede generar respuesta automatica
**Entonces** la conversacion queda disponible para gestion humana
**Y** no se bloquea el trabajo del Inbox

### Historia 2.4: Asignar, tomar y reasignar chats por usuario
Como admin o usuario autorizado del tenant,
Quiero tomar, asignar y reasignar conversaciones segun reglas operativas,
Para que el equipo distribuya la atencion sin duplicar el trabajo.

**Criterios de aceptación:**

**Dado** que existe un chat disponible
**Cuando** un usuario con permiso lo toma
**Entonces** el chat queda asignado a ese usuario
**Y** no queda disponible para gestion simultanea por otro usuario

**Dado** que el tenant solo tiene usuario admin activo
**Cuando** se listan los chats
**Entonces** el admin puede gestionarlos todos sin asignacion adicional obligatoria
**Y** la bandeja no exige otro responsable para operar

**Dado** que el tenant tiene exactamente un usuario adicional activo
**Cuando** la autoasignacion esta habilitada
**Entonces** los chats nuevos se asignan por defecto a ese usuario salvo ajuste manual del admin
**Y** si la autoasignacion se desactiva, los chats nuevos quedan disponibles/no asignados

**Dado** que un chat ya fue tomado o asignado
**Cuando** el admin lo reasigna a otro usuario
**Entonces** el sistema actualiza el responsable
**Y** registra el cambio para auditoria

**Dado** que el usuario ve la bandeja
**Cuando** revisa chats disponibles, asignados a el y asignados a otros
**Entonces** el sistema diferencia claramente esos estados
**Y** respeta permisos por usuario y aislamiento por tenant

### Historia 2.5: Clasificar conversaciones y preparar agenda desde el hilo
Como usuario autorizado del tenant,
Quiero clasificar conversaciones con funnel y dejar lista la intención de agenda,
Para que pueda avanzar la oportunidad comercial sin salir del Inbox.

**Criterios de aceptación:**

**Dado** que la IA infiere un funnel y una etapa para la conversacion
**Cuando** el usuario abre el hilo
**Entonces** el sistema muestra el funnel y la etapa actuales
**Y** esa clasificacion queda disponible para filtros y metricas

**Dado** que el usuario autorizado quiere ajustar la clasificacion
**Cuando** cambia manualmente el funnel o la etapa
**Entonces** el sistema guarda el nuevo valor
**Y** mantiene el historial de la conversacion asociado a ese cambio

**Dado** que el cliente expresa intencion de cita
**Cuando** el usuario registra esa intencion desde el Inbox
**Entonces** el sistema conserva el contexto de la conversacion para que la agenda se complete en el modulo de citas
**Y** refleja la accion en el historial de la conversacion

**Dado** que el usuario quiere seguir el contexto comercial
**Cuando** la conversacion avanza con mensajes nuevos
**Entonces** el Inbox conserva el contexto suficiente para que la IA o el humano retomen el hilo
**Y** la informacion permanece aislada al tenant correspondiente

## Epic 3: Catalogo e Inventario Comercial

### Historia 3.1: Sincronizar el catalogo Meta del tenant
Como admin principal del tenant,
Quiero sincronizar el catalogo existente de Meta con Swaflow,
Para que el sistema pueda operar productos reales sin crear catalogos paralelos.

**Criterios de aceptación:**

**Dado** que el tenant tiene un catalogo Meta asociado
**Cuando** el admin ejecuta la sincronizacion
**Entonces** el sistema trae los productos existentes desde Meta
**Y** guarda localmente nombre, descripcion, precio, moneda, estado, catalogo Meta, retailer ID y metadata relevante

**Dado** que un producto se sincroniza correctamente
**Cuando** el sistema lo almacena
**Entonces** queda disponible para visualizacion y uso operativo dentro del tenant
**Y** conserva el `whatsapp_product_retailer_id` cuando corresponda

**Dado** que el producto no existe en Meta
**Cuando** el admin revisa el catalogo local
**Entonces** el sistema no permite crear ese producto como si fuera nativo de Swaflow
**Y** evita mezclar productos inventados con productos sincronizados

### Historia 3.2: Visualizar y validar el catalogo sincronizado
Como usuario autorizado del tenant,
Quiero ver el catalogo sincronizado con mensajes claros sobre su estado en Meta,
Para que pueda entender si los productos estan listos para operar o requieren correccion.

**Criterios de aceptación:**

**Dado** que el catalogo ya fue sincronizado
**Cuando** el usuario abre Productos
**Entonces** el sistema muestra los productos sincronizados dentro de Swaflow
**Y** la vista permite distinguir productos activos, inactivos o con problemas de asociacion

**Dado** que el catalogo Meta no esta asociado a la WABA activa
**Cuando** el usuario revisa el estado del catalogo
**Entonces** el sistema lo advierte claramente
**Y** explica cuando Meta permite leer productos pero no enviarlos como cards nativas

**Dado** que Meta devuelve errores comunes de configuracion
**Cuando** ocurre un problema con IDs de catalogo o conjuntos de productos
**Entonces** el sistema muestra un mensaje entendible para el admin
**Y** no oculta el motivo tecnico esencial de la falla

### Historia 3.3: Registrar y calcular disponibilidad operativa de inventario
Como usuario autorizado del tenant,
Quiero ver la disponibilidad base, las reservas y el stock operativo,
Para que pueda evaluar con precision que productos estan realmente disponibles.

**Criterios de aceptación:**

**Dado** que un producto fue sincronizado desde Meta
**Cuando** el sistema crea o actualiza su inventario local
**Entonces** solo lo hace para productos existentes en el catalogo sincronizado
**Y** no permite inventario para productos inexistentes en Meta

**Dado** que el inventario local existe
**Cuando** el usuario abre la vista de inventario
**Entonces** el sistema muestra disponibilidad base, reservas operativas y disponibilidad operativa calculada
**Y** la disponibilidad operativa considera disponibilidad base menos reservas vigentes

**Dado** que Meta no puede leerse o sincronizarse
**Cuando** el sistema no tiene stock confiable
**Entonces** advierte que la disponibilidad es incierta
**Y** evita tratar el producto como disponible sin validacion

### Historia 3.4: Consumir reservas y exponer disponibilidad a IA e Inbox
Como usuario del tenant,
Quiero que la disponibilidad real controle lo que la IA y el Inbox pueden ofrecer,
Para que no se generen ventas ni recomendaciones sobre stock inexistente.

**Criterios de aceptación:**

**Dado** que una orden reserva inventario
**Cuando** la reserva queda activa
**Entonces** la disponibilidad operativa se reduce en consecuencia
**Y** el cambio se refleja en la vista del producto

**Dado** que una orden se cancela, expira o pasa a estado terminal
**Cuando** el sistema libera la reserva
**Entonces** la disponibilidad operativa vuelve a calcularse sin esa reserva
**Y** el cambio queda consistente en backend

**Dado** que una orden se confirma como pagada
**Cuando** el backend consume o confirma la reserva
**Entonces** el inventario refleja el consumo final
**Y** la venta queda lista para impactar reportes y dashboards

**Dado** que la IA o el Inbox quieren ofrecer un producto
**Cuando** consultan la disponibilidad
**Entonces** solo pueden usar la disponibilidad operativa validada
**Y** no pueden ofrecer productos no sincronizados o con disponibilidad incierta

## Epic 4: Ordenes, Pagos y Seguimiento Comercial

### Historia 4.1: Crear ordenes desde una conversacion con reserva de inventario
Como usuario autorizado del tenant,
Quiero convertir una conversacion en una orden valida con reserva de stock,
Para que pueda formalizar una compra sin sobreventa operativa.

**Criterios de aceptación:**

**Dado** que existe una intencion de compra en una conversacion
**Cuando** el usuario o la IA inicia la creacion de una orden
**Entonces** el sistema valida tenant, contacto, conversacion, productos sincronizados, disponibilidad operativa, cantidades y moneda
**Y** no permite crear la orden si falta informacion critica

**Dado** que la orden se crea como pendiente de pago
**Cuando** el sistema confirma la creacion
**Entonces** reserva la cantidad correspondiente de inventario
**Y** evita que otro flujo comercial consuma ese stock mientras la orden este pendiente

**Dado** que la orden queda creada
**Cuando** el usuario revisa el historial comercial
**Entonces** la orden queda asociada a la conversacion correspondiente
**Y** puede rastrearse desde el chat y desde el modulo de ordenes

### Historia 4.2: Generar y mostrar links de pago por tenant
Como usuario autorizado del tenant,
Quiero generar links de pago con una expiracion controlada,
Para que el cliente pueda completar el pago con la pasarela configurada.

**Criterios de aceptación:**

**Dado** que existe una orden lista para pago
**Cuando** el sistema solicita el link a la pasarela configurada
**Entonces** crea el enlace usando el adaptador autorizado para ese tenant
**Y** conserva referencia de pago, link, estado, total, moneda y fecha de vencimiento cuando aplique

**Dado** que el tenant tiene configurada una expiracion de links
**Cuando** se genera un nuevo link de pago
**Entonces** el sistema aplica la expiracion definida por el admin
**Y** usa 120 minutos por defecto si no existe configuracion personalizada

**Dado** que el usuario revisa la orden
**Cuando** observa la informacion de pago
**Entonces** el sistema muestra el estado y la referencia de forma entendible
**Y** no expone secretos ni credenciales de la pasarela

### Historia 4.3: Confirmar pagos por webhook con idempotencia
Como sistema backend del tenant,
Quiero confirmar pagos unicamente con webhooks validos e idempotentes,
Para que la orden cambie de estado solo cuando exista evidencia real de la pasarela.

**Criterios de aceptación:**

**Dado** que llega un webhook de pago valido
**Cuando** el backend lo valida con firma, token o secreto del proveedor
**Entonces** actualiza el estado de la orden sin requerir confirmacion manual de IA o frontend
**Y** refleja el cambio en menos de 5 segundos bajo condiciones normales

**Dado** que el webhook ya fue procesado
**Cuando** llega una repeticion con la misma referencia o transaccion
**Entonces** el sistema evita el doble procesamiento
**Y** mantiene el estado consistente

**Dado** que una orden pasa a pagada
**Cuando** el backend confirma el evento
**Entonces** consume o confirma la reserva de inventario
**Y** registra el evento de venta para dashboard y auditoria

**Dado** que una orden se cancela o expira
**Cuando** el estado terminal se confirma
**Entonces** libera las reservas correspondientes
**Y** registra el evento de cancelacion o expiracion

### Historia 4.4: Listar, filtrar y leer estados de orden en espanol
Como usuario autorizado del tenant,
Quiero revisar las ordenes por fecha, estado, cliente, producto y conversacion,
Para que pueda dar seguimiento comercial rapido y entendible.

**Criterios de aceptación:**

**Dado** que el usuario abre Ordenes
**Cuando** se carga la lista
**Entonces** el sistema muestra las ordenes de la mas reciente a la mas antigua
**Y** agrupa visualmente por mes y anio

**Dado** que el usuario necesita localizar una orden
**Cuando** aplica filtros por rango de fechas, estado, cliente/contacto, producto o usuario/conversacion
**Entonces** el sistema devuelve resultados filtrados correctamente
**Y** mantiene el contexto del tenant

**Dado** que el usuario ve el estado de una orden
**Cuando** el sistema muestra el valor en la interfaz
**Entonces** el estado se presenta en espanol para usuarios y admin
**Y** internamente puede seguir usando codigos estables

### Historia 4.5: Hacer seguimiento de links vencidos sin romper la verdad del backend
Como usuario autorizado del tenant,
Quiero que la IA pueda seguir una orden vencida sin confirmar pagos falsos,
Para que pueda recuperar ventas sin comprometer inventario ni estados criticos.

**Criterios de aceptación:**

**Dado** que un link de pago expira sin confirmacion
**Cuando** la conversacion sigue activa
**Entonces** el sistema permite seguimiento comercial por IA para preguntar si el cliente quiere continuar
**Y** puede generar un nuevo flujo de pago o agregar otro producto mediante backend

**Dado** que se ejecuta el seguimiento de un link vencido
**Cuando** la IA intenta actuar
**Entonces** no puede confirmar pagos, extender vencimientos ni retener inventario por su cuenta
**Y** solo puede continuar el flujo si el backend y las reglas del agente lo permiten

**Dado** que el link expirado ya tuvo un seguimiento automatico
**Cuando** pasan mas eventos sin respuesta del cliente
**Entonces** la IA no insiste nuevamente de forma automatica en V1
**Y** como maximo ejecuta un unico seguimiento automatico por expiracion

## Epic 5: Citas y Calendario

### Historia 5.1: Crear citas desde conversaciones o manualmente
Como usuario autorizado del tenant,
Quiero registrar citas desde una conversacion o de forma manual,
Para que pueda agendar oportunidades comerciales sin salir del flujo operativo.

**Criterios de aceptación:**

**Dado** que un cliente expresa intencion de agendar
**Cuando** la IA o el usuario inicia la creacion de la cita
**Entonces** el sistema permite crear la cita desde la conversacion
**Y** guarda la relacion entre cita, contacto y chat cuando exista

**Dado** que un usuario autorizado crea una cita manualmente desde Inbox
**Cuando** completa fecha, hora, estado, motivo y notas opcionales
**Entonces** el sistema guarda la cita como parte del tenant
**Y** mantiene el historial asociado al contexto conversacional cuando aplique

**Dado** que la cita se visualiza en la plataforma
**Cuando** el usuario revisa el modulo Citas
**Entonces** la cita aparece aunque no exista integracion con calendario externo
**Y** el estado visible se muestra en espanol

### Historia 5.2: Validar disponibilidad y proponer horarios de agenda
Como sistema de agenda del tenant,
Quiero validar disponibilidad y proponer opciones realistas de horario,
Para que la IA no invente disponibilidad y el cliente reciba alternativas concretas.

**Criterios de aceptación:**

**Dado** que un cliente solicita una cita
**Cuando** la IA inicia el flujo de agenda
**Entonces** primero pregunta si prefiere horario de manana o tarde
**Y** solo despues propone opciones

**Dado** que el tenant tiene calendario integrado
**Cuando** el sistema valida disponibilidad inicial
**Entonces** usa el calendario configurado para determinar opciones
**Y** mantiene la sincronizacion sin bloquear el flujo comercial si falla la integracion

**Dado** que el tenant no tiene calendario integrado
**Cuando** el sistema valida disponibilidad
**Entonces** usa las citas internas y el horario operativo compartido del comercio
**Y** no requiere configuraciones de horario duplicadas entre IA y Citas

**Dado** que se generan opciones de agenda
**Cuando** el sistema calcula propuestas
**Entonces** ofrece tres opciones con hora, preferiblemente en dias diferentes
**Y** busca dentro de un horizonte maximo de 7 dias a partir del dia siguiente

### Historia 5.3: Configurar reglas de horario y duracion de citas
Como admin principal del tenant,
Quiero definir el horario operativo y la duracion por defecto de las citas,
Para que la agenda siga reglas consistentes para todo el negocio.

**Criterios de aceptación:**

**Dado** que el admin configura las reglas de citas
**Cuando** define la duracion por defecto
**Entonces** el sistema usa 1 hora por defecto
**Y** permite modificar esa duracion en el modulo Citas

**Dado** que el admin usa franjas operativas por defecto
**Cuando** el sistema interpreta horarios de agenda
**Entonces** la franja de manana se toma como 08:00-12:00
**Y** la franja de tarde se toma como 14:00-18:00

**Dado** que el horario operativo cambia segun dias
**Cuando** se configura la disponibilidad semanal
**Entonces** el sistema aplica horarios distintos para lunes a viernes y para sabado/domingo
**Y** el comportamiento se usa tanto para IA como para agenda interna

### Historia 5.4: Sincronizar citas con calendario externo sin bloquear Swaflow
Como admin principal del tenant,
Quiero que las citas se sincronicen con el calendario externo cuando exista,
Para que el sistema mantenga el flujo comercial aunque la integracion falle o no exista.

**Criterios de aceptación:**

**Dado** que el tenant tiene una integracion de calendario activa
**Cuando** se crea o actualiza una cita
**Entonces** el sistema intenta sincronizarla con el calendario configurado
**Y** contempla Google Calendar y Microsoft Calendar como opciones esperadas

**Dado** que la integracion de calendario no existe
**Cuando** se crea una cita
**Entonces** la cita queda registrada y operable dentro de Swaflow
**Y** el flujo comercial no se bloquea

**Dado** que el calendario externo presenta una falla temporal
**Cuando** el sistema no puede sincronizar
**Entonces** la cita sigue disponible en Swaflow
**Y** la falla queda registrada para soporte

### Historia 5.5: Filtrar y reflejar citas en el dashboard y el hilo de conversacion
Como usuario autorizado del tenant,
Quiero encontrar y seguir citas por estado, origen y responsable,
Para que pueda entender el impacto comercial de la agenda en la operacion diaria.

**Criterios de aceptación:**

**Dado** que el usuario abre el modulo Citas
**Cuando** aplica filtros por rango de fechas, estado, usuario/asesor, cliente/contacto y origen
**Entonces** el sistema devuelve las citas correspondientes al tenant
**Y** mantiene la integridad de los datos entre vistas

**Dado** que una cita se crea o actualiza
**Cuando** el sistema guarda el cambio
**Entonces** la cita se refleja en el Dashboard
**Y** aparece en el historial o contexto de la conversacion relacionada

**Dado** que la IA no tiene datos suficientes para confirmar agenda
**Cuando** debe responder al cliente
**Entonces** pide aclaracion o deriva a humano segun las reglas del agente
**Y** no confirma disponibilidad inventada

## Epic 6: Dashboard y Visibilidad Operativa

### Historia 6.1: Ver resumen operativo del tenant en el Dashboard
Como admin o usuario autorizado del tenant,
Quiero ver un resumen rapido de chats, ventas y agendamientos,
Para que pueda entender el estado comercial sin entrar a cada modulo por separado.

**Criterios de aceptación:**

**Dado** que el usuario abre el Dashboard
**Cuando** se carga la vista principal
**Entonces** el sistema muestra tarjetas resumen con chats totales, chats pendientes por leer, ventas y agendamientos
**Y** la informacion pertenece solo al tenant autenticado

**Dado** que el tenant tiene actividad comercial
**Cuando** el Dashboard carga sus metricas iniciales
**Entonces** muestra resultados en un tiempo razonable bajo volumen normal
**Y** no requiere recorrer otros modulos para leer el estado basico del negocio

### Historia 6.2: Visualizar graficas y filtrar metricas del Dashboard
Como admin o usuario autorizado del tenant,
Quiero ver graficas y filtrar las metricas del Dashboard por distintos criterios,
Para que pueda analizar tendencias de ventas, chats y agendamientos con contexto util.

**Criterios de aceptación:**

**Dado** que el usuario revisa el Dashboard
**Cuando** la vista muestra series historicas
**Entonces** el sistema presenta graficas de ventas, agendamientos y chats en el tiempo
**Y** las graficas usan datos reales del tenant

**Dado** que el usuario quiere analizar una ventana concreta
**Cuando** aplica filtros por rango de fechas, asesor/usuario, estado de chat, funnel o etapa, y producto
**Entonces** el Dashboard devuelve las metricas filtradas correspondientes
**Y** los cambios de filtro conservan el contexto del tenant

**Dado** que no existe serie real para una grafica
**Cuando** el Dashboard intenta mostrarla
**Entonces** el sistema debe preferir un estado vacio o resumen textual honesto
**Y** no inventa datos para rellenar el panel

### Historia 6.3: Mantener aislamiento y rendimiento visible en el Dashboard
Como usuario del tenant,
Quiero que el Dashboard sea rapido y respete el aislamiento multi-tenant,
Para que pueda confiar en la informacion sin ver datos de otras empresas.

**Criterios de aceptación:**

**Dado** que el Dashboard consulta datos del backend
**Cuando** se calculan metricas o cambios de filtros
**Entonces** el sistema filtra todo por `company_id` o mecanismo equivalente
**Y** no expone datos de otro tenant bajo ninguna consulta normal

**Dado** que el usuario interactua con la navegación principal
**Cuando** abre o refresca vistas comunes
**Entonces** el sistema responde dentro de los tiempos objetivo de experiencia
**Y** las metricas iniciales y cambios de filtro mantienen un comportamiento fluido bajo volumen normal

**Dado** que existen cambios de ventas o citas originadas en otros modulos
**Cuando** el Dashboard actualiza sus datos
**Entonces** refleja esos cambios sin mezclar información entre tenants
**Y** conserva coherencia con el backend como fuente de verdad

## Epic 7: Superadmin, Auditoria y Retiro del Tenant

### Historia 7.1: Operar como superadmin con acceso auditado
Como operador de Swateck,
Quiero acceder a tenants como superadmin con trazabilidad completa,
Para que pueda dar soporte interno sin romper el aislamiento normal.

**Criterios de aceptación:**

**Dado** que el usuario tiene rol superadmin autorizado
**Cuando** accede a un tenant
**Entonces** el sistema le permite operar como excepcion explicita
**Y** registra el acceso para auditoria

**Dado** que el usuario no tiene rol superadmin
**Cuando** intenta acceder a datos de otro tenant
**Entonces** el sistema lo trata como no encontrado o sin permiso segun la regla de aislamiento
**Y** no revela informacion de otras empresas

**Dado** que el usuario superadmin realiza acciones sensibles
**Cuando** cambia configuracion o revisa datos operativos
**Entonces** el sistema deja registro auditable de la accion
**Y** conserva la separacion por tenant

### Historia 7.2: Registrar auditoria de cambios y eventos relevantes
Como operador o admin del tenant,
Quiero que los cambios criticos queden registrados,
Para que exista trazabilidad operativa para soporte, seguridad y control interno.

**Criterios de aceptación:**

**Dado** que ocurren eventos de negocio relevantes
**Cuando** el sistema procesa mensajes, ordenes, pagos, citas, asignaciones de chat o cambios de configuracion critica
**Entonces** registra esos eventos de forma auditable
**Y** conserva la informacion necesaria para soporte posterior

**Dado** que un admin reasigna un chat
**Cuando** se confirma el cambio
**Entonces** el sistema guarda usuario, fecha y nuevo responsable
**Y** ese historial queda disponible para auditoria operativa

**Dado** que se modifican permisos, integraciones, credenciales, IA o funnels
**Cuando** se guarda la accion
**Entonces** el cambio queda disponible para auditoria
**Y** no se pierde el rastro del actor ni del momento del cambio

### Historia 7.3: Exportar la informacion completa al retiro del tenant
Como operador autorizado de Swateck,
Quiero generar un paquete de exportacion completo cuando un tenant se retira,
Para que la empresa pueda recibir sus gestiones de forma ordenada y verificable.

**Criterios de aceptación:**

**Dado** que un tenant se retira
**Cuando** se solicita la exportacion de su informacion
**Entonces** Swaflow genera un archivo ZIP
**Y** conserva mensajes, eventos, archivos y gestiones mientras el tenant este activo

**Dado** que el ZIP se genera
**Cuando** el usuario abre su contenido
**Entonces** incluye un archivo TXT por modulo
**Y** cada TXT contiene interacciones delimitadas por pipe `|` con encabezado de columnas

**Dado** que el tenant ya no opera activamente
**Cuando** se consulta la disponibilidad de sus datos exportados
**Entonces** el sistema mantiene la trazabilidad documental requerida
**Y** la exportacion cubre todas las gestiones registradas en la plataforma

FR60: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR61: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR62: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR63: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR64: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR65: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR145: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR146: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR153: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR154: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR167: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR168: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR169: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR174: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR178: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR179: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR180: Epic 4 - Ordenes, Pagos y Seguimiento Comercial
FR66: Epic 5 - Citas y Calendario
FR67: Epic 5 - Citas y Calendario
FR68: Epic 5 - Citas y Calendario
FR69: Epic 5 - Citas y Calendario
FR70: Epic 5 - Citas y Calendario
FR71: Epic 5 - Citas y Calendario
FR72: Epic 5 - Citas y Calendario
FR73: Epic 5 - Citas y Calendario
FR74: Epic 5 - Citas y Calendario
FR75: Epic 5 - Citas y Calendario
FR147: Epic 5 - Citas y Calendario
FR148: Epic 5 - Citas y Calendario
FR149: Epic 5 - Citas y Calendario
FR150: Epic 5 - Citas y Calendario
FR151: Epic 5 - Citas y Calendario
FR152: Epic 5 - Citas y Calendario
FR158: Epic 5 - Citas y Calendario
FR161: Epic 5 - Citas y Calendario
FR162: Epic 5 - Citas y Calendario
FR163: Epic 5 - Citas y Calendario
FR164: Epic 5 - Citas y Calendario
FR165: Epic 5 - Citas y Calendario
FR166: Epic 5 - Citas y Calendario
FR1: Epic 6 - Dashboard y Visibilidad Operativa
FR2: Epic 6 - Dashboard y Visibilidad Operativa
FR3: Epic 6 - Dashboard y Visibilidad Operativa
FR4: Epic 6 - Dashboard y Visibilidad Operativa
FR5: Epic 6 - Dashboard y Visibilidad Operativa
FR6: Epic 6 - Dashboard y Visibilidad Operativa
FR7: Epic 6 - Dashboard y Visibilidad Operativa
FR8: Epic 6 - Dashboard y Visibilidad Operativa
FR140: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR141: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR142: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR159: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR160: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR175: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR176: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
FR177: Epic 7 - Superadmin, Auditoria y Retiro del Tenant
