"""Strict validation and ingestion for externally supplied provider evidence."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from provider_reliability import (
    ProviderState,
    attempted,
    configured,
    failed,
    skipped,
    succeeded,
    unavailable,
)
from provider_runtime import record


_ALLOWED_STATES = {state.value for state in ProviderState}


def _optional_string(value: Any, field: str, provider: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RuntimeError(f"Malformed provider evidence for {provider}: {field} must be a string or null.")
    return value


def _capabilities(value: Any, provider: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise RuntimeError(f"Malformed provider evidence for {provider}: capabilities must be a list of strings.")
    return list(value)


def ingest_provider_evidence(evidence_map: dict[str, Any]) -> None:
    """Validate and record externally supplied provider execution evidence.

    The accepted schema is intentionally strict so malformed external state
    cannot be coerced into a trustworthy runtime manifest.
    """
    if not isinstance(evidence_map, dict):
        raise RuntimeError("Malformed provider evidence: expected an object.")

    for provider, evidence in evidence_map.items():
        if not isinstance(provider, str) or not provider.strip():
            raise RuntimeError("Malformed provider evidence: provider name must be a non-empty string.")
        if not isinstance(evidence, dict):
            raise RuntimeError(f"Malformed provider evidence for {provider}: expected an object.")

        state = evidence.get("state")
        if not isinstance(state, str) or state not in _ALLOWED_STATES:
            raise RuntimeError(
                f"Malformed provider evidence for {provider}: state must be one of {sorted(_ALLOWED_STATES)}."
            )

        version = _optional_string(evidence.get("version"), "version", provider)
        reason = _optional_string(evidence.get("reason"), "reason", provider)
        capabilities = _capabilities(evidence.get("capabilities"), provider)
        artifact_value = evidence.get("artifact")
        if artifact_value is not None and not isinstance(artifact_value, str):
            raise RuntimeError(f"Malformed provider evidence for {provider}: artifact must be a string or null.")

        configured_value = evidence.get("configured")
        attempted_value = evidence.get("attempted")
        for field, value in (("configured", configured_value), ("attempted", attempted_value)):
            if value is not None and type(value) is not bool:
                raise RuntimeError(f"Malformed provider evidence for {provider}: {field} must be a boolean when supplied.")

        if state == ProviderState.SUCCEEDED.value:
            if artifact_value is None or not artifact_value.strip():
                raise RuntimeError(f"Malformed provider evidence for {provider}: succeeded state requires an artifact path.")
            if configured_value is not None and configured_value is not True:
                raise RuntimeError(f"Malformed provider evidence for {provider}: succeeded state requires configured=true.")
            if attempted_value is not None and attempted_value is not True:
                raise RuntimeError(f"Malformed provider evidence for {provider}: succeeded state requires attempted=true.")
            execution = succeeded(provider, reason or "Provider execution succeeded.", version=version, capabilities=capabilities)
            valid = record(execution)
            if artifact_value:
                artifact = Path(artifact_value)
                if not artifact.is_file() or artifact.stat().st_size < 1:
                    raise RuntimeError(f"Malformed provider evidence for {provider}: succeeded artifact is missing or empty.")
            continue

        if artifact_value is not None:
            raise RuntimeError(f"Malformed provider evidence for {provider}: artifact is only valid for succeeded state.")

        if state == ProviderState.FAILED.value:
            if configured_value is not None and configured_value is not True:
                raise RuntimeError(f"Malformed provider evidence for {provider}: failed state requires configured=true.")
            if attempted_value is not None and attempted_value is not True:
                raise RuntimeError(f"Malformed provider evidence for {provider}: failed state requires attempted=true.")
            record(failed(provider, reason or "Provider execution failed.", version=version, capabilities=capabilities))
        elif state == ProviderState.ATTEMPTED.value:
            if configured_value is not None and configured_value is not True:
                raise RuntimeError(f"Malformed provider evidence for {provider}: attempted state requires configured=true.")
            if attempted_value is not None and attempted_value is not True:
                raise RuntimeError(f"Malformed provider evidence for {provider}: attempted state requires attempted=true.")
            record(attempted(provider, reason or "Provider execution started.", version=version, capabilities=capabilities))
        elif state == ProviderState.CONFIGURED.value:
            if configured_value is not None and configured_value is not True:
                raise RuntimeError(f"Malformed provider evidence for {provider}: configured state requires configured=true.")
            if attempted_value is True:
                raise RuntimeError(f"Malformed provider evidence for {provider}: configured state cannot set attempted=true.")
            record(configured(provider, reason or "Provider is configured and ready.", version=version, capabilities=capabilities))
        elif state == ProviderState.UNAVAILABLE.value:
            if configured_value is True:
                raise RuntimeError(f"Malformed provider evidence for {provider}: unavailable state cannot set configured=true.")
            if attempted_value is True:
                raise RuntimeError(f"Malformed provider evidence for {provider}: unavailable state cannot set attempted=true.")
            record(unavailable(provider, reason or "Provider is unavailable.", version=version))
        elif state == ProviderState.SKIPPED.value:
            if attempted_value is True:
                raise RuntimeError(f"Malformed provider evidence for {provider}: skipped state cannot set attempted=true.")
            record(skipped(provider, reason or "Provider execution skipped.", version=version))
