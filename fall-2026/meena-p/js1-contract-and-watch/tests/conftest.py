import pytest

from agent import claude_judge


@pytest.fixture(autouse=True)
def _isolate_calls_log(tmp_path, monkeypatch):
    """No test may append to the real evidence/claude_calls.jsonl."""
    monkeypatch.setattr(claude_judge, "CALLS_LOG", tmp_path / "claude_calls.jsonl")
