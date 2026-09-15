"""Auditable execution-state helpers for optional production providers."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import Enum

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
    def __post_init__(self):
        if self.capabilities is None: self.capabilities = []
        if self.state is not ProviderState.SUCCEEDED and self.applied:
            raise ValueError("Only a succeeded provider execution may be applied.")
    def to_manifest(self):
        data = asdict(self); data["state"] = self.state.value; return data

def unavailable(provider, reason, *, version=None): return ProviderExecution(provider, ProviderState.UNAVAILABLE, False, reason, version)
def configured(provider, reason="Provider is configured and ready.", *, version=None, capabilities=None): return ProviderExecution(provider, ProviderState.CONFIGURED, False, reason, version, capabilities)
def attempted(provider, reason="Provider execution started.", *, version=None, capabilities=None): return ProviderExecution(provider, ProviderState.ATTEMPTED, False, reason, version, capabilities)
def succeeded(provider, reason="Provider execution succeeded.", *, version=None, capabilities=None): return ProviderExecution(provider, ProviderState.SUCCEEDED, True, reason, version, capabilities)
def failed(provider, reason, *, version=None, capabilities=None): return ProviderExecution(provider, ProviderState.FAILED, False, reason, version, capabilities)
def skipped(provider, reason, *, version=None): return ProviderExecution(provider, ProviderState.SKIPPED, False, reason, version)
