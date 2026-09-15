from pathlib import Path
from provider_runtime import finalize
from provider_reliability import ProviderState

def test_artifact_too_small_fails(tmp_path: Path):
    p=tmp_path/'x.wav'; p.write_bytes(b'x')
    r=finalize('demucs',configured=True,attempted=True,artifact=p,min_bytes=10,suffix='.wav')
    assert r.state is ProviderState.FAILED
    assert not r.applied
