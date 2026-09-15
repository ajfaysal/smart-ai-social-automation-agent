import threading

import provider_runtime
from provider_reliability import ProviderExecution, ProviderState


def test_runtime_registry_supports_explicit_request_scope_reset():
    provider_runtime.reset_provider_executions()
    provider_runtime.record(ProviderExecution("demucs", ProviderState.SUCCEEDED, True, "artifact_valid"))
    assert provider_runtime.snapshot()["demucs"]["applied"] is True
    provider_runtime.reset_provider_executions()
    assert provider_runtime.snapshot() == {}
