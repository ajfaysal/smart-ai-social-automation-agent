from pathlib import Path


RUNNER = Path(__file__).resolve().parents[1] / "real_provider_runner.py"


def test_real_provider_runner_keeps_stdout_machine_readable():
    source = RUNNER.read_text(encoding="utf-8")
    assert "contextlib.redirect_stdout(io.StringIO())" in source
    assert 'print(json.dumps(result, ensure_ascii=False, indent=2))' in source


def test_real_provider_runner_validates_audit_before_json_output():
    source = RUNNER.read_text(encoding="utf-8")
    assert "validate_provider_snapshot(result[\"provider_execution\"])" in source
    assert source.index("validate_provider_snapshot(result[") < source.index("print(json.dumps(result")
