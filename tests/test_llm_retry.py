"""Tests for the LLM retry wrapper and chunker error handling."""

import json

import pytest

from course_intelligence.engine.agents.utils.llm_retry import invoke_with_retry


class _FlakyLLM:
    """Fake LLM that raises N times then returns a fixed response."""

    def __init__(self, fail_times: int, response: str = "[]"):
        self._fail_times = fail_times
        self._calls = 0
        self._response = response

    def invoke(self, messages):
        self._calls += 1
        if self._calls <= self._fail_times:
            raise RuntimeError("simulated peg-gemma4 parse error")
        return type("Resp", (), {"content": self._response})()


class _AlwaysFailingLLM:
    """Fake LLM that always raises."""

    def invoke(self, messages):
        raise RuntimeError("permanent failure")


def test_retry_succeeds_after_transient_failure():
    """invoke_with_retry returns a result when the LLM succeeds on retry."""
    llm = _FlakyLLM(fail_times=2, response='[{"topic": "t", "content": "c"}]')
    result = invoke_with_retry(llm, [], max_retries=3)
    assert result.content == '[{"topic": "t", "content": "c"}]'
    assert llm._calls == 3


def test_retry_exhausted_raises():
    """invoke_with_retry raises the last exception when all retries fail."""
    llm = _AlwaysFailingLLM()
    with pytest.raises(RuntimeError, match="permanent failure"):
        invoke_with_retry(llm, [], max_retries=2)


def test_retry_succeeds_first_try(monkeypatch):
    """No retries needed when the LLM succeeds immediately."""
    monkeypatch.setattr("time.sleep", lambda s: None)  # avoid real sleeping
    llm = _FlakyLLM(fail_times=0, response="ok")
    result = invoke_with_retry(llm, [], max_retries=3)
    assert result.content == "ok"
    assert llm._calls == 1


def test_chunker_handles_llm_failure_gracefully():
    """Semantic chunker returns None (not an exception) when LLM fails persistently."""
    from course_intelligence.engine.agents.chunker.semantic_chunker import _chunk_text

    llm = _AlwaysFailingLLM()
    result = _chunk_text(llm, "some text")
    assert result is None


def test_chunker_retries_then_succeeds(monkeypatch):
    """Semantic chunker retries and succeeds when the LLM is transiently flaky."""
    monkeypatch.setattr("time.sleep", lambda s: None)
    from course_intelligence.engine.agents.chunker.semantic_chunker import _chunk_text

    response = json.dumps([{"topic": "Test", "content": "Test content"}])
    llm = _FlakyLLM(fail_times=1, response=response)
    result = _chunk_text(llm, "some text")
    assert result is not None
    assert len(result) == 1
    assert result[0]["topic"] == "Test"
