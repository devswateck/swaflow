# Validación del backend de IA

## Hallazgo

El módulo de IA actual está suficientemente estructurado para tratarse como base funcional del PRD, no como un módulo por diseñar desde cero.

## Evidencia local

- `backend/app/ai/models.py` - `AiAgent`: `system_prompt`, `conversation_objective`, `conversation_guide`, `security_rules`, `tone`, `rules`, `active`.
- `AiInteractiveTemplate`: plantillas de botones/listas con `action_key`, opciones, instrucciones de uso, modo de activación y campos requeridos.
- `AiFaqEntry`: FAQs por tenant.
- `backend/app/ai/service.py` - modo de agente único canónico por tenant.
- CRUD del agente, FAQs, carga de FAQ por CSV/TXT/JSON/XLSX, plantillas interactivas.
- `backend/app/ai/runtime.py` - construye el prompt con configuración del agente, reglas, FAQ, catálogo, inventario, historial y plantillas interactivas.
- Exige salida JSON con `reply_text`, `action`, `captured_fields`, `product_retailer_ids`.
- Evita ofrecer productos sin stock real o sin mapeo Meta.
- Controla saludo inicial, acciones interactivas repetidas y cards de productos.
- `backend/app/ai/tools.py` - herramientas para buscar productos, consultar stock, crear orden y generar enlace de pago.

## Implicación para el PRD

El módulo de IA debe requerir una experiencia de configuración "de principio a fin" sobre capacidades ya existentes:

- identidad y objetivo del agente,
- contexto del negocio,
- prompt del sistema,
- guía conversacional,
- reglas de seguridad,
- FAQs externas,
- plantillas interactivas,
- reglas de handoff,
- campos a capturar,
- relación con funnels,
- límites para no inventar precios, stock, disponibilidad ni pagos.
