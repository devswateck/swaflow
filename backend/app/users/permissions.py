from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from fastapi import HTTPException, status

MODULE_PERMISSION_KEYS: tuple[str, ...] = (
    "dashboard",
    "inbox",
    "products",
    "inventory",
    "orders",
    "appointments",
    "whatsapp",
    "ai",
    "funnels",
    "integrations",
    "settings",
)

DEFAULT_SAFE_MODULES = {
    "dashboard",
    "inbox",
    "products",
    "inventory",
    "orders",
    "appointments",
}

PRIVILEGED_ROLES = {"owner", "admin", "superadmin"}


def default_module_permissions(*, role: str) -> dict[str, bool]:
    if role in PRIVILEGED_ROLES:
        return {module: True for module in MODULE_PERMISSION_KEYS}
    return {module: module in DEFAULT_SAFE_MODULES for module in MODULE_PERMISSION_KEYS}


def normalize_module_permissions(
    module_permissions: Mapping[str, object] | None,
    *,
    role: str,
) -> dict[str, bool]:
    permissions = default_module_permissions(role=role)
    if module_permissions is None:
        return permissions
    if not isinstance(module_permissions, Mapping):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid module permissions",
        )
    for module, value in module_permissions.items():
        if module not in MODULE_PERMISSION_KEYS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown module permission: {module}",
            )
        permissions[module] = bool(value)
    return permissions


def effective_module_permissions(user) -> dict[str, bool]:
    raw_permissions = getattr(user, "module_permissions", None)
    return normalize_module_permissions(raw_permissions, role=user.role)


def can_access_module(user, module: str) -> bool:
    if module not in MODULE_PERMISSION_KEYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown module permission: {module}",
        )
    if user.role in PRIVILEGED_ROLES:
        return True
    return effective_module_permissions(user).get(module, False)


def ensure_module_access(user, module: str) -> None:
    if not can_access_module(user, module):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient module permissions",
        )


def user_accessible_modules(user) -> list[str]:
    return [module for module, allowed in effective_module_permissions(user).items() if allowed]


def user_company_scope(user) -> UUID:
    return user.company_id
