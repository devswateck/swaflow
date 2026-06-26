from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import re

MANDATORY_GUARDRAILS = {
    "tenant_isolation": True,
    "payments_locked_to_backend": True,
    "inventory_reserved_by_backend": True,
    "no_invention": True,
    "no_manual_payment_confirmation": True,
}

DEFAULT_WEEKDAY_WINDOW = {"start": "08:00", "end": "18:00"}
DEFAULT_WEEKEND_WINDOW = {"start": "08:00", "end": "14:00"}
DEFAULT_OUTSIDE_HOURS_MESSAGE = "Estamos fuera de horario. Te respondemos apenas retomemos atencion."
DEFAULT_HANDOFF_MESSAGE = "Te paso con una persona del equipo para continuar."
ALLOWED_OUTSIDE_HOURS_BEHAVIORS = {"handoff", "hold", "auto_reply"}
ALLOWED_INSIDE_HOURS_BEHAVIORS = {"normal", "priority"}
ALLOWED_OPERATIONAL_STATUS = {"draft", "published"}
DEFAULT_MIN_CONFIDENCE = 0.75
DEFAULT_CRITICAL_INTENTS = ["buy_product", "schedule_appointment", "request_human", "complaint"]
DEFAULT_REQUIRED_CAPTURE_FIELDS = ["nombre", "correo", "ciudad"]

TIME_PATTERN = re.compile(r"^(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?$")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if isinstance(value, str):
        return value.strip()
    return default


def _normalize_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "si", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return default


def _normalize_float(value: Any, *, default: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if numeric != numeric:
        return default
    return max(0.0, min(numeric, 1.0))


def _normalize_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _normalize_text(item)
        if text:
            result.append(text)
    return result


def _normalize_clock(value: Any, *, default: str) -> str:
    text = _normalize_text(value, default=default)
    match = TIME_PATTERN.match(text)
    if match is None:
        return default
    hour = int(match.group("hour"))
    minute = int(match.group("minute") or 0)
    if hour > 23 or minute > 59:
        return default
    return f"{hour:02d}:{minute:02d}"


def _normalize_window(value: Any, *, default: dict[str, str]) -> dict[str, str]:
    if isinstance(value, dict):
        return {
            "start": _normalize_clock(value.get("start"), default=default["start"]),
            "end": _normalize_clock(value.get("end"), default=default["end"]),
        }
    if isinstance(value, str) and "-" in value:
        start_raw, end_raw = value.split("-", 1)
        return {
            "start": _normalize_clock(start_raw, default=default["start"]),
            "end": _normalize_clock(end_raw, default=default["end"]),
        }
    return dict(default)


def _normalize_timezone(value: Any, *, fallback: str | None) -> str:
    timezone = _normalize_text(value, default=fallback or "UTC")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        return fallback or "UTC"
    return timezone


def _normalize_section(default: dict[str, Any], value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        merged = deepcopy(default)
        merged.update(value)
        return merged
    return deepcopy(default)


def _normalize_security(value: Any) -> dict[str, Any]:
    section = _normalize_section(
        {
            "mandatory_guardrails": dict(MANDATORY_GUARDRAILS),
            "custom_rules": "",
        },
        value,
    )
    guardrails = section.get("mandatory_guardrails")
    if isinstance(guardrails, dict):
        normalized_guardrails = dict(MANDATORY_GUARDRAILS)
        for key in normalized_guardrails:
            normalized_guardrails[key] = _normalize_bool(
                guardrails.get(key), default=normalized_guardrails[key]
            )
        section["mandatory_guardrails"] = normalized_guardrails
    else:
        section["mandatory_guardrails"] = dict(MANDATORY_GUARDRAILS)
    section["custom_rules"] = _normalize_text(section.get("custom_rules"))
    return section


def _normalize_schedule(value: Any, *, fallback_timezone: str | None) -> dict[str, Any]:
    section = _normalize_section(
        {
            "timezone": _normalize_timezone(None, fallback=fallback_timezone),
            "weekday": dict(DEFAULT_WEEKDAY_WINDOW),
            "weekend": dict(DEFAULT_WEEKEND_WINDOW),
            "outside_hours_behavior": "handoff",
            "inside_hours_behavior": "normal",
            "outside_hours_message": DEFAULT_OUTSIDE_HOURS_MESSAGE,
            "handoff_message": DEFAULT_HANDOFF_MESSAGE,
        },
        value,
    )
    section["timezone"] = _normalize_timezone(section.get("timezone"), fallback=fallback_timezone)
    section["weekday"] = _normalize_window(section.get("weekday"), default=DEFAULT_WEEKDAY_WINDOW)
    section["weekend"] = _normalize_window(section.get("weekend"), default=DEFAULT_WEEKEND_WINDOW)
    outside_behavior = _normalize_text(section.get("outside_hours_behavior"), default="handoff").lower()
    section["outside_hours_behavior"] = (
        outside_behavior if outside_behavior in ALLOWED_OUTSIDE_HOURS_BEHAVIORS else "handoff"
    )
    inside_behavior = _normalize_text(section.get("inside_hours_behavior"), default="normal").lower()
    section["inside_hours_behavior"] = (
        inside_behavior if inside_behavior in ALLOWED_INSIDE_HOURS_BEHAVIORS else "normal"
    )
    section["outside_hours_message"] = _normalize_text(
        section.get("outside_hours_message"), default=DEFAULT_OUTSIDE_HOURS_MESSAGE
    )
    section["handoff_message"] = _normalize_text(
        section.get("handoff_message"), default=DEFAULT_HANDOFF_MESSAGE
    )
    return section


def _normalize_autonomy(value: Any) -> dict[str, Any]:
    section = _normalize_section(
        {
            "allow_critical_actions": False,
            "critical_intents": list(DEFAULT_CRITICAL_INTENTS),
            "min_confidence": DEFAULT_MIN_CONFIDENCE,
            "required_capture_fields": list(DEFAULT_REQUIRED_CAPTURE_FIELDS),
        },
        value,
    )
    section["allow_critical_actions"] = _normalize_bool(
        section.get("allow_critical_actions"), default=False
    )
    section["critical_intents"] = _normalize_list(section.get("critical_intents")) or list(
        DEFAULT_CRITICAL_INTENTS
    )
    section["min_confidence"] = _normalize_float(
        section.get("min_confidence"), default=DEFAULT_MIN_CONFIDENCE
    )
    section["required_capture_fields"] = _normalize_list(section.get("required_capture_fields"))
    return section


def _normalize_escalation(value: Any) -> dict[str, Any]:
    section = _normalize_section(
        {
            "low_confidence": True,
            "complaint": True,
            "payment_failed": True,
            "stock_uncertain": True,
            "explicit_human_request": True,
            "handoff_message": DEFAULT_HANDOFF_MESSAGE,
            "clarification_message": "Necesito un poco mas de informacion para ayudarte mejor.",
        },
        value,
    )
    for key in (
        "low_confidence",
        "complaint",
        "payment_failed",
        "stock_uncertain",
        "explicit_human_request",
    ):
        section[key] = _normalize_bool(section.get(key), default=True)
    section["handoff_message"] = _normalize_text(
        section.get("handoff_message"), default=DEFAULT_HANDOFF_MESSAGE
    )
    section["clarification_message"] = _normalize_text(
        section.get("clarification_message"),
        default="Necesito un poco mas de informacion para ayudarte mejor.",
    )
    return section


def _normalize_policies(value: Any) -> dict[str, Any]:
    section = _normalize_section(
        {"shipping": "", "warranty": "", "returns": "", "payments": ""},
        value,
    )
    for key in ("shipping", "warranty", "returns", "payments"):
        section[key] = _normalize_text(section.get(key))
    return section


def _normalize_priorities(value: Any) -> dict[str, Any]:
    section = _normalize_section(
        {"priority_categories": [], "restricted_categories": []},
        value,
    )
    section["priority_categories"] = _normalize_list(section.get("priority_categories"))
    section["restricted_categories"] = _normalize_list(section.get("restricted_categories"))
    return section


def _normalize_test_mode(value: Any) -> dict[str, Any]:
    section = _normalize_section(
        {"enabled": False, "simulation_note": ""},
        value,
    )
    section["enabled"] = _normalize_bool(section.get("enabled"), default=False)
    section["simulation_note"] = _normalize_text(section.get("simulation_note"))
    return section


def normalize_operational_section(value: Any, *, fallback_timezone: str | None = None) -> dict[str, Any]:
    return {
        "security": _normalize_security(value.get("security") if isinstance(value, dict) else None),
        "schedule": _normalize_schedule(
            value.get("schedule") if isinstance(value, dict) else None,
            fallback_timezone=fallback_timezone,
        ),
        "autonomy": _normalize_autonomy(value.get("autonomy") if isinstance(value, dict) else None),
        "escalation": _normalize_escalation(value.get("escalation") if isinstance(value, dict) else None),
        "policies": _normalize_policies(value.get("policies") if isinstance(value, dict) else None),
        "priorities": _normalize_priorities(value.get("priorities") if isinstance(value, dict) else None),
        "test_mode": _normalize_test_mode(value.get("test_mode") if isinstance(value, dict) else None),
    }


def _is_legacy_operational_rule(key: str) -> bool:
    return key in {
        "guardrails",
        "schedule",
        "timezone",
        "handoff_rule",
        "min_confidence",
        "required_capture_fields",
        "critical_intents",
        "shipping_policy",
        "warranty_policy",
        "returns_policy",
        "payments_policy",
        "priority_categories",
        "restricted_categories",
        "test_mode",
        "simulation_note",
    }


def build_operational_config(
    raw_rules: dict[str, Any] | None,
    *,
    fallback_timezone: str | None = None,
) -> dict[str, Any]:
    rules = raw_rules if isinstance(raw_rules, dict) else {}
    if isinstance(rules.get("operational"), dict):
        operational = rules["operational"]
        has_versioned_sections = "draft" in operational or "published" in operational
        direct_section = {
            key: value
            for key, value in operational.items()
            if key
            not in {"status", "version", "published_at", "draft", "published"}
        }
        normalized = {
            "status": _normalize_text(operational.get("status"), default="draft").lower(),
            "version": int(operational.get("version") or 1),
            "published_at": operational.get("published_at"),
            "draft": normalize_operational_section(
                operational.get("draft") if has_versioned_sections else direct_section,
                fallback_timezone=fallback_timezone,
            ),
            "published": normalize_operational_section(
                operational.get("published") if has_versioned_sections else direct_section,
                fallback_timezone=fallback_timezone,
            ),
        }
        if normalized["status"] not in ALLOWED_OPERATIONAL_STATUS:
            normalized["status"] = "draft"
        if not isinstance(normalized["published"], dict):
            normalized["published"] = deepcopy(normalized["draft"])
        return normalized

    legacy_section = {
        "security": {
            "mandatory_guardrails": dict(MANDATORY_GUARDRAILS),
            "custom_rules": _normalize_text(rules.get("guardrails")),
        },
        "schedule": _normalize_schedule(rules.get("schedule"), fallback_timezone=fallback_timezone),
        "autonomy": {
            "allow_critical_actions": _normalize_bool(rules.get("allow_critical_actions"), default=False),
            "critical_intents": _normalize_list(rules.get("critical_intents")) or list(DEFAULT_CRITICAL_INTENTS),
            "min_confidence": _normalize_float(rules.get("min_confidence"), default=DEFAULT_MIN_CONFIDENCE),
            "required_capture_fields": _normalize_list(rules.get("required_capture_fields")),
        },
        "escalation": _normalize_escalation(
            {
                "handoff_message": rules.get("handoff_rule"),
                "clarification_message": rules.get("clarification_message"),
                "low_confidence": True,
                "explicit_human_request": True,
            }
        ),
        "policies": {
            "shipping": _normalize_text(rules.get("shipping_policy")),
            "warranty": _normalize_text(rules.get("warranty_policy")),
            "returns": _normalize_text(rules.get("returns_policy")),
            "payments": _normalize_text(rules.get("payments_policy")),
        },
        "priorities": {
            "priority_categories": _normalize_list(rules.get("priority_categories")),
            "restricted_categories": _normalize_list(rules.get("restricted_categories")),
        },
        "test_mode": {
            "enabled": _normalize_bool(rules.get("test_mode"), default=False),
            "simulation_note": _normalize_text(rules.get("simulation_note")),
        },
    }
    has_legacy_content = any(_is_legacy_operational_rule(key) for key in rules)
    return {
        "status": "published" if has_legacy_content else "draft",
        "version": int(rules.get("operational_version") or 1),
        "published_at": rules.get("operational_published_at"),
        "draft": normalize_operational_section(legacy_section, fallback_timezone=fallback_timezone),
        "published": normalize_operational_section(legacy_section, fallback_timezone=fallback_timezone),
    }


def validate_operational_config(operational_config: dict[str, Any]) -> None:
    for label in ("draft", "published"):
        section = operational_config.get(label)
        if not isinstance(section, dict):
            continue
        security = section.get("security")
        if not isinstance(security, dict):
            continue
        guardrails = security.get("mandatory_guardrails")
        if not isinstance(guardrails, dict):
            continue
        disabled = [key for key, value in guardrails.items() if not value]
        if disabled:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "No puedes desactivar los guardrails obligatorios: "
                    + ", ".join(sorted(disabled))
                ),
            )


def publish_operational_config(
    operational_config: dict[str, Any],
) -> dict[str, Any]:
    validated = deepcopy(operational_config)
    validated["published"] = deepcopy(validated.get("draft") or {})
    validated["status"] = "published"
    validated["version"] = int(validated.get("version") or 1) + 1
    validated["published_at"] = datetime.utcnow().isoformat() + "Z"
    return validated


def get_effective_operational_section(operational_config: dict[str, Any]) -> dict[str, Any]:
    status = _normalize_text(operational_config.get("status"), default="draft").lower()
    if status == "published" and isinstance(operational_config.get("published"), dict):
        return operational_config["published"]
    if isinstance(operational_config.get("draft"), dict):
        return operational_config["draft"]
    if isinstance(operational_config.get("published"), dict):
        return operational_config["published"]
    return normalize_operational_section({}, fallback_timezone=None)


def _parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(hour=int(hour), minute=int(minute))


def _timezone_for_value(timezone_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name or "UTC")
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def evaluate_business_hours(
    operational_config: dict[str, Any],
    *,
    timezone_name: str | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    section = get_effective_operational_section(operational_config)
    schedule = section.get("schedule") if isinstance(section, dict) else {}
    if not isinstance(schedule, dict):
        schedule = {}
    tz_name = _normalize_text(schedule.get("timezone"), default=timezone_name or "UTC")
    tzinfo = _timezone_for_value(tz_name)
    current = now or datetime.now(tzinfo)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tzinfo)
    current = current.astimezone(tzinfo)
    is_weekend = current.weekday() >= 5
    window_key = "weekend" if is_weekend else "weekday"
    window = schedule.get(window_key)
    if not isinstance(window, dict):
        window = DEFAULT_WEEKEND_WINDOW if is_weekend else DEFAULT_WEEKDAY_WINDOW
    start = _parse_time(_normalize_clock(window.get("start"), default=window["start"]))
    end = _parse_time(_normalize_clock(window.get("end"), default=window["end"]))
    current_time = current.time()
    within_hours = start <= current_time <= end
    return {
        "timezone": tz_name,
        "day_type": "weekend" if is_weekend else "weekday",
        "within_hours": within_hours,
        "window": {"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M")},
        "outside_hours_behavior": _normalize_text(
            schedule.get("outside_hours_behavior"), default="handoff"
        ).lower()
        or "handoff",
        "outside_hours_message": _normalize_text(
            schedule.get("outside_hours_message"), default=DEFAULT_OUTSIDE_HOURS_MESSAGE
        ),
        "handoff_message": _normalize_text(
            schedule.get("handoff_message"), default=DEFAULT_HANDOFF_MESSAGE
        ),
        "current_iso": current.isoformat(),
    }


def summarize_operational_config(
    operational_config: dict[str, Any],
    *,
    timezone_name: str | None,
    now: datetime | None = None,
) -> str:
    active_section = get_effective_operational_section(operational_config)
    hours = evaluate_business_hours(
        operational_config,
        timezone_name=timezone_name,
        now=now,
    )
    security = active_section.get("security", {}) if isinstance(active_section, dict) else {}
    autonomy = active_section.get("autonomy", {}) if isinstance(active_section, dict) else {}
    escalation = active_section.get("escalation", {}) if isinstance(active_section, dict) else {}
    policies = active_section.get("policies", {}) if isinstance(active_section, dict) else {}
    priorities = active_section.get("priorities", {}) if isinstance(active_section, dict) else {}
    test_mode = active_section.get("test_mode", {}) if isinstance(active_section, dict) else {}
    lines = [
        "Configuracion operativa obligatoria:",
        f"- estado: {_normalize_text(operational_config.get('status'), default='draft')}",
        f"- version: {operational_config.get('version') or 1}",
        f"- timezone: {hours['timezone']}",
        f"- horario: {hours['day_type']} {hours['window']['start']}-{hours['window']['end']} | "
        f"fuera_de_horario={hours['outside_hours_behavior']}",
        f"- dentro_de_horario: {schedule_behavior_label(active_section)}",
        f"- guardrails: {', '.join([key for key, value in (security.get('mandatory_guardrails') or {}).items() if value]) or 'ninguno'}",
        f"- autonomia_confianza_minima: {autonomy.get('min_confidence', DEFAULT_MIN_CONFIDENCE)}",
        f"- autonomia_critica: {', '.join(_normalize_list(autonomy.get('critical_intents')))}",
        f"- handoff: {escalation.get('handoff_message') or DEFAULT_HANDOFF_MESSAGE}",
        f"- aclaracion: {escalation.get('clarification_message') or ''}",
        f"- politicas: envios={policies.get('shipping') or '-'} | garantia={policies.get('warranty') or '-'} | "
        f"cambios={policies.get('returns') or '-'} | pagos={policies.get('payments') or '-'}",
        f"- prioridades: altas={', '.join(_normalize_list(priorities.get('priority_categories'))) or 'ninguna'} | "
        f"restringidas={', '.join(_normalize_list(priorities.get('restricted_categories'))) or 'ninguna'}",
        f"- modo_prueba: {'activo' if _normalize_bool(test_mode.get('enabled'), default=False) else 'inactivo'}",
    ]
    return "\n".join(lines)


def schedule_behavior_label(active_section: dict[str, Any]) -> str:
    schedule = active_section.get("schedule") if isinstance(active_section, dict) else {}
    if not isinstance(schedule, dict):
        return "normal"
    return _normalize_text(schedule.get("inside_hours_behavior"), default="normal")


def simulation_summary(
    operational_config: dict[str, Any],
    *,
    timezone_name: str | None,
    message: str,
) -> dict[str, Any]:
    from app.ai.intent_classifier import classify_intent

    hours = evaluate_business_hours(
        operational_config,
        timezone_name=timezone_name,
        now=None,
    )
    active_section = get_effective_operational_section(operational_config)
    autonomy = active_section.get("autonomy", {}) if isinstance(active_section, dict) else {}
    escalation = active_section.get("escalation", {}) if isinstance(active_section, dict) else {}
    intent = classify_intent(message)
    confidence = intent.confidence
    critical_intents = set(_normalize_list(autonomy.get("critical_intents")) or DEFAULT_CRITICAL_INTENTS)
    min_confidence = _normalize_float(autonomy.get("min_confidence"), default=DEFAULT_MIN_CONFIDENCE)
    outside_hours_handoff = not hours["within_hours"] and hours["outside_hours_behavior"] == "handoff"
    low_confidence_critical = confidence < min_confidence and intent.intent in critical_intents
    explicit_escalation = intent.intent in {"request_human", "complaint"}
    requires_handoff = outside_hours_handoff or low_confidence_critical or explicit_escalation
    reason = ""
    if outside_hours_handoff:
        reason = "fuera de horario"
    elif low_confidence_critical:
        reason = "baja confianza"
    elif explicit_escalation:
        reason = "escalamiento explicito"
    return {
        "within_hours": hours["within_hours"],
        "day_type": hours["day_type"],
        "timezone": hours["timezone"],
        "status": _normalize_text(operational_config.get("status"), default="draft"),
        "intent": intent.intent,
        "confidence": confidence,
        "requires_handoff": requires_handoff,
        "reason": reason,
        "suggested_reply": (
            hours["outside_hours_message"]
            if not hours["within_hours"] and hours["outside_hours_behavior"] == "handoff"
            else escalation.get("clarification_message")
            or DEFAULT_OUTSIDE_HOURS_MESSAGE
        ),
        "min_confidence": min_confidence,
        "critical_intents": list(critical_intents),
    }
