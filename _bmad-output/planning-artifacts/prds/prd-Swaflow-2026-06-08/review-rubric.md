# Revisión de calidad del PRD - Swaflow

## Veredicto general

El PRD ya está listo para decisión en la mayor parte del alcance funcional: V1/V2, módulos, roles, recorridos, guardrails de IA, n8n auxiliar y flujo punta a punta están definidos con claridad. El principal riesgo antes de usarlo para UX, arquitectura y épicas es que algunas decisiones operativas de lanzamiento siguen demasiado implícitas: provisionamiento de tenants, estrategia de pasarelas "cualquier proveedor" y contrato real de disponibilidad de Meta.

## Preparación para decisión - adecuada

El PRD toma decisiones claras: el SuperUsuario avanzado va a V2, WhatsApp V1 conserva la configuración técnica, los productos nacen en Meta, n8n no es fuente de verdad, el horario operativo es único y la retención es indefinida mientras el tenant esté activo. También registra contramétricas y NFRs concretos.

### Hallazgos

- **alto** El provisionamiento comercial de tenants no está decidido (§ Product Scope / UJ-003) — El PRD dice que debe existir "una forma mínima operativa de crear/soportar tenants" y el journey empieza cuando Marcela "ingresa a Swaflow", pero no define quién crea el tenant, si es manual por Swateck, si hay flujo de onboarding interno ni qué queda fuera de self-service. *Fix:* agregar una decisión V1: provisionamiento manual por Swateck o flujo admin mínimo, y declarar self-service signup como V2 si aplica.
- **alto** La estrategia de pasarelas queda abierta para implementación (§ Integraciones FR-110) — "sin quedar limitado como producto a un único proveedor" respeta la visión, pero no define el contrato mínimo para soportar múltiples pasarelas ni qué significa "la pasarela que desee" en V1. *Fix:* especificar que V1 soporta proveedores mediante adaptadores certificados/configurados por Swaflow, con contrato común para crear enlace, validar webhook, mapear estados e idempotencia.

## Sustancia sobre forma - fuerte

El PRD no se lee como una plantilla genérica. Las decisiones vienen de restricciones reales: catálogo Meta, reservas operativas, IA con contexto, permisos por módulo, usuarios con costo mensual, horarios compartidos, Google/Microsoft Calendar, enlaces de pago expirados y n8n como periferia.

### Hallazgos

- **bajo** La sección "Módulos indicados por el usuario" conserva texto de intake (§ Discovery Intake) — Es útil como histórico, pero puede duplicar o contradecir secciones finales si se lee como especificación activa. *Fix:* marcarla claramente como intake histórico o moverla al addendum antes de finalizar.

## Coherencia estratégica - fuerte

La tesis es consistente: Swaflow vende el flujo conversacional completo por WhatsApp para negocios de producto, citas o mixtos. Los módulos sirven a esa tesis y el éxito se mide como punta a punta, no por funcionalidades aisladas.

### Hallazgos

_Sin hallazgos sustantivos._

## Claridad de terminado - adecuada

La mayoría de FRs son verificables y los NFRs tienen umbrales. Hay buenas consecuencias esperadas para pagos, inventario, IA, roles y journeys. El punto más débil es que algunas integraciones externas necesitan contratos de "done" más concretos.

### Hallazgos

- **medio** La disponibilidad de Meta necesita un contrato de fallback más preciso (§ Inventario FR-045, FR-047, FR-052) — El PRD exige disponibilidad base desde Meta, pero no define qué pasa si Meta solo devuelve estado/disponibilidad y no cantidad confiable para reserva operativa. *Fix:* definir si la disponibilidad de Meta puede ser booleana/estado y cómo Swaflow calcula cantidad/reserva cuando no hay cantidad numérica.
- **medio** El paquete de exportación al retiro no tiene contenido mínimo (§ Retención y exportación FR-160) — La obligación existe, pero no se sabe si incluye CSV/JSON, mensajes, contactos, órdenes, citas, eventos, archivos, imágenes, logs y metadata. *Fix:* agregar contenido mínimo y formato esperado, aunque el mecanismo técnico quede para arquitectura.

## Honestidad de alcance - adecuada

V1/V2 está bien separado para SuperUsuario avanzado y WhatsApp Embedded Signup. También hay decisiones diferidas no bloqueantes. Falta una sección explícita de No objetivos para evitar que los lectores infieran CRM, ERP, omnicanal o self-service completo.

### Hallazgos

- **medio** No objetivos V1 no están centralizados (§ Product Scope) — La información existe en la fuente histórica y en V2, pero no hay una lista clara de lo que V1 no hará. *Fix:* agregar No objetivos V1: panel SuperUsuario avanzado, popup de Meta, omnicanal, CRM/ERP avanzado, builder visual, RAG, voz, automatizaciones críticas en n8n y creación de productos fuera de Meta.

## Usabilidad aguas abajo - adecuada

Los FR, NFR y UJ tienen IDs y protagonistas. Los módulos son extraíbles para UX y arquitectura. La principal fricción es mecánica: IDs agregados tarde no están en orden ascendente dentro de todos los módulos y hay narrativa duplicada de roles.

### Hallazgos

- **bajo** IDs FR fuera de orden local (§ Functional Requirements) — Los IDs son únicos, pero FR-153/154 aparecen antes de FR-145/146, y FR-158 aparece dentro de Integraciones antes de FR-113. *Fix:* renumerar mecánicamente antes de generar épicas o mantener un índice de FRs.
- **bajo** Roles aparece como FRs y narrativa separada (§ Roles y permisos / Roles and Permissions) — La duplicación es entendible, pero puede divergir. *Fix:* mantener los FRs como fuente normativa y convertir la narrativa final en resumen, o moverla al addendum.

## Ajuste de forma - fuerte

La forma encaja con un PRD chain-top para SaaS B2B modular: FR por módulo, NFR transversales, UJs con protagonistas y reconciliación de insumos. La extensión está justificada por el alcance de lanzamiento comercial.

### Hallazgos

_Sin hallazgos sustantivos._

## Notas mecánicas

- No hay `[ASSUMPTION]` pendientes.
- No hay FR duplicados en líneas de requisito.
- El documento conserva acentos omitidos por estilo ASCII; consistente con el resto de artefactos.
