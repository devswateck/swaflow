# PRD Quality Review — Swaflow

## Overall verdict

El PRD ya es decision-ready en la mayor parte del alcance funcional: V1/V2, modulos, roles, journeys, guardrails de IA, n8n auxiliar y flujo punta a punta estan claramente definidos. El riesgo principal antes de usarlo para UX/arquitectura/epicas es que algunas decisiones operativas de lanzamiento siguen demasiado implicitas: provisionamiento de tenants, estrategia de pasarelas "cualquier proveedor" y contrato real de disponibilidad Meta.

## Decision-readiness — adequate

El PRD toma decisiones claras: SuperUsuario avanzado va a V2, WhatsApp V1 conserva configuracion tecnica, productos nacen en Meta, n8n no es fuente de verdad, horario operativo es unico, y retencion es indefinida mientras el tenant este activo. Tambien registra contrametricas y NFRs concretos.

### Findings

- **high** Provisionamiento comercial de tenants no esta decidido (§ Product Scope / UJ-003) — El PRD dice que debe existir "una forma minima operativa de crear/soportar tenants" y el journey empieza cuando Marcela "ingresa a Swaflow", pero no define quien crea el tenant, si es manual por Swateck, si hay flujo de onboarding interno, ni que queda fuera de self-service. *Fix:* agregar una decision V1: provisionamiento manual por Swateck o flujo admin minimo, y declarar self-service signup como V2 si aplica.
- **high** Estrategia de pasarelas queda abierta para implementacion (§ Integraciones FR-110) — "sin quedar limitado como producto a un unico proveedor" respeta la vision, pero no define el contrato minimo para soportar multiples pasarelas ni que significa "la pasarela que desee" en V1. *Fix:* especificar que V1 soporta proveedores mediante adaptadores certificados/configurados por Swaflow, con contrato comun para crear link, validar webhook, mapear estados e idempotencia.

## Substance over theater — strong

El PRD no lee como plantilla generica. Las decisiones vienen de restricciones reales: catalogo Meta, reservas operativas, IA con contexto, permisos por modulo, usuarios con costo mensual, horarios compartidos, Google/Microsoft calendar, links de pago expirados y n8n como periferia.

### Findings

- **low** La seccion "Modulos Indicados Por El Usuario" conserva texto de intake (§ Discovery Intake) — Es util como historico, pero puede duplicar o contradecir secciones finales si se lee como especificacion activa. *Fix:* marcarla claramente como intake historico o moverla al addendum antes de finalizar.

## Strategic coherence — strong

La tesis es consistente: Swaflow vende el flujo conversacional completo por WhatsApp para negocios de producto, citas o mixtos. Los modulos sirven a esa tesis y el exito se mide como punta a punta, no por funcionalidades aisladas.

### Findings

_Sin hallazgos sustantivos._

## Done-ness clarity — adequate

La mayoria de FRs son verificables y los NFRs tienen umbrales. Hay buenas consecuencias esperadas para pagos, inventario, IA, roles y journeys. El punto mas debil es que algunas integraciones externas necesitan contratos de "done" mas concretos.

### Findings

- **medium** Disponibilidad Meta necesita contrato de fallback mas preciso (§ Inventario FR-045, FR-047, FR-052) — El PRD exige disponibilidad base desde Meta, pero no define que pasa si Meta solo devuelve estado/availability y no cantidad confiable para reserva operativa. *Fix:* definir si disponibilidad Meta puede ser booleana/estado y como Swaflow calcula cantidad/reserva cuando no hay cantidad numerica.
- **medium** Paquete de exportacion al retiro no tiene contenido minimo (§ Retencion y Exportacion FR-160) — La obligacion existe, pero no se sabe si incluye CSV/JSON, mensajes, contactos, ordenes, citas, eventos, archivos, imagenes, logs y metadata. *Fix:* agregar contenido minimo y formato esperado, aunque el mecanismo tecnico quede para arquitectura.

## Scope honesty — adequate

V1/V2 esta bien separado para SuperUsuario avanzado y WhatsApp Embedded Signup. Tambien hay decisiones diferidas no bloqueantes. Falta una seccion explicita de Non-Goals para evitar que lectores infieran CRM, ERP, omnicanal o self-service completo.

### Findings

- **medium** Non-Goals V1 no esta centralizado (§ Product Scope) — La informacion existe en fuente historica y V2, pero no hay una lista clara de lo que V1 no hara. *Fix:* agregar Non-Goals V1: panel SuperUsuario avanzado, popup Meta, omnicanal, CRM/ERP avanzado, builder visual, RAG, voz, automatizaciones criticas en n8n y creacion de productos fuera de Meta.

## Downstream usability — adequate

FRs, NFRs y UJs tienen IDs y protagonistas. Los modulos son extraibles para UX/arquitectura. La principal friccion es mecanica: IDs agregados tarde no estan en orden ascendente dentro de todos los modulos y hay narrativa duplicada de roles.

### Findings

- **low** IDs FR fuera de orden local (§ Functional Requirements) — Los IDs son unicos, pero FR-153/154 aparecen antes de FR-145/146, y FR-158 aparece dentro de Integraciones antes de FR-113. *Fix:* renumerar mecanicamente antes de generar epicas o mantener un indice de FRs.
- **low** Roles aparece como FRs y narrativa separada (§ Roles Y Permisos / Roles And Permissions) — La duplicacion es entendible, pero puede divergir. *Fix:* mantener FRs como fuente normativa y convertir la narrativa final en resumen, o moverla al addendum.

## Shape fit — strong

La forma encaja con un PRD chain-top para SaaS B2B modular: FRs por modulo, NFRs transversales, UJs con protagonistas y reconciliacion de insumos. La extension esta justificada por el alcance de lanzamiento comercial.

### Findings

_Sin hallazgos sustantivos._

## Mechanical notes

- No hay `[ASSUMPTION]` tags pendientes.
- No hay FRs duplicados en lineas de requisito.
- El documento tiene acentos omitidos por estilo ASCII; consistente con el resto de artefactos.

