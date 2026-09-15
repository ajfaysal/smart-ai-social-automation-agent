"""Auditable execution-state helpers for optional production providers.

The pipeline must never infer success from configuration alone. A provider
moves through explicit states and failures are represented as data so the
final manifest/QC layer can report what actually happened.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class ProviderState(str, Enum):
    UNAVAILABLE = "unavailable"
    CONFIGURED = "configured"
    ATTEMPTED = "attempted"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProviderExecution:
    provider: str
    state: ProviderState
    applied: bool = False
    reason: str = ""
    version: str | None = None
    capabilities: list[str] | None = None

    def __post_init__(self) -> None:
        if self.capabilities is None:
            self.capabilities = []
        if self.state is not ProviderState.SUCCEEDED and self.applied:
            raise ValueError("Only a succeeded provider execution may be applied.")

    def to_manifest(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


def unavailable(provider: str, reason: str, *, version: str | None = None) -> ProviderExecution:
    return ProviderExecution(provider, ProviderState.UNAVAILABLE, False, reason, version)


def configured(provider: str, reason: str = "Provider is configured and ready.", *, version: str | None = None, capabilities: list[str] | None = None) -> ProviderExecution:
    return ProviderExecution(provider, ProviderState.CONFIGURED, False, reason, version, capabilities)


def attempted(provider: str, reason: str = "Provider execution started.", *, version: str | None = None, capabilities: list[str] | None = None) -> ProviderExecution:
    return ProviderExecution(provider, ProviderState.ATTEMPTED, False, reason, version, capabilities)


def succeeded(provider: str, reason: str = "Provider execution succeeded.", *, version: str | None = None, capabilities: list[str] | None = None) -> ProviderExecution:
    return ProviderExecution(provider, ProviderState.SUCCEEDED, True, reason, version, capabilities)


def failed(provider: str, reason: str, *, version: str | None = None, capabilities: list[str] | None = None) -> ProviderExecution:
    return ProviderExecution(provider, ProviderState.FAILED, False, reason, version, capabilities)


def skipped(provider: str, reason: str, *, version: str | None = None) -> ProviderExecution:
    return ProviderExecution(provider, ProviderState.SKIPPED, False, reason, version)
