# Backend AI Validation

## Hallazgo

El modulo de IA actual esta suficientemente estructurado para ser tratado como base funcional del PRD, no como modulo por disenar desde cero.

## Evidencia Local

- `backend/app/ai/models.py`
  - `AiAgent`: `system_prompt`, `conversation_objective`, `conversation_guide`, `security_rules`, `tone`, `rules`, `active`.
  - `AiInteractiveTemplate`: plantillas de botones/listas con `action_key`, opciones, instrucciones de uso, modo de activacion y campos requeridos.
  - `AiFaqEntry`: FAQs por tenant.
- `backend/app/ai/service.py`
  - Modo de agente unico canonico por tenant.
  - CRUD de agente, FAQs, carga FAQ por CSV/TXT/JSON/XLSX, plantillas interactivas.
- `backend/app/ai/runtime.py`
  - Construye prompt con configuracion del agente, reglas, FAQ, catalogo, inventario, historial y plantillas interactivas.
  - Exige salida JSON con `reply_text`, `action`, `captured_fields`, `product_retailer_ids`.
  - Evita ofrecer productos sin stock real o sin mapeo Meta.
  - Controla saludo inicial, acciones interactivas repetidas y cards de productos.
- `backend/app/ai/tools.py`
  - Herramientas para buscar productos, consultar stock, crear orden y generar link de pago.

## Implicacion Para El PRD

El modulo de IA debe requerir una experiencia de configuracion "de principio a fin" sobre capacidades ya existentes:

- identidad y objetivo del agente,
- contexto del negocio,
- prompt del sistema,
- guia conversacional,
- reglas de seguridad,
- FAQs externas,
- plantillas interactivas,
- reglas de handoff,
- campos a capturar,
- relacion con funnels,
- limites para no inventar precios, stock, disponibilidad ni pagos.

