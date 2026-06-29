from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import quote
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_secret
from app.integrations.models import CompanyIntegration

SUPPORTED_CALENDAR_PROVIDERS = {"google_calendar", "microsoft_calendar"}
CALENDAR_PROVIDER_ALIASES = {"outlook_calendar": "microsoft_calendar"}
DEFAULT_CALENDAR_PROVIDER = "google_calendar"
CALENDAR_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "google_calendar": {
        "api_base_url": "https://www.googleapis.com/calendar/v3",
        "create_event_path": "calendars/{calendar_id}/events",
        "update_event_path": "calendars/{calendar_id}/events/{event_id}",
        "response_event_id_path": "id",
    },
    "microsoft_calendar": {
        "api_base_url": "https://graph.microsoft.com/v1.0",
        "create_event_path": "me/calendars/{calendar_id}/events",
        "update_event_path": "me/events/{event_id}",
        "response_event_id_path": "id",
    },
}


@dataclass(frozen=True)
class CalendarSyncResult:
    external_event_id: str
    raw: dict[str, Any]


class CalendarAdapter(Protocol):
    provider: str

    def validate_integration(
        self,
        *,
        config: dict[str, Any],
        credentials_raw: str | None,
        integration_status: str,
    ) -> None: ...

    def sync_appointment(
        self,
        *,
        company_id: UUID,
        appointment_id: UUID,
        scheduled_at: datetime,
        duration_minutes: int,
        notes: str | None,
        external_event_id: str | None,
        config: dict[str, Any],
        credentials_raw: str | None,
    ) -> CalendarSyncResult: ...


def normalize_calendar_provider(provider: str | None) -> str:
    normalized = str(provider or DEFAULT_CALENDAR_PROVIDER).strip().lower() or DEFAULT_CALENDAR_PROVIDER
    return CALENDAR_PROVIDER_ALIASES.get(normalized, normalized)


def _provider_defaults(provider: str) -> dict[str, str]:
    normalized = normalize_calendar_provider(provider)
    return dict(CALENDAR_PROVIDER_DEFAULTS.get(normalized, {}))


def normalize_calendar_config(config: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    next_config = dict(config)
    if "provider" in next_config and next_config.get("provider") is not None:
        provider = normalize_calendar_provider(next_config.get("provider"))
        next_config["provider"] = provider
        for key, value in _provider_defaults(provider).items():
            next_config.setdefault(key, value)
    return next_config


def calendar_credentials_raw(integration: CompanyIntegration | None) -> str | None:
    if integration is None or not integration.credentials_encrypted:
        return None
    try:
        return decrypt_secret(integration.credentials_encrypted)
    except Exception:
        return None


def _normalize_status(status_value: str | None) -> str:
    return str(status_value or "").strip().lower() or "active"


def _require_calendar_config_value(config: dict[str, Any], key: str) -> str:
    value = str(config.get(key) or "").strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Calendar {key.replace('_', ' ')} is required to activate this calendar integration",
        )
    return value


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _build_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _format_path(path: str, *, calendar_id: str, event_id: str | None = None) -> str:
    safe_event_id = quote(event_id or "", safe="") if event_id is not None else ""
    safe_calendar_id = quote(calendar_id, safe="")
    return path.format(calendar_id=safe_calendar_id, event_id=safe_event_id)


def _parse_credentials_headers(credentials_raw: str | None) -> dict[str, str]:
    raw = str(credentials_raw or "").strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Calendar credentials are required to sync this appointment",
        )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"Authorization": f"Bearer {raw}"}
    if not isinstance(parsed, dict):
        return {"Authorization": f"Bearer {raw}"}

    headers: dict[str, str] = {}
    extra_headers = parsed.get("headers")
    if isinstance(extra_headers, dict):
        headers.update(
            {
                str(key): str(value)
                for key, value in extra_headers.items()
                if value is not None and str(value).strip()
            }
        )

    access_token = str(parsed.get("access_token") or parsed.get("token") or "").strip()
    api_key = str(parsed.get("api_key") or "").strip()
    if access_token:
        headers.setdefault("Authorization", f"Bearer {access_token}")
    elif api_key:
        headers.setdefault("X-API-Key", api_key)

    if not headers:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Calendar credentials must include an access token, api_key or headers",
        )
    return headers


def _extract_response_event_id(response: httpx.Response, config: dict[str, Any]) -> str:
    response_json: Any
    try:
        response_json = response.json()
    except Exception:
        response_json = None

    path = str(config.get("response_event_id_path") or "id").strip()
    candidates: list[str] = []
    if isinstance(response_json, dict):
        if path:
            value: Any = response_json
            for segment in path.split("."):
                if not isinstance(value, dict):
                    value = None
                    break
                value = value.get(segment)
            if value not in {None, ""}:
                candidates.append(str(value))
        for fallback_key in ("external_event_id", "event_id", "id"):
            value = response_json.get(fallback_key)
            if value not in {None, ""}:
                candidates.append(str(value))

    location = response.headers.get("Location")
    if location:
        candidates.append(location.rstrip("/").rsplit("/", 1)[-1])

    for candidate in candidates:
        if candidate:
            return candidate

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Calendar API did not return an event identifier",
    )


class HttpCalendarAdapter:
    def __init__(self, provider: str) -> None:
        self.provider = normalize_calendar_provider(provider)

    def validate_integration(
        self,
        *,
        config: dict[str, Any],
        credentials_raw: str | None,
        integration_status: str,
    ) -> None:
        if _normalize_status(integration_status) != "active":
            return
        provider = _require_calendar_config_value(config, "provider")
        provider = normalize_calendar_provider(provider)
        if provider not in SUPPORTED_CALENDAR_PROVIDERS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Calendar provider must be Google Calendar or Microsoft Calendar",
            )
        _require_calendar_config_value(config, "calendar_id")
        _require_calendar_config_value(config, "timezone")
        _require_calendar_config_value(config, "api_base_url")
        _require_calendar_config_value(config, "create_event_path")
        _require_calendar_config_value(config, "update_event_path")
        _parse_credentials_headers(credentials_raw)

    def sync_appointment(
        self,
        *,
        company_id: UUID,
        appointment_id: UUID,
        scheduled_at: datetime,
        duration_minutes: int,
        notes: str | None,
        external_event_id: str | None,
        config: dict[str, Any],
        credentials_raw: str | None,
    ) -> CalendarSyncResult:
        provider = normalize_calendar_provider(_require_calendar_config_value(config, "provider") or self.provider)
        if provider not in SUPPORTED_CALENDAR_PROVIDERS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Calendar provider must be Google Calendar or Microsoft Calendar",
            )
        headers = _parse_credentials_headers(credentials_raw)
        calendar_id = _require_calendar_config_value(config, "calendar_id")
        timezone = _require_calendar_config_value(config, "timezone")
        api_base_url = _require_calendar_config_value(config, "api_base_url")
        create_event_path = _require_calendar_config_value(config, "create_event_path")
        update_event_path = _require_calendar_config_value(config, "update_event_path")
        request_payload = {
            "provider": provider,
            "company_id": str(company_id),
            "appointment_id": str(appointment_id),
            "calendar_id": calendar_id,
            "timezone": timezone,
            "scheduled_at": _normalize_datetime(scheduled_at).isoformat(),
            "duration_minutes": duration_minutes,
            "notes": notes,
        }
        method = "PATCH" if external_event_id else "POST"
        path = update_event_path if external_event_id else create_event_path
        formatted_path = _format_path(
            path,
            calendar_id=calendar_id,
            event_id=external_event_id,
        )
        url = _build_url(api_base_url, formatted_path)

        with httpx.Client(timeout=10) as client:
            response = client.request(method, url, json=request_payload, headers=headers)
            response.raise_for_status()

        next_external_event_id = external_event_id or _extract_response_event_id(response, config)
        return CalendarSyncResult(
            external_event_id=next_external_event_id,
            raw={
                "provider": provider,
                "company_id": str(company_id),
                "appointment_id": str(appointment_id),
                "calendar_id": calendar_id,
                "timezone": timezone,
                "scheduled_at": request_payload["scheduled_at"],
                "duration_minutes": duration_minutes,
                "notes": notes,
                "external_event_id": next_external_event_id,
                "request": {
                    "method": method,
                    "url": url,
                    "payload": request_payload,
                },
            },
        )


def get_calendar_adapter(provider: str | None) -> CalendarAdapter:
    return HttpCalendarAdapter(normalize_calendar_provider(provider))


def validate_calendar_integration_config(
    *,
    config: dict[str, Any],
    credentials_raw: str | None,
    integration_status: str,
) -> None:
    get_calendar_adapter(config.get("provider")).validate_integration(
        config=normalize_calendar_config(config),
        credentials_raw=credentials_raw,
        integration_status=integration_status,
    )


def sync_appointment_with_calendar(
    db: Session,
    *,
    company_id: UUID,
    appointment,
) -> CalendarSyncResult | None:
    integration = db.scalar(
        select(CompanyIntegration)
        .where(
            CompanyIntegration.company_id == company_id,
            CompanyIntegration.type == "calendar",
            CompanyIntegration.status == "active",
        )
        .order_by(CompanyIntegration.updated_at.desc())
    )
    if integration is None:
        return None

    config = normalize_calendar_config(integration.config)
    credentials_raw = calendar_credentials_raw(integration)
    adapter = get_calendar_adapter(config.get("provider"))
    adapter.validate_integration(
        config=config,
        credentials_raw=credentials_raw,
        integration_status=integration.status,
    )
    return adapter.sync_appointment(
        company_id=company_id,
        appointment_id=appointment.id,
        scheduled_at=appointment.scheduled_at,
        duration_minutes=appointment.duration_minutes,
        notes=appointment.notes,
        external_event_id=appointment.external_calendar_event_id,
        config=config,
        credentials_raw=credentials_raw,
    )
