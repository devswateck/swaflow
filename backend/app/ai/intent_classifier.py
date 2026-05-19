from app.ai.schemas import IntentClassifyResponse


KEYWORDS_BY_INTENT = {
    "buy_product": ["comprar", "quiero", "pagar", "me llevo", "precio", "vale"],
    "ask_product_info": ["tienes", "disponible", "color", "talla", "info", "informacion"],
    "schedule_appointment": ["cita", "agenda", "agendar", "llamada", "reunion"],
    "request_human": ["asesor", "humano", "persona", "agente"],
    "support": ["soporte", "ayuda", "problema", "garantia"],
    "complaint": ["queja", "molesto", "reclamo", "malo", "demora"],
}


def classify_intent(message: str) -> IntentClassifyResponse:
    normalized = message.lower()
    matches: list[tuple[str, int]] = []
    for intent, keywords in KEYWORDS_BY_INTENT.items():
        score = sum(1 for keyword in keywords if keyword in normalized)
        if score:
            matches.append((intent, score))
    if not matches:
        return IntentClassifyResponse(intent="unknown", confidence=0.4, entities={})
    intent, score = max(matches, key=lambda item: item[1])
    confidence = min(0.95, 0.65 + (score * 0.1))
    return IntentClassifyResponse(intent=intent, confidence=confidence, entities={})

