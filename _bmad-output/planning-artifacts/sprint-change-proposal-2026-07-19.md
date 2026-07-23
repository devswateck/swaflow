# Sprint Change Proposal - Inbox y shell conversacional

**Proyecto:** Swaflow  
**Fecha:** 2026-07-19  
**Estado:** Aprobado para implementacion  
**Alcance:** Ajuste moderado de UX y frontend

## 1. Resumen del problema

Durante la revision visual del Inbox y del shell global se detecto una sobrecarga de tarjetas informativas que rompe la jerarquia de trabajo. En lugar de ver el chat primero, el usuario ve tres cuadros grandes para `Responsable humano`, `IA` y `Clasificación comercial`, lo que ocupa el espacio principal y desplaza el hilo de mensajes y el composer fuera de foco.

La evidencia viene de las capturas compartidas y de la implementacion actual:

- El header global muestra buscador y campana sin una accion explicita visible, y la campana no despliega contexto operativo.
- El Inbox renderiza tres tarjetas densas en la parte superior del detalle y tres tarjetas repetidas por conversacion en la lista.
- El composer no destaca lo suficiente como area principal de escritura, por lo que el chat se siente incompleto.
- Los labels de accion no reflejan la nomenclatura pedida por negocio: `Tomar humano` y `Pasar a IA`.

El resultado es una pantalla visualmente pesada, con baja jerarquia y poca claridad sobre donde responder, donde cambiar el estado de IA y donde cambiar el funnel.

## 2. Impacto

### Impacto en épicas

- **Epic 2: Inbox y Operacion Conversacional** es la principal afectada.
- **Epic 8: Estabilizacion Operativa y Endurecimiento del Inbox** puede requerir ajuste menor si se decide formalizar la campana de notificaciones o el estado de busqueda.
- El resto de epicas no cambian funcionalmente, pero si pueden heredar el nuevo patron visual del shell.

### Impacto en historias

- **Historia 2.1: Ver y actualizar conversaciones en tiempo real**
  - Debe cambiar la presentacion del detalle para que el chat y el composer sean la superficie principal.
  - Debe quedar claro que el estado de IA, responsable y clasificacion viven como tags compactos, no como cards grandes.
- **Historia 2.2: Responder manualmente desde el Inbox**
  - Debe reforzarse la visibilidad del composer y el manejo del borrador.
- **Historia 2.3: Desactivar, reactivar y continuar la IA en una conversacion**
  - Debe renombrarse el CTA segun el estado: `Tomar humano` / `Pasar a IA`.
- **Historia 2.4: Asignar, tomar y reasignar chats por usuario**
  - El estado de responsable debe pasar a tag compacto en la cabecera, con accion clara al costado.
- **Historia 2.5: Clasificar conversaciones y preparar agenda desde el hilo**
  - El funnel debe moverse a un tag o control compacto en la barra superior del chat.

### Impacto en artefactos

- **PRD**: no cambia el objetivo del producto, pero conviene explicitar que el Inbox debe priorizar el chat y no tarjetas densas de estado.
- **Arquitectura frontend**: ya define Inbox como workspace de tres zonas; esta propuesta alinea la implementacion con esa estructura.
- **UX DESIGN / EXPERIENCE**: requiere actualizar el patron de Inbox para tags compactos, composer visible y header con acciones claras.
- **Frontend implementation brief**: debe reflejar la nueva jerarquia de la pantalla y la desambiguacion de search / notifications.

### Impacto tecnico

- Ajuste de layout en `frontend/src/App.tsx` para reorganizar el detalle del Inbox.
- Posible extraccion de primitives `Badge`, `Tag`, `Composer`, `HeaderActions` o `RailAction`.
- Cambio de comportamiento del header global para que búsqueda y campana no parezcan elementos decorativos.
- No se identifican cambios obligatorios de backend para este corte.

## 3. Recomendacion

**Ruta recomendada: Ajuste directo.**

### Por que

- El problema es de jerarquia visual y nomenclatura, no de modelo de dominio.
- El alcance se resuelve dentro del shell y del Inbox sin reescribir flujos criticos.
- Hay alineacion clara con el PRD y la arquitectura existente; el cambio corrige la ejecucion, no la estrategia.
- Revertir trabajo no aporta valor: el problema no es que el flujo exista, sino que esta representado con mala densidad.

### Estimacion

- **Esfuerzo:** Medio
- **Riesgo:** Bajo a medio
- **Impacto en timeline:** acotado, principalmente frontend y redaccion de UX/epics

### Criterio de exito

- El Inbox se lee primero como chat, no como panel de estado.
- Los estados `Responsable humano`, `IA activa` y `Clasificación comercial` pasan a tags pequeños en la parte superior.
- El composer queda visible y prominente.
- El CTA de handoff usa la nomenclatura pedida por negocio.
- La campana deja de ser un icono sin contexto.
- La busqueda tiene una funcion clara o se degrada a un control secundario con proposito definido.

## 4. Propuestas de cambio detalladas

### 4.1 PRD

**Seccion:** Requisitos funcionales > Inbox

**Texto actual relevante:**
- FR-009, FR-010, FR-011, FR-012, FR-013, FR-016, FR-017 cubren la operacion del Inbox, pero no fijan la jerarquia visual ni la ubicacion del composer.

**Propuesta:**
- Agregar una nota de experiencia al bloque Inbox:
  - El detalle de una conversacion debe priorizar el hilo de mensajes y el composer.
  - El estado de IA, responsable humano y clasificacion comercial deben mostrarse como tags compactos en la cabecera o barra superior del chat.
  - Las acciones de handoff y funnel deben permanecer visibles sin ocupar el espacio principal del hilo.

**Razon:** evita interpretaciones que lleven a tarjetas grandes y a un chat visualmente fragmentado.

### 4.2 Epics / Stories

**Historia 2.1: Ver y actualizar conversaciones en tiempo real**

**OLD**
- El sistema muestra contacto, ultimo mensaje, fecha y hora de ultima actividad, estado, no leidos y funnel cuando exista.
- La lista prioriza la actividad reciente.
- El sistema muestra el historial de mensajes entrantes, respuestas de IA, mensajes de asesores, mensajes interactivos y eventos relevantes.

**NEW**
- El sistema muestra contacto, ultimo mensaje, fecha y hora de ultima actividad, estado, no leidos y funnel cuando exista.
- La lista prioriza la actividad reciente.
- En el detalle, el hilo de mensajes ocupa la superficie principal.
- El estado de responsable humano, IA y clasificacion comercial se muestra como tags compactos en la parte superior del chat.
- El composer permanece visible y accesible bajo el hilo.

**Razon:** alinea la historia con la jerarquia real requerida por la UX.

**Historia 2.2: Responder manualmente desde el Inbox**

**OLD**
- El usuario envia mensajes manuales desde el Inbox y el sistema registra el mensaje como parte del historial.

**NEW**
- El usuario envia mensajes manuales desde el Inbox y el sistema registra el mensaje como parte del historial.
- El composer debe ser visualmente prioritario, pequeno y claro, con error inline y preservacion de borrador si falla el envio.

**Razon:** el valor central del chat es escribir, no navegar tarjetas de estado.

**Historia 2.3: Desactivar, reactivar y continuar la IA en una conversacion**

**OLD**
- El usuario desactiva la IA y luego la reactiva desde el mismo contexto.

**NEW**
- El usuario desactiva la IA y luego la reactiva desde el mismo contexto.
- El CTA visible debe usar la nomenclatura `Tomar humano` cuando el chat pasa a gestion humana y `Pasar a IA` cuando se devuelve al agente.

**Razon:** reduce ambiguedad operativa y mejora la lectura en produccion.

**Historia 2.4: Asignar, tomar y reasignar chats por usuario**

**OLD**
- El sistema diferencia claramente chats disponibles, asignados a el y asignados a otros.

**NEW**
- El sistema diferencia claramente chats disponibles, asignados a el y asignados a otros.
- El estado de responsable se expresa como tag compacto en la barra superior del chat, no como tarjeta dominante.

**Razon:** el responsable es contexto, no bloque principal.

**Historia 2.5: Clasificar conversaciones y preparar agenda desde el hilo**

**OLD**
- El sistema muestra el funnel y la etapa actuales.
- El usuario puede ajustar manualmente la clasificacion.

**NEW**
- El sistema muestra el funnel y la etapa actuales.
- El funnel y la etapa se representan como tag o selector compacto en la cabecera superior del chat.
- La accion de agenda no compite visualmente con el hilo ni con el composer.

**Razon:** la clasificacion debe ser visible pero secundaria frente al chat.

### 4.3 UX / Experience

**Archivos a actualizar:**
- `DESIGN.md`
- `EXPERIENCE.md`
- `frontend-implementation-brief.md`

**Cambios propuestos:**
- Reemplazar los tres cuadros grandes del Inbox por tags pequenos en la cabecera del chat.
- Mantener el hilo como area dominante.
- Reubicar el composer en la parte inferior con jerarquia visual clara.
- Renombrar las acciones de handoff a `Tomar humano` y `Pasar a IA`.
- Mostrar funnel como tag o selector pequeño al costado derecho del nombre en la barra superior.
- Definir una regla explicita para la campana:
  - o despliega un panel con notificaciones relevantes,
  - o se oculta hasta tener una accion real.
- Definir una regla explicita para busqueda:
  - o se convierte en busqueda operativa util,
  - o se relega a un control secundario con alcance claro.

**Razon:** el UX actual mezcla elementos decorativos con elementos de trabajo.

### 4.4 Frontend

**Archivo principal:** `frontend/src/App.tsx`

**Cambios propuestos:**
- Sustituir los paneles `Responsable humano`, `IA` y `Clasificación comercial` por una fila compacta de tags.
- Mantener solo el chat visible como contenido principal del detalle.
- Mover acciones de handoff y funnel al encabezado del chat o a una mini barra contextual.
- Agregar composer visible y pequeño debajo del hilo.
- Implementar un dropdown o estado util para la campana, o retirar el icono si no hay flujo real.
- Revisar el campo de busqueda para que no parezca un adorno sin efecto.

## 5. Handoff de implementación

**Clasificacion de alcance:** Moderado

**Destino principal:** Developer agent

**Responsabilidades:**

- Ajustar layout y jerarquia visual del Inbox.
- Reducir las cards densas a tags compactos.
- Alinear CTA y copy de handoff con la nomenclatura pedida.
- Resolver el comportamiento de search y notifications en el shell.
- Verificar que el composer quede visible y funcional.

**Apoyo requerido:**

- Product / UX si se decide formalizar la regla final de campana y búsqueda.
- Arquitectura solo si el equipo quiere convertir estos controles en patrones reutilizables globales.

**Success criteria para cierre:**

- El chat vuelve a ser la superficie principal.
- No quedan cards grandes para responsable / IA / clasificacion.
- El composer es visible sin scroll extra.
- Los controles superiores tienen proposito claro.
- La implementacion sigue alineada con PRD, Epic 2 y el spine UX.
- La propuesta queda lista para que Developer ejecute el cambio en frontend.
