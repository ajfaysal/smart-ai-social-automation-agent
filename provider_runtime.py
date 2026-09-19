"""Runtime registry for auditable optional provider execution.

The registry is process-local but request-scoped via ContextVar so concurrent
dubbing jobs cannot mix provider execution records. Providers register only
after an explicit execution attempt; success is accepted only when the
expected artifact validator passes. It is safe in credential-free CI.
"""
from __future__ import annotations

import json
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from provider_reliability import ProviderExecution, ProviderState


_EXECUTIONS: ContextVar[dict[str, ProviderExecution]] = ContextVar(
    "provider_executions",
    default={},
)


def reset_provider_executions() -> None:
    """Start a fresh provider audit scope for the current execution context."""
    _EXECUTIONS.set({})


def record(execution: ProviderExecution) -> ProviderExecution:
    executions = dict(_EXECUTIONS.get())
    executions[execution.provider] = execution
    _EXECUTIONS.set(executions)
    return execution


def snapshot() -> dict[str, dict[str, Any]]:
    return {
        name: execution.to_manifest()
        for name, execution in _EXECUTIONS.get().items()
    }


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


def write_snapshot(path: Path) -> None:
    path.write_text(json.dumps(snapshot(), ensure_ascii=False, indent=2), encoding="utf-8")
