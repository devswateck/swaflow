---
title: "PRD: Swaflow"
status: final
created: "2026-06-08"
updated: "2026-06-09"
---

# PRD: Swaflow

> PRD final. Este documento se construyo usando
> `project-context.md`, `proyecto_saas_ia_comercial_multitenant.md`, la
> validacion del backend actual y la investigacion puntual de onboarding
> WhatsApp/Meta.

## Discovery Intake

### Vision Inicial

Swaflow sera una plataforma web SaaS multi-tenant para que empresas gestionen
ventas conversacionales por WhatsApp conectado a Meta, con IA comercial,
operacion humana, catalogo, inventario, ordenes, citas, funnels, integraciones
y control administrativo por tenant. Debe servir a negocios que venden
productos, negocios que solo agendan citas y negocios mixtos que necesitan ambos
flujos.

### Modulos Indicados Por El Usuario

- Dashboard: metricas de negocio, chats, pendientes por leer, ventas,
  agendamientos y graficos en tiempo.
- Inbox: listado de chats, detalle de conversacion, control para desactivar IA,
  agendar citas y asignar/ver funnel manual o automaticamente.
- Productos: sincronizacion/actualizacion del catalogo existente en Meta y
  visualizacion del catalogo.
- Inventario: productos del catalogo con stock y reservas.
- Ordenes: listado de mas reciente a mas antiguo, agrupado por mes y anio, con
  estados segun pasarela de pago.
- Citas: nombre del cliente, fecha, hora, estado en espanol y motivo.
- Funnels: creacion de apartados personalizables con prompts por paso y criterio
  para clasificar clientes.
- IA: configuracion integral del agente, usando como base lo ya estructurado en
  backend.
- WhatsApp: conexion de WhatsApp Cloud API al sistema. V1 mantiene la
  configuracion tecnica actual; V2 simplifica el onboarding con autenticacion
  Meta/Embedded Signup mediante popup.
- Integraciones: calendario, notificaciones por correo, pasarela de pagos y
  webhooks salientes para n8n u otras automatizaciones.
- Configuracion: reseteo de contrasena.
- Superusuario: control de consumos por cliente/tenant, chats, ventas,
  agendamientos y reseteo de usuarios admin de cada tenant.

### Restricciones Vigentes

- Backend es fuente de verdad para pagos, inventario, ordenes, permisos y
  estados criticos.
- n8n solo debe ejecutar automatizaciones auxiliares.
- MySQL es la decision vigente de base de datos, aunque la fuente historica
  mencione PostgreSQL.
- La IA no debe inventar precios, stock, disponibilidad, links de pago,
  politicas ni agenda.

### Discovery Status

Discovery inicial completado en Coaching path. El PRD esta listo para auditoria,
reviewer pass y resolucion de preguntas residuales.

## Stakes Calibration

Este PRD se trabajara con rigor de **lanzamiento comercial SaaS**. Debe ser
suficiente para alinear producto, UX, arquitectura, implementacion y validacion
de una plataforma vendible a multiples tenants.

## Product Scope

### V1 Comercial

La primera version comercial debe incluir los modulos funcionales ya adelantados
que hacen vendible el flujo comercial conversacional:

- Dashboard.
- Inbox.
- WhatsApp.
- IA.
- Productos y catalogo Meta.
- Inventario.
- Ordenes.
- Citas.
- Funnels.
- Integraciones.
- Configuracion de cuenta/usuario.

### V2

- Panel SuperUsuario SaaS: control centralizado de consumos por tenant, chats,
  ventas, agendamientos, soporte operativo y reseteo de usuarios admin de cada
  tenant.
- Conexion simplificada de WhatsApp mediante autenticacion/popup de Meta
  Embedded Signup, reduciendo configuracion tecnica manual para clientes.
- Self-service signup de tenants y alta autonoma sin intervencion de Swateck.

### Non-Goals V1

- Panel SuperUsuario avanzado.
- Self-service signup de tenants.
- Conexion WhatsApp mediante popup Meta/Embedded Signup.
- Omnicanal completo distinto a WhatsApp.
- CRM, ERP o builder visual avanzado.
- RAG, voz o multiagentes complejos.
- Automatizaciones criticas ejecutadas por n8n.
- Creacion de productos en Swaflow fuera del catalogo Meta.
- Pasarelas arbitrarias sin adaptador/proveedor configurado o certificado por
  Swateck.

### Implicacion De Alcance

V1 debe permitir vender y operar clientes tenant desde su propia experiencia de
negocio. La operacion interna avanzada de Swateck sobre todos los tenants puede
quedar fuera del primer lanzamiento, siempre que exista una forma minima
operativa de crear/soportar tenants por medios administrativos actuales.

En V1, cada tenant y su admin principal son creados por Swateck mediante un
proceso operativo/admin. El alta self-service de tenants queda fuera de V1.

## Launch Goal And Success Metrics

### Launch Goal

V1 comercial estara lista para vender cuando un tenant pueda operar el flujo
completo de ventas conversacionales por WhatsApp de punta a punta, desde la
conexion de su cuenta Meta hasta la gestion de conversaciones, IA, catalogo,
inventario, ordenes, pagos, citas, funnels, integraciones auxiliares y metricas
basicas del negocio.

### End-To-End Success Path

El flujo minimo exitoso de V1 debe permitir:

1. El admin del tenant configura su cuenta, usuarios y accesos.
2. El admin conecta WhatsApp Cloud API mediante la configuracion tecnica actual
   disponible en V1.
3. El tenant sincroniza o visualiza productos desde catalogo Meta.
4. El tenant revisa inventario, stock disponible y reservas.
5. Un cliente escribe por WhatsApp y el mensaje entra al Inbox del tenant.
6. La IA responde usando la configuracion del agente, catalogo, inventario,
   FAQs, reglas de seguridad y guion conversacional.
7. El chat puede pasar a humano o desactivar intervencion IA cuando un asesor lo
   necesite.
8. La conversacion queda clasificada en un funnel por criterio de IA o ajuste
   manual.
9. Si el cliente compra, el sistema crea una orden, reserva inventario y genera
   link de pago.
10. La pasarela confirma el estado de pago por webhook y la orden refleja el
    estado correcto.
11. Si el cliente agenda, la cita queda registrada con fecha, hora, estado y
    motivo.
12. Las integraciones auxiliares pueden notificar o automatizar eventos sin
    reemplazar al backend como fuente de verdad.
13. El dashboard muestra metricas basicas de chats, pendientes, ventas,
    agendamientos y comportamiento en el tiempo.

### Primary Success Metrics

- Tiempo desde creacion de tenant hasta primer mensaje WhatsApp recibido.
- Porcentaje de tenants que completan la configuracion tecnica de WhatsApp V1
  con datos validos y webhook operativo.
- Porcentaje de conversaciones respondidas correctamente por IA o humano.
- Porcentaje de chats con estado/funnel identificable.
- Numero de ordenes creadas y pagadas correctamente desde conversaciones.
- Numero de citas creadas desde conversaciones.
- Precicion operacional de inventario: ventas pagadas descuentan stock y
  cancelaciones/liberaciones eliminan reservas.
- Disponibilidad percibida del inbox y actualizacion realtime durante operacion.

### Counter-Metrics

- Cero fugas de datos entre tenants.
- Cero pagos marcados como pagados sin confirmacion valida de la pasarela.
- Cero respuestas de IA que inventen precio, stock, disponibilidad, links de
  pago, politicas comerciales o agenda.
- Cero reservas de inventario retenidas indebidamente tras cancelacion o estado
  terminal.
- Webhooks o integraciones auxiliares fallidas no deben romper transacciones
  criticas ya confirmadas.

## Functional Requirements

### Dashboard

El Dashboard V1 debe darle al admin y usuarios autorizados una lectura rapida del
estado comercial del tenant, sin obligarlos a entrar modulo por modulo para
entender actividad, pendientes, ventas y citas.

- **FR-001:** El sistema debe mostrar tarjetas resumen con chats totales, chats
  pendientes por leer, ventas y agendamientos del tenant.
- **FR-002:** El sistema debe mostrar graficos de ventas, agendamientos y chats
  en el tiempo.
- **FR-003:** El sistema debe permitir filtrar las metricas del Dashboard por
  rango de fechas.
- **FR-004:** El sistema debe permitir filtrar las metricas del Dashboard por
  asesor/usuario cuando existan usuarios adicionales en el tenant.
- **FR-005:** El sistema debe permitir filtrar las metricas del Dashboard por
  estado de chat.
- **FR-006:** El sistema debe permitir filtrar las metricas del Dashboard por
  funnel o etapa cuando la conversacion tenga clasificacion comercial.
- **FR-007:** El sistema debe permitir filtrar las metricas del Dashboard por
  producto cuando existan ordenes o interacciones asociadas a productos.
- **FR-008:** El sistema debe respetar aislamiento multi-tenant en todos los
  calculos del Dashboard; ningun usuario debe ver metricas de otra empresa.

### Inbox

El Inbox V1 debe ser el centro de operacion diaria para gestionar conversaciones
de WhatsApp, alternar entre IA y asesores humanos, clasificar oportunidades y
ejecutar acciones comerciales sin perder contexto.

- **FR-009:** El sistema debe mostrar un listado de conversaciones del tenant
  con contacto, ultimo mensaje, fecha/hora de ultima actividad, estado,
  conteo de no leidos y clasificacion de funnel cuando exista.
- **FR-010:** El sistema debe mostrar el detalle de una conversacion con el
  historial de mensajes entrantes, respuestas de IA, mensajes de asesores,
  mensajes interactivos y eventos relevantes.
- **FR-011:** El sistema debe permitir enviar mensajes manuales desde el Inbox
  usando la cuenta WhatsApp conectada del tenant.
- **FR-012:** El sistema debe permitir desactivar la intervencion de IA por
  conversacion individual.
- **FR-013:** La desactivacion de IA por conversacion debe ser reversible desde
  el mismo contexto operativo del chat.
- **FR-014:** Cuando la IA se reactive en una conversacion, debe poder usar el
  historial de mensajes del humano y del cliente como contexto para continuar de
  forma natural, respetando reglas del agente, catalogo, inventario y seguridad.
- **FR-015:** El sistema debe permitir agendar una cita desde una conversacion,
  conservando relacion entre cita, contacto y chat.
- **FR-016:** El sistema debe mostrar el funnel y etapa asignados a la
  conversacion cuando hayan sido inferidos por IA.
- **FR-017:** El sistema debe permitir que un usuario autorizado seleccione o
  ajuste manualmente el funnel y etapa de una conversacion.
- **FR-018:** El sistema debe actualizar en tiempo real, o de forma equivalente
  perceptible, mensajes nuevos, conteos no leidos y cambios de estado relevantes
  del Inbox.
- **FR-019:** Las acciones del Inbox deben respetar permisos por usuario y
  aislamiento por tenant.
- **FR-020:** Si el tenant solo tiene usuario admin activo, el admin debe poder
  gestionar todos los chats del tenant sin asignacion adicional obligatoria.
- **FR-021:** Si el tenant tiene exactamente un usuario adicional activo, el
  sistema debe asignar todos los chats a ese usuario por defecto, salvo ajuste
  manual del admin.
- **FR-022:** Si el tenant tiene mas de un usuario adicional activo, los chats
  no asignados deben poder ser tomados por un usuario.
- **FR-023:** Cuando un usuario toma un chat, el chat debe quedar asignado a ese
  usuario y no debe estar disponible para que otro usuario lo gestione
  simultaneamente.
- **FR-024:** El admin del tenant debe poder asignar manualmente chats a un
  usuario especifico.
- **FR-025:** El Inbox debe permitir distinguir chats disponibles, chats
  asignados al usuario actual y chats asignados a otros usuarios, respetando los
  permisos del usuario autenticado.
- **FR-026:** El admin del tenant debe poder reasignar un chat a otro usuario
  aunque el chat ya haya sido tomado o este asignado, dejando registro del cambio
  de responsable.
- **FR-172:** El admin debe poder desactivar la autoasignacion por defecto cuando
  el tenant tenga exactamente un usuario adicional activo.
- **FR-173:** Si la autoasignacion esta desactivada, los chats nuevos deben
  quedar disponibles/no asignados hasta que un usuario los tome o el admin los
  asigne manualmente.

### WhatsApp

El modulo WhatsApp V1 debe permitir conectar y operar WhatsApp Cloud API con la
configuracion tecnica actual. La simplificacion con popup Meta queda como mejora
V2.

- **FR-027:** El sistema debe permitir configurar una cuenta WhatsApp Cloud API
  por tenant con los datos tecnicos requeridos por la integracion actual.
- **FR-028:** El sistema debe mostrar la URL de callback/webhook, verify token,
  version de Graph API y estado de configuracion necesario para completar la
  conexion en Meta.
- **FR-029:** El sistema debe almacenar tokens y credenciales de WhatsApp de
  forma cifrada y nunca exponerlos en texto plano despues de guardarlos.
- **FR-030:** El sistema debe permitir probar la cuenta WhatsApp configurada para
  validar que puede enviar y recibir mediante Cloud API.
- **FR-031:** El sistema debe recibir mensajes entrantes desde el webhook de
  WhatsApp y asociarlos al tenant, contacto y conversacion correctos.
- **FR-032:** El sistema debe enviar mensajes salientes desde Inbox, IA o
  acciones autorizadas usando la cuenta WhatsApp del tenant.
- **FR-033:** El sistema debe procesar mensajes interactivos y respuestas de
  clientes preservando metadata suficiente para que Inbox e IA entiendan el
  contexto.
- **FR-034:** El sistema debe validar firma o secreto de webhooks de WhatsApp
  cuando la configuracion disponible lo permita.
- **FR-035:** El sistema debe contemplar para V2 un flujo de conexion menos
  tecnico basado en autenticacion con popup de Meta/Embedded Signup.

### Productos Y Catalogo Meta

El modulo Productos V1 debe reflejar el catalogo existente en Meta. Swaflow no
debe crear productos adicionales ni convertirse en fuente primaria del catalogo
en V1.

- **FR-036:** El sistema debe sincronizar productos existentes desde el catalogo
  Meta conectado al tenant.
- **FR-037:** El sistema debe guardar localmente los datos necesarios para operar
  ventas conversacionales: nombre, descripcion, precio, moneda, estado,
  catalogo Meta, retailer ID y metadata relevante devuelta por Meta.
- **FR-038:** El sistema debe permitir visualizar el catalogo sincronizado desde
  Meta dentro de Swaflow.
- **FR-039:** El sistema no debe permitir crear productos nuevos en Swaflow que
  no existan previamente en Meta.
- **FR-040:** El sistema no debe permitir que la IA ofrezca productos que no
  esten sincronizados desde Meta y disponibles segun inventario local.
- **FR-041:** El sistema debe advertir claramente cuando el catalogo Meta no
  este asociado a la WABA activa o cuando Meta permita leer productos pero no
  permita enviarlos como cards nativas.
- **FR-042:** El sistema debe conservar el `whatsapp_product_retailer_id` para
  enviar cards nativas de WhatsApp cuando corresponda.
- **FR-043:** El sistema debe manejar errores comunes de Meta con mensajes
  entendibles para el admin, incluyendo el uso de IDs incorrectos de catalogo o
  conjuntos de productos.

### Inventario

El modulo Inventario V1 debe mostrar la disponibilidad de los productos
sincronizados desde Meta. Meta es la fuente de disponibilidad base; Swaflow no
debe pedir al admin crear stock para productos que no existan en Meta.

- **FR-044:** El sistema debe crear o actualizar registros de inventario local
  solo para productos sincronizados desde Meta.
- **FR-045:** El sistema debe reflejar la disponibilidad base recibida desde
  Meta para cada producto sincronizado.
- **FR-046:** El sistema debe mostrar, por producto, disponibilidad base,
  reservas operativas en Swaflow y disponibilidad operativa calculada.
- **FR-047:** La disponibilidad operativa debe calcularse considerando la
  disponibilidad base de Meta menos las reservas vigentes generadas por ordenes
  en proceso dentro de Swaflow.
- **FR-048:** El sistema no debe permitir inventario para productos inexistentes
  en Meta o no sincronizados en el catalogo del tenant.
- **FR-049:** La IA y el Inbox deben usar la disponibilidad operativa para
  decidir si un producto puede ofrecerse, reservarse o enviarse como card nativa.
- **FR-050:** El sistema debe liberar reservas cuando una orden sea cancelada,
  expirada o pase a un estado terminal que no requiere retener inventario.
- **FR-051:** El sistema debe descontar o marcar como consumida la reserva cuando
  una orden sea confirmada como pagada por la pasarela.
- **FR-052:** El sistema debe advertir cuando la disponibilidad de Meta no pueda
  leerse o sincronizarse, evitando que la IA ofrezca productos con disponibilidad
  incierta.

### Ordenes

El modulo Ordenes V1 debe registrar y visualizar los pedidos generados desde el
flujo conversacional, con estados entendibles para el admin/usuarios y control
transaccional desde backend.

- **FR-053:** El sistema debe crear ordenes desde una conversacion cuando exista
  intencion de compra y datos suficientes para una accion critica.
- **FR-054:** La creacion de una orden debe validar tenant, contacto,
  conversacion, productos sincronizados desde Meta, disponibilidad operativa,
  cantidades y moneda.
- **FR-055:** Al crear una orden pendiente de pago, el sistema debe reservar la
  cantidad correspondiente para evitar sobreventa operativa.
- **FR-056:** El sistema debe generar link de pago mediante la pasarela
  configurada para el tenant cuando la orden este lista para pago.
- **FR-057:** El sistema debe almacenar y mostrar referencia de pago, link de
  pago, estado de pago, fecha de vencimiento cuando aplique, total y moneda.
- **FR-058:** El sistema debe actualizar el estado de pago de la orden con base
  en webhooks validos de la pasarela, no por confirmacion manual de IA o
  frontend.
- **FR-059:** El sistema debe listar ordenes de la mas reciente a la mas antigua.
- **FR-060:** La vista de Ordenes debe agrupar visualmente las ordenes por mes y
  anio.
- **FR-061:** El sistema debe mostrar estados visibles en espanol para
  admin/usuarios, aunque internamente use codigos estables.
- **FR-062:** El sistema debe permitir filtrar ordenes por rango de fechas,
  estado, cliente/contacto, producto y usuario/conversacion cuando la relacion
  exista.
- **FR-063:** Cuando una orden sea pagada, el sistema debe registrar el evento de
  venta, consumir o confirmar la reserva de inventario y reflejar la venta en el
  Dashboard.
- **FR-064:** Cuando una orden sea cancelada o expirada, el sistema debe liberar
  reservas y registrar el evento correspondiente.
- **FR-065:** El sistema debe evitar duplicidad o doble procesamiento de
  webhooks de pago mediante identificadores de referencia/transaccion.
- **FR-153:** Los links de pago deben expirar por defecto a los 120 minutos.
- **FR-154:** El admin debe poder configurar el tiempo de expiracion de links de
  pago dentro de la configuracion de la integracion de pagos.
- **FR-145:** Cuando un link de pago expire sin confirmacion, el sistema debe
  permitir seguimiento comercial por IA para preguntar si el cliente desea
  continuar con el pago, generar un nuevo flujo de pago por backend o agregar
  otro producto.
- **FR-146:** El seguimiento de pagos expirados no debe confirmar pagos,
  extender vencimientos ni retener inventario sin pasar por reglas y servicios
  backend autorizados.
- **FR-178:** La IA debe ejecutar como maximo un seguimiento automatico despues
  de que expire un link de pago.
- **FR-179:** Si el cliente responde al seguimiento de link expirado, la IA puede
  continuar el flujo comercial segun reglas del agente y backend.
- **FR-180:** Si el cliente no responde al seguimiento de link expirado, la IA no
  debe insistir nuevamente de forma automatica en V1.

### Citas

El modulo Citas V1 debe registrar agendamientos originados desde conversaciones,
por IA o por accion manual, y mantenerlos visibles en Swaflow aunque no exista
integracion de calendario externa.

- **FR-066:** El sistema debe permitir crear citas desde una conversacion por
  accion de IA cuando el cliente exprese intencion de agendar y existan datos
  suficientes.
- **FR-067:** El sistema debe permitir crear citas manualmente desde el Inbox por
  un usuario autorizado.
- **FR-068:** Cada cita debe guardar cliente/contacto, conversacion relacionada
  cuando exista, fecha, hora, estado, motivo de agendamiento y notas opcionales.
- **FR-069:** Los estados visibles de cita deben mostrarse en espanol para
  admin/usuarios.
- **FR-070:** El modulo Citas debe listar todas las citas del tenant,
  independientemente de si existe o no integracion con calendario externo.
- **FR-071:** Si el tenant tiene calendario integrado, el sistema debe intentar
  sincronizar la cita con el calendario configurado.
- **FR-072:** Si no hay calendario integrado, la cita debe quedar registrada y
  operable dentro de Swaflow sin bloquear el flujo comercial.
- **FR-073:** El sistema debe permitir filtrar citas por rango de fechas, estado,
  usuario/asesor, cliente/contacto y origen cuando aplique.
- **FR-074:** El sistema debe reflejar citas creadas o actualizadas en el
  Dashboard y en el historial/contexto de la conversacion relacionada.
- **FR-075:** La IA no debe confirmar disponibilidad de agenda si no tiene datos
  suficientes o integracion/reglas configuradas; debe pedir aclaracion o derivar
  a humano segun reglas del agente.
- **FR-147:** Cuando un cliente solicite una cita, la IA debe preguntar si
  prefiere horario de manana o tarde antes de proponer opciones.
- **FR-148:** Si el tenant tiene calendario integrado, el sistema debe validar
  disponibilidad inicial contra ese calendario para proponer citas.
- **FR-149:** Si el tenant no tiene calendario integrado, el sistema debe validar
  disponibilidad contra las citas internas de Swaflow y el horario operativo
  compartido del comercio.
- **FR-150:** El sistema debe proponer al cliente tres opciones de agenda
  posibles con hora, preferiblemente en dias diferentes, segun disponibilidad y
  preferencia manana/tarde.
- **FR-151:** El sistema debe usar el mismo horario operativo configurado para
  IA y para validar disponibilidad de citas cuando no exista calendario
  integrado.
- **FR-152:** El sistema no debe requerir configuraciones de horario duplicadas
  entre IA y Citas para V1.
- **FR-161:** La duracion por defecto de una cita debe ser 1 hora.
- **FR-162:** El cliente/admin debe poder configurar la duracion de las citas en
  el modulo Citas.
- **FR-163:** La franja de manana debe interpretarse por defecto como
  08:00-12:00.
- **FR-164:** La franja de tarde debe interpretarse por defecto como 14:00-18:00.
- **FR-165:** El sistema debe ofrecer citas como minimo desde el dia siguiente,
  no para el mismo dia.
- **FR-166:** El sistema debe buscar las tres opciones de agenda dentro de un
  horizonte maximo de los proximos 7 dias.

### Funnels

El modulo Funnels V1 debe permitir modelar etapas conversacionales y comerciales
que orientan a la IA y clasifican conversaciones. Todo tenant debe tener un
funnel inicial de bienvenida como punto de entrada.

- **FR-076:** El sistema debe garantizar que cada tenant tenga un funnel inicial
  de bienvenida.
- **FR-077:** El funnel de bienvenida debe permitir configurar el mensaje inicial
  al cliente.
- **FR-078:** El funnel de bienvenida debe permitir configurar datos a capturar
  del cliente durante la apertura de la conversacion.
- **FR-079:** El admin debe poder crear funnels adicionales para distintos flujos,
  intenciones, productos, servicios o etapas comerciales.
- **FR-080:** Cada funnel debe permitir definir nombre, descripcion, estado y
  criterios/caracteristicas de asignacion.
- **FR-081:** Cada funnel debe permitir configurar pasos o apartados
  personalizables.
- **FR-082:** Cada paso de funnel debe permitir definir prompt/instruccion,
  objetivos y criterio de transicion.
- **FR-083:** La IA debe iniciar nuevas conversaciones en el funnel de
  bienvenida, salvo que existan reglas explicitas que indiquen otro punto de
  entrada.
- **FR-084:** A partir del funnel de bienvenida, la IA debe poder asignar la
  conversacion a cualquier funnel activo segun intencion del cliente y criterios
  configurados.
- **FR-085:** El Inbox debe mostrar el funnel y paso actual asignado por IA.
- **FR-086:** Un usuario autorizado debe poder ajustar manualmente el funnel y
  paso de una conversacion.
- **FR-087:** La asignacion de funnel, automatica o manual, debe quedar
  disponible para filtros, metricas de Dashboard y contexto de IA.
- **FR-155:** El funnel de bienvenida debe capturar como campos iniciales
  Nombre, Correo y Ciudad.
- **FR-156:** El sistema debe tomar el telefono del cliente desde el chat de
  WhatsApp y no pedirlo como campo obligatorio inicial si ya esta disponible.
- **FR-157:** La intencion del cliente debe completarse desde el funnel y la
  clasificacion conversacional, no como campo manual obligatorio de bienvenida.

### IA

El modulo IA V1 debe permitir al admin configurar el agente comercial de punta a
punta, usando la estructura existente del backend y agregando controles
operativos que hagan segura su activacion para clientes reales.

- **FR-088:** El sistema debe permitir configurar identidad/nombre del agente.
- **FR-089:** El sistema debe permitir configurar el objetivo comercial del
  agente, por ejemplo vender, agendar, calificar lead, soporte inicial o derivar
  a asesor.
- **FR-090:** El sistema debe permitir configurar contexto del negocio,
  productos/servicios declarados y descripcion comercial del tenant.
- **FR-091:** El sistema debe permitir configurar prompt del sistema, tono,
  objetivo conversacional y guia conversacional.
- **FR-092:** El sistema debe permitir configurar reglas de seguridad del agente
  separadas del prompt general.
- **FR-093:** El sistema debe permitir configurar FAQs del tenant y cargarlas
  desde archivo cuando el formato sea soportado.
- **FR-094:** El sistema debe permitir configurar campos a capturar del cliente,
  especialmente durante el funnel de bienvenida.
- **FR-095:** El sistema debe permitir configurar plantillas interactivas de
  WhatsApp, como botones o listas, asociadas a `action_key` y reglas de uso.
- **FR-096:** El sistema debe permitir configurar horario de atencion y
  comportamiento dentro/fuera de horario.
- **FR-097:** El sistema debe permitir configurar reglas de autonomia que definan
  que acciones puede ejecutar la IA sin humano y que acciones requieren
  intervencion.
- **FR-098:** El sistema debe permitir configurar politicas comerciales
  verificadas, incluyendo envios, garantias, cambios, devoluciones, tiempos y
  medios de pago.
- **FR-099:** El sistema debe permitir configurar reglas de escalamiento a humano
  por baja confianza, queja, reclamo, cliente molesto, pago fallido, stock
  incierto o solicitud explicita.
- **FR-100:** El sistema debe permitir configurar productos o categorias
  prioritarias, restringidas o que requieren asesor.
- **FR-101:** El sistema debe ofrecer un modo de prueba para simular
  conversaciones antes de activar cambios de configuracion en produccion.
- **FR-102:** El sistema debe permitir guardar configuracion de IA como borrador
  y publicar una version activa.
- **FR-103:** La IA debe usar catalogo Meta sincronizado, disponibilidad
  operativa, FAQs, reglas de seguridad, funnels y contexto reciente de
  conversacion antes de responder.
- **FR-104:** La IA no debe inventar precios, stock, disponibilidad, links de
  pago, politicas comerciales, agenda ni confirmaciones de pago.
- **FR-105:** La IA debe pedir aclaracion o escalar a humano cuando la confianza
  sea baja o falte informacion para una accion critica.
- **FR-106:** El sistema debe impedir que configuraciones del admin desactiven
  guardrails obligatorios sobre tenant, pagos, inventario, seguridad y no
  invencion.
- **FR-107:** La configuracion de horario de atencion debe permitir definir un
  horario para lunes a viernes y un horario diferente para sabado y domingo.
- **FR-108:** La IA debe aplicar el comportamiento configurado para fuera de
  horario segun el dia y hora local del tenant.
- **FR-109:** El flujo inicial de IA debe poder capturar datos principales del
  cliente y presentar opciones configurables como comprar producto, consultar
  productos o agendar cita mediante menus, botones o listas.

### Integraciones

El modulo Integraciones V1 debe cubrir solo integraciones nativas necesarias para
el flujo critico o la experiencia base. Las automatizaciones perifericas deben
resolverse mediante webhooks salientes y herramientas como n8n.

- **FR-110:** El sistema debe permitir configurar una pasarela de pagos por
  tenant para generar links de pago y recibir confirmaciones por webhook, sin
  quedar limitado como producto a un unico proveedor.
- **FR-111:** El sistema debe cifrar credenciales de pasarela y validar webhooks
  de pago segun el mecanismo de seguridad del proveedor.
- **FR-112:** El sistema debe permitir configurar una integracion de calendario
  por tenant para sincronizar citas cuando este disponible.
- **FR-158:** La integracion de calendario V1 debe contemplar Google Calendar y
  Microsoft Calendar como opciones esperadas por clientes.
- **FR-113:** La ausencia de integracion de calendario no debe bloquear la
  creacion ni visualizacion de citas dentro de Swaflow.
- **FR-114:** El sistema debe permitir configurar correo/notificaciones para
  avisos operativos como compra aprobada, cita creada o eventos relevantes.
- **FR-115:** El sistema debe permitir configurar webhooks salientes por tenant
  para eventos relevantes.
- **FR-116:** Los webhooks salientes deben poder filtrar por tipo de evento,
  estar activos/inactivos y usar firma o secreto cuando se configure.
- **FR-117:** Las fallas de webhooks salientes o automatizaciones de n8n no deben
  romper transacciones criticas ya confirmadas en backend.
- **FR-118:** El sistema debe mantener el backend como fuente de verdad para
  ordenes, pagos, inventario, citas, permisos y estados criticos.
- **FR-119:** Integraciones perifericas como CRM, hojas de calculo, mensajeria
  interna, reportes avanzados o automatizaciones personalizadas deben resolverse
  inicialmente por n8n mediante webhooks/eventos, no como integraciones nativas
  V1.
- **FR-167:** Las pasarelas deben soportarse mediante adaptadores o proveedores
  configurados/certificados por Swateck, no como integraciones arbitrarias sin
  contrato.
- **FR-168:** Todo adaptador de pasarela debe implementar un contrato comun que
  permita crear link de pago, configurar expiracion, validar webhook, mapear
  estados de pago y manejar idempotencia por referencia/transaccion.
- **FR-169:** El sistema debe impedir activar una pasarela si no cuenta con los
  datos minimos para validar webhooks y mapear estados de forma confiable.
- **FR-174:** El contrato tecnico detallado para adaptadores de pasarela debe
  mantenerse en el addendum del PRD y servir como base para arquitectura e
  implementacion.

### Configuracion

El modulo Configuracion V1 debe permitir al admin gestionar la cuenta del tenant,
usuarios, permisos, seguridad y elementos de marca usados por la plataforma y
comunicaciones al cliente.

- **FR-120:** El sistema debe permitir editar datos basicos de empresa del
  tenant, incluyendo nombre comercial y datos de contacto relevantes.
- **FR-121:** El sistema debe permitir configurar logo o marca visual del tenant.
- **FR-122:** El sistema debe permitir configurar zona horaria del tenant.
- **FR-123:** El sistema debe permitir configurar moneda principal del tenant
  para visualizacion y reportes.
- **FR-143:** El sistema debe permitir configurar el modo de negocio del tenant
  como venta de productos, agendamiento de citas o mixto.
- **FR-144:** Los menus, listas, funnels y comportamiento inicial de IA deben
  poder adaptarse al modo de negocio configurado para mostrar opciones
  relevantes como comprar, consultar productos o agendar.
- **FR-124:** El sistema debe permitir cargar una imagen de banner del tenant.
- **FR-125:** El sistema debe permitir cargar una imagen de profile/perfil del
  tenant.
- **FR-126:** Las imagenes de banner y profile deben poder usarse en la
  generacion de correos electronicos enviados a clientes.
- **FR-127:** El sistema debe permitir al admin gestionar usuarios adicionales
  del tenant.
- **FR-128:** Antes o durante la creacion/habilitacion de usuarios adicionales,
  el sistema debe mostrar un mensaje resaltado indicando que cada usuario
  adicional tendra costo mensual.
- **FR-129:** El sistema debe permitir al admin habilitar por usuario acceso a
  modulos restringidos mediante checks, sin cambiar el rol base del usuario.
- **FR-130:** El sistema debe permitir cambio o reseteo de contrasena segun
  permisos del usuario y reglas de seguridad.
- **FR-131:** El sistema debe impedir que usuarios adicionales gestionen
  Configuracion salvo que el admin les conceda acceso explicito a ese modulo.
- **FR-132:** El sistema debe aplicar permisos configurados en la navegacion,
  rutas y acciones de backend, no solo ocultando elementos visuales.

### Roles Y Permisos

- **FR-133:** El sistema debe crear o mantener un usuario admin principal por
  tenant.
- **FR-134:** El admin principal del tenant debe tener acceso a todos los modulos
  V1 de su tenant.
- **FR-135:** El sistema debe permitir usuarios adicionales por tenant.
- **FR-136:** Los usuarios adicionales deben tener acceso por defecto solo a
  Dashboard, Inbox, Productos, Inventario, Ordenes y Citas.
- **FR-137:** Los usuarios adicionales no deben tener acceso por defecto a
  WhatsApp, IA, Funnels, Integraciones ni Configuracion.
- **FR-138:** El admin debe poder habilitar acceso a modulos restringidos por
  usuario mediante checks en Configuracion.
- **FR-139:** Habilitar un modulo restringido a un usuario adicional no debe
  cambiar su rol base.
- **FR-140:** El sistema debe reconocer un rol superadmin de Swateck con acceso
  ilimitado a todos los tenants para soporte y operacion interna.
- **FR-141:** El acceso superadmin debe tratarse como excepcion explicita al
  aislamiento tenant normal y debe quedar sujeto a auditoria.
- **FR-142:** El panel avanzado de SuperUsuario SaaS, incluyendo consumos por
  tenant y reseteo centralizado de admins, queda fuera de V1 y debe planearse
  para V2.
- **FR-170:** En V1, Swateck debe crear cada tenant y su admin principal mediante
  un proceso operativo/admin.
- **FR-171:** El sistema no debe requerir self-service signup de tenants para el
  lanzamiento V1.

### Retencion Y Exportacion

- **FR-159:** Mientras el tenant este activo, el sistema debe conservar de forma
  indefinida mensajes, eventos, archivos y gestiones realizadas en la plataforma,
  salvo que una politica posterior indique lo contrario.
- **FR-160:** Cuando un cliente/tenant se retire, Swaflow debe poder entregar un
  paquete de exportacion con todas las gestiones realizadas en la plataforma.
- **FR-175:** El paquete de exportacion al retiro del tenant debe entregarse como
  archivo ZIP.
- **FR-176:** El ZIP de exportacion debe incluir un archivo TXT por modulo.
- **FR-177:** Cada TXT de exportacion debe listar las interacciones/gestiones del
  modulo delimitadas por pipe `|`, con encabezado de columnas.

## Non-Functional Requirements

### Performance And Response Times

Los siguientes tiempos son una linea base recomendada y ajustable para V1. No
constituyen SLA contractual definitivo hasta que Swateck defina plan comercial,
infraestructura y monitoreo formal.

- **NFR-001:** La navegacion principal y carga de vistas comunes debe responder
  en menos de 2 segundos bajo condiciones normales de operacion.
- **NFR-002:** Las listas principales como Inbox, Ordenes, Citas, Productos e
  Inventario deben cargar o refrescar resultados visibles en menos de 3
  segundos bajo volumen normal de tenant V1.
- **NFR-003:** El Inbox debe reflejar mensajes nuevos, conteos no leidos y
  cambios de estado en menos de 2 segundos desde que el backend los procesa,
  cuando la conexion realtime este activa.
- **NFR-004:** La respuesta automatica de IA por WhatsApp debe apuntar a enviarse
  dentro de 10 segundos desde la recepcion del mensaje entrante en backend,
  excluyendo latencias externas de Meta/OpenAI fuera del control directo de
  Swaflow.
- **NFR-005:** Si la IA no puede responder por error, falta de configuracion o
  timeout, el sistema debe evitar loops y dejar el chat disponible para gestion
  humana.
- **NFR-006:** El Dashboard debe cargar metricas iniciales en menos de 5
  segundos bajo volumen normal de tenant V1.
- **NFR-007:** Cambios de filtros del Dashboard deben devolver resultados en
  menos de 5 segundos bajo volumen normal de tenant V1.
- **NFR-008:** Un webhook de pago valido debe reflejar el estado actualizado de
  la orden en menos de 5 segundos desde que es recibido y validado por backend.
- **NFR-009:** Webhooks salientes y eventos hacia n8n deben ejecutarse de forma
  auxiliar; su latencia no debe bloquear la respuesta de operaciones criticas al
  usuario.

### Security And Tenant Isolation

- **NFR-010:** Toda consulta o accion sobre datos de negocio debe estar aislada
  por `company_id` o mecanismo equivalente de tenant.
- **NFR-011:** Cuando un recurso exista en otro tenant, el sistema debe tratarlo
  como no encontrado para usuarios sin acceso cross-tenant.
- **NFR-012:** El acceso superadmin debe ser una excepcion explicita, limitada a
  usuarios Swateck autorizados y auditable.
- **NFR-013:** Tokens, llaves privadas, secretos de webhooks, credenciales de
  pasarela, calendario, correo y WhatsApp deben almacenarse cifrados.
- **NFR-014:** Secretos y tokens no deben exponerse completos en UI, logs,
  respuestas API, errores ni documentacion generada.
- **NFR-015:** Las rutas autenticadas deben aplicar autorizacion en backend,
  ademas de cualquier restriccion visual en frontend.
- **NFR-016:** Webhooks publicos deben validar token, firma o secreto cuando el
  proveedor lo permita.
- **NFR-017:** Pagos deben validarse con firma/secreto del proveedor y manejarse
  con idempotencia.

### AI Safety And Business Integrity

- **NFR-018:** La IA debe usar backend, catalogo sincronizado, inventario
  operativo y configuracion del tenant como fuentes de verdad para acciones
  comerciales.
- **NFR-019:** La IA no debe ejecutar acciones criticas cuando falten datos
  requeridos o exista baja confianza.
- **NFR-020:** La IA no debe confirmar pagos, alterar inventario ni modificar
  estados criticos sin pasar por servicios backend autorizados.
- **NFR-021:** El sistema debe evitar respuestas automatizadas repetitivas o
  loops cuando fallen OpenAI, WhatsApp o configuracion del agente.

### Reliability And Data Integrity

- **NFR-022:** Ordenes, pagos, inventario y citas deben mantener consistencia
  transaccional en backend.
- **NFR-023:** Reservas de inventario deben liberarse en cancelaciones,
  expiraciones o estados terminales que no retengan producto.
- **NFR-024:** Mensajes entrantes de WhatsApp deben manejar duplicados mediante
  identificadores externos cuando Meta los provea.
- **NFR-025:** Operaciones criticas no deben depender de n8n ni de webhooks
  salientes para confirmarse.
- **NFR-026:** Fallas de integraciones auxiliares deben registrarse y hacerse
  visibles para soporte/admin sin revertir transacciones ya confirmadas.

### Auditability

- **NFR-027:** El sistema debe registrar eventos relevantes de negocio como
  mensajes recibidos/enviados, cambios de estado de orden, pagos, citas,
  asignaciones de chat y cambios de configuracion critica.
- **NFR-028:** Reasignaciones de chat hechas por admin deben quedar registradas
  con usuario, fecha/hora y nuevo responsable.
- **NFR-029:** Cambios de permisos, integraciones, credenciales, IA y funnels
  deben quedar disponibles para auditoria operativa.

### Privacy And Retention

- **NFR-030:** Datos personales de contactos y conversaciones deben limitarse al
  uso operativo del tenant y no compartirse entre tenants.
- **NFR-031:** El PRD V1 debe contemplar una politica configurable o documentada
  de retencion de mensajes, eventos, archivos y gestiones. La politica V1 es
  retencion indefinida mientras el tenant este activo.
- **NFR-032:** Activos de marca cargados por el tenant, como banner y profile,
  deben almacenarse de forma asociada al tenant y no estar disponibles para otros
  tenants.

### Availability And Operations

- **NFR-033:** El sistema debe exponer una verificacion de salud backend para
  monitoreo operativo.
- **NFR-034:** La perdida temporal de OpenAI no debe impedir gestion humana del
  Inbox.
- **NFR-035:** La perdida temporal de calendario externo no debe impedir crear
  citas internas en Swaflow.
- **NFR-036:** La perdida temporal de webhooks salientes/n8n no debe impedir
  crear ordenes, confirmar pagos recibidos por pasarela, gestionar inventario o
  operar conversaciones.

## User Journeys

### UJ-001: Compra Por WhatsApp Con IA Y Pago

**Protagonista:** Laura, cliente final que escribe por WhatsApp a una empresa que
usa Swaflow para vender productos de su catalogo Meta.

**Narrativa:**

Laura escribe por WhatsApp. Swaflow recibe el mensaje por webhook, identifica el
tenant, crea o actualiza el contacto y muestra la conversacion en Inbox. La IA
inicia desde el funnel de bienvenida, saluda, captura los datos principales del
cliente y presenta opciones configurables mediante menu, botones o lista, por
ejemplo comprar un producto, consultar productos o agendar una cita. Laura elige
consultar o comprar un producto. La IA usa el contexto del negocio y consulta el
catalogo sincronizado desde Meta junto con la disponibilidad operativa. Si el
producto existe y tiene disponibilidad, la IA responde con informacion breve y
puede enviar cards nativas de WhatsApp si el producto tiene mapeo Meta valido.

Cuando Laura confirma intencion de compra, el backend valida contacto,
conversacion, producto, cantidad, moneda y disponibilidad. Swaflow crea una orden
pendiente, reserva inventario operativo y genera un link de pago con la pasarela
configurada. La IA envia el link sin inventarlo y el Inbox muestra la orden
relacionada. Si Laura tiene dudas o pide asesor, un usuario puede tomar el chat,
pausar la IA por esa conversacion y responder manualmente.

Cuando la pasarela confirma el pago por webhook valido, Swaflow actualiza la
orden, registra la venta, consume o confirma la reserva de inventario, dispara
eventos internos y actualiza Dashboard. Si existen integraciones auxiliares, se
pueden enviar notificaciones por correo o webhooks hacia n8n sin alterar la
transaccion principal.

Si el link de pago expira sin confirmacion, Swaflow debe reflejar el estado de
la orden y liberar reservas cuando corresponda. La IA puede hacer seguimiento en
la conversacion para preguntar si Laura desea continuar con el pago, generar un
nuevo flujo de pago por backend o agregar otro producto, sin inventar estados ni
confirmar pagos.

**Resultado esperado:**

- Laura recibe respuestas coherentes y un link real de pago.
- El tenant ve la conversacion, orden, estado de pago, venta e inventario
  actualizado.
- La IA no inventa precio, stock ni confirmaciones.
- El asesor puede intervenir y reactivar IA sin perder contexto.
- Si el pago expira, el sistema conserva trazabilidad y permite seguimiento
  comercial sin bloquear el chat.

### UJ-002: Agendamiento De Cita Por WhatsApp

**Protagonista:** Andres, cliente final que escribe por WhatsApp a un negocio que
usa Swaflow para agendar citas.

**Narrativa:**

Andres escribe por WhatsApp y entra al funnel de bienvenida. La IA saluda,
captura los datos principales definidos por el tenant y presenta opciones
configurables mediante menu, botones o lista. Andres elige agendar una cita o lo
solicita directamente en lenguaje natural.

La IA pregunta si prefiere horario de manana o tarde. Con esa preferencia, el
sistema valida disponibilidad. Si el tenant tiene calendario integrado, Swaflow
consulta la disponibilidad del calendario configurado. Si no hay calendario
integrado, Swaflow valida contra las citas internas ya registradas y el horario
operativo compartido del comercio.

Swaflow propone tres opciones con hora al cliente, preferiblemente en dias
diferentes. Andres elige una opcion. El backend crea la cita asociada al contacto
y conversacion, guarda fecha, hora, motivo y estado visible en espanol. Si hay
calendario integrado, intenta sincronizar la cita. Si no lo hay, la cita queda
igualmente visible y operable en el modulo Citas.

**Resultado esperado:**

- Andres recibe opciones reales segun preferencia manana/tarde.
- El tenant ve la cita en el modulo Citas aunque no tenga calendario integrado.
- La IA no inventa disponibilidad; usa calendario externo o disponibilidad
  interna segun configuracion.
- La cita queda conectada al historial del chat y al Dashboard.

### UJ-003: Configuracion Inicial Del Tenant Por Admin

**Protagonista:** Marcela, admin principal de una empresa que acaba de contratar
Swaflow.

**Narrativa:**

Marcela ingresa a Swaflow como admin principal del tenant. En Configuracion
completa los datos de empresa, moneda, zona horaria, marca visual, imagen de
banner e imagen de profile que podran usarse en correos al cliente. Define el
modo de negocio del tenant: venta de productos, agendamiento de citas o mixto.
Configura el horario operativo unico, con horario de lunes a viernes y horario
diferente para sabado y domingo; ese horario aplica al comportamiento de IA y a
la disponibilidad de citas cuando no haya calendario integrado.

Marcela revisa usuarios adicionales. Antes de crearlos, Swaflow muestra un
mensaje resaltado indicando que cada usuario adicional tendra costo mensual. Si
crea usuarios, estos reciben acceso por defecto solo a Dashboard, Inbox,
Productos, Inventario, Ordenes y Citas. Marcela puede habilitar por checks
acceso a WhatsApp, IA, Funnels, Integraciones o Configuracion sin cambiar el rol
base del usuario.

Luego Marcela configura WhatsApp Cloud API con el flujo tecnico disponible en
V1, valida callback, verify token y prueba la cuenta. En Productos sincroniza el
catalogo existente en Meta; Swaflow muestra productos, precios, retailer IDs y
estado de asociacion con WABA. En Inventario revisa la disponibilidad recibida
desde Meta y la disponibilidad operativa calculada.

Marcela configura la IA: identidad, objetivo comercial, contexto, prompt, guia
conversacional, reglas de seguridad, FAQs, menus/listas, reglas de autonomia,
politicas comerciales, escalamiento, productos/categorias prioritarias o
restringidas, modo de prueba y publicacion. Configura el funnel de bienvenida y,
si lo necesita, crea funnels adicionales con criterios de asignacion.

Finalmente configura integraciones V1: pasarela de pagos, calendario si aplica,
correo/notificaciones y webhooks salientes para n8n. Con esto el tenant queda
preparado para recibir mensajes reales, operar conversaciones y medir el flujo
punta a punta desde Dashboard.

**Resultado esperado:**

- Marcela deja el tenant listo para operar el flujo comercial V1.
- Los usuarios y permisos quedan claros antes de generar costos mensuales.
- WhatsApp, IA, catalogo, inventario, funnels e integraciones quedan alineados
  al modo de negocio.
- El sistema evita configuraciones duplicadas de horario y evita que usuarios
  adicionales accedan a modulos restringidos sin permiso.

## Roles And Permissions

### Tenant Admin

Cada tenant tendra un usuario admin principal. Este usuario administra la cuenta
del negocio y tiene acceso a todos los modulos V1 del tenant.

El admin puede crear o gestionar usuarios adicionales. Estos usuarios adicionales
pueden representar un costo adicional de gestion dentro del modelo comercial.

### Usuarios Adicionales Del Tenant

Los usuarios adicionales tendran acceso por defecto solo a:

- Dashboard.
- Inbox.
- Productos.
- Inventario.
- Ordenes.
- Citas.

Los usuarios adicionales no tendran acceso por defecto a:

- WhatsApp.
- IA.
- Funnels.
- Integraciones.
- Configuracion.

El admin podra habilitar acceso a esos modulos mediante checks por usuario en el
area de Configuracion. Esta habilitacion debe ser modular: concede acceso al
modulo seleccionado, pero no cambia el rol base del usuario.

En el area de Configuracion, antes de crear o habilitar usuarios adicionales, el
admin debe ver un mensaje resaltado indicando que cada usuario adicional tendra
costo mensual. El mensaje debe quedar asociado al flujo de gestion de usuarios
para evitar altas accidentales sin conocimiento del impacto comercial.

### Superadmin Swateck

El superadmin pertenece a Swateck y tendra acceso ilimitado a todos los tenants
para soporte, administracion y operacion interna. Este acceso debe tratarse como
una excepcion explicita al aislamiento normal por tenant y debe estar protegido
por permisos y auditoria.

El panel SuperUsuario avanzado queda diferido a V2, pero la capacidad de acceso
superadmin como rol operativo debe existir como requisito transversal.

## Concern Scan

El producto carga las siguientes preocupaciones que deben aparecer en el PRD:

- Aislamiento multi-tenant y prevencion de fuga de datos entre empresas.
- Tiempos de respuesta claros para UI, Inbox, IA, WhatsApp, Dashboard,
  webhooks e integraciones.
- Operaciones criticas de dinero, ordenes, inventario, pagos y citas bajo control
  del backend.
- Guardrails de IA para evitar invenciones sobre precio, stock, disponibilidad,
  pagos, politicas o agenda.
- Handoff humano y desactivacion de IA por conversacion.
- Integracion con WhatsApp/Meta, incluyendo onboarding sencillo via Embedded
  Signup y fallback manual.
- Sincronizacion entre catalogo Meta, productos locales e inventario/reservas.
- Experiencia realtime de inbox, conteos no leidos y estados de conversacion.
- Webhooks salientes, n8n e integraciones externas sin convertirlas en fuente de
  verdad.
- Seguridad de secretos, tokens, webhooks, firmas y permisos por rol.
- Operacion SaaS de superusuario: consumo por tenant, soporte y reseteo de admins.
- Observabilidad basica para ventas, chats, citas, pagos y salud de integraciones.
