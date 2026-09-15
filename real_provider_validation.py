"""Helpers for opt-in real provider execution validation.

This module deliberately validates outputs rather than claiming success from
configuration alone. It is safe to use in credential-free CI.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from provider_reliability import ProviderExecution, ProviderState


@dataclass(frozen=True)
class ArtifactExpectation:
    provider: str
    path: str
    min_bytes: int = 1
    required_suffix: str | None = None


def validate_artifact(expectation: ArtifactExpectation) -> tuple[bool, str]:
    path = Path(expectation.path)
    if not path.exists():
        return False, f"artifact_missing:{path}"
    if not path.is_file():
        return False, f"artifact_not_file:{path}"
    size = path.stat().st_size
    if size < expectation.min_bytes:
        return False, f"artifact_too_small:{size}<{expectation.min_bytes}"
    if expectation.required_suffix and path.suffix.lower() != expectation.required_suffix.lower():
        return False, f"artifact_suffix_mismatch:{path.suffix}"
    return True, "artifact_valid"


def finalize_execution(
    provider: str,
    *,
    configured: bool,
    attempted: bool,
    expectation: ArtifactExpectation | None = None,
    version: str | None = None,
    capabilities: Mapping[str, str] | None = None,
    failure_reason: str | None = None,
) -> ProviderExecution:
    """Return an auditable execution result with fail-closed success semantics."""
    if not configured:
        return ProviderExecution(provider, ProviderState.UNAVAILABLE, False, "provider_not_configured", version, capabilities or {})
    if not attempted:
        return ProviderExecution(provider, ProviderState.CONFIGURED, False, "provider_not_attempted", version, capabilities or {})
    if failure_reason:
        return ProviderExecution(provider, ProviderState.FAILED, False, failure_reason, version, capabilities or {})
    if expectation is None:
        return ProviderExecution(provider, ProviderState.FAILED, False, "artifact_expectation_missing", version, capabilities or {})
    valid, reason = validate_artifact(expectation)
    if not valid:
        return ProviderExecution(provider, ProviderState.FAILED, False, reason, version, capabilities or {})
    return ProviderExecution(provider, ProviderState.SUCCEEDED, True, reason, version, capabilities or {})
