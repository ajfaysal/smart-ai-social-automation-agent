"""Request-scoped runtime registry for auditable provider execution."""
from __future__ import annotations

import contextvars
import json
from pathlib import Path
from typing import Any

from provider_reliability import ProviderExecution, ProviderState

_EXECUTIONS: contextvars.ContextVar[dict[str, ProviderExecution] | None] = contextvars.ContextVar(
    "provider_executions", default=None
)


def _registry() -> dict[str, ProviderExecution]:
    registry = _EXECUTIONS.get()
    if registry is None:
        registry = {}
        _EXECUTIONS.set(registry)
    return registry


def reset_provider_executions() -> None:
    _EXECUTIONS.set({})


def record(execution: ProviderExecution) -> ProviderExecution:
    _registry()[execution.provider] = execution
    return execution


def snapshot() -> dict[str, dict[str, Any]]:
    return {name: execution.to_manifest() for name, execution in _registry().items()}


def validate_provider_snapshot(data: dict[str, dict[str, Any]]) -> tuple[bool, str]:
    for provider, execution in data.items():
        if not isinstance(execution, dict):
            return False, f"invalid_execution:{provider}"
        state = execution.get("state")
        applied = execution.get("applied")
        reason = execution.get("reason")
        if not provider or state not in {s.value for s in ProviderState}:
            return False, f"invalid_state:{provider}"
        if not isinstance(applied, bool):
            return False, f"invalid_applied:{provider}"
        if applied and state != ProviderState.SUCCEEDED.value:
            return False, f"applied_without_success:{provider}"
        if state in {ProviderState.UNAVAILABLE.value, ProviderState.CONFIGURED.value,
                     ProviderState.ATTEMPTED.value, ProviderState.FAILED.value,
                     ProviderState.SKIPPED.value} and not isinstance(reason, str):
            return False, f"missing_reason:{provider}"
    return True, "provider_audit_valid"


def validate_artifact(path: Path, *, min_bytes: int = 1, suffix: str | None = None) -> tuple[bool, str]:
    if not path.exists():
        return False, f"artifact_missing:{path}"
    if not path.is_file():
        return False, f"artifact_not_file:{path}"
    size = path.stat().st_size
    if size < min_bytes:
        return False, f"artifact_too_small:{size}<{min_bytes}"
    if suffix and path.suffix.lower() != suffix.lower():
        return False, f"artifact_suffix_mismatch:{path.suffix}"
    return True, "artifact_valid"


def finalize(provider: str, *, configured: bool, attempted: bool,
             artifact: Path | None = None, min_bytes: int = 1,
             suffix: str | None = None, reason: str | None = None,
             version: str | None = None, capabilities: list[str] | None = None) -> ProviderExecution:
    capabilities = capabilities or []
    if not configured:
        return record(ProviderExecution(provider, ProviderState.UNAVAILABLE, False,
                                        reason or "provider_not_configured", version, capabilities))
    if not attempted:
        return record(ProviderExecution(provider, ProviderState.CONFIGURED, False,
                                        reason or "provider_not_attempted", version, capabilities))
    if reason:
        return record(ProviderExecution(provider, ProviderState.FAILED, False, reason, version, capabilities))
    if artifact is None:
        return record(ProviderExecution(provider, ProviderState.FAILED, False,
                                        "artifact_expectation_missing", version, capabilities))
    valid, validation_reason = validate_artifact(artifact, min_bytes=min_bytes, suffix=suffix)
    state = ProviderState.SUCCEEDED if valid else ProviderState.FAILED
    return record(ProviderExecution(provider, state, valid, validation_reason, version, capabilities))


def skip_provider(provider: str, reason: str, *, version: str | None = None,
                  capabilities: list[str] | None = None) -> ProviderExecution:
    return record(ProviderExecution(provider, ProviderState.SKIPPED, False,
                                    reason, version, capabilities or []))


def write_snapshot(path: Path) -> None:
    data = snapshot()
    valid, reason = validate_provider_snapshot(data)
    if not valid:
        raise ValueError(reason)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
