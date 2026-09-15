"""Deterministic validation for provider execution audit data."""
from __future__ import annotations

from typing import Any

TERMINAL_STATES = {"unavailable", "succeeded", "failed", "skipped"}


def validate_provider_audit(snapshot: dict[str, dict[str, Any]]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for name, item in snapshot.items():
        state = item.get("state")
        applied = bool(item.get("applied", False))
        if state not in TERMINAL_STATES | {"configured", "attempted"}:
            errors.append(f"{name}:invalid_state:{state}")
        if applied and state != "succeeded":
            errors.append(f"{name}:applied_requires_succeeded")
        if state in {"failed", "skipped", "unavailable"} and not str(item.get("reason") or "").strip():
            errors.append(f"{name}:terminal_non_success_requires_reason")
    return not errors, errors


def provider_audit_qc(snapshot: dict[str, dict[str, Any]]) -> dict[str, Any]:
    valid, errors = validate_provider_audit(snapshot)
    return {"valid": valid, "errors": errors, "providers": snapshot}
