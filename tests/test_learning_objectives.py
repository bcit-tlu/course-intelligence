"""Tests for wiring learning objectives into chunker/classifier LLM calls.

Covers: objectives injected as a separate user message when provided,
messages identical to the legacy two-message form when absent or blank
(backward compat), objectives read from AgentState by both nodes, and
whitespace-only objectives treated as absent.
"""

import json

from langchain_core.messages import AIMessage

from course_intelligence.engine.agents.chunker.semantic_chunker import (
    _chunk_text,
    create_semantic_chunker,
)
from course_intelligence.engine.agents.classifier.blooms_classifier import (
    _classify_batch,
    create_blooms_classifier,
)
from course_intelligence.engine.agents.utils.objectives import build_messages


OBJECTIVES = "Students should be able to analyze circuit diagrams."


class _CapturingLLM:
    """LLM stub that records every messages list it is invoked with."""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls: list[list[dict]] = []

    def invoke(self, messages):
        self.calls.append(messages)
        return AIMessage(content=self.response_text)


def _chunker_llm() -> _CapturingLLM:
    return _CapturingLLM(json.dumps([{"topic": "T", "content": "C"}]))


def _classifier_llm() -> _CapturingLLM:
    return _CapturingLLM(
        json.dumps([{"chunk_id": "id-0", "blooms_level": "Analyze", "rationale": "r"}])
    )


def _batch() -> list[dict]:
    return [{"chunk_id": "id-0", "topic": "Topic 0", "content": "Content 0"}]


# --- chunker ---------------------------------------------------------------

def test_chunker_injects_objectives_message():
    llm = _chunker_llm()
    result = _chunk_text(llm, "page text", OBJECTIVES)

    assert result is not None
    messages = llm.calls[0]
    assert [m["role"] for m in messages] == ["system", "user", "user"]
    assert messages[1]["content"] == f"Learning objectives for this course:\n{OBJECTIVES}"
    assert messages[2]["content"] == "page text"


def test_chunker_empty_objectives_keeps_legacy_messages():
    llm = _chunker_llm()
    _chunk_text(llm, "page text", "")

    messages = llm.calls[0]
    assert [m["role"] for m in messages] == ["system", "user"]
    assert messages[1]["content"] == "page text"


def test_chunker_whitespace_objectives_not_injected():
    llm = _chunker_llm()
    _chunk_text(llm, "page text", "   ")

    assert len(llm.calls[0]) == 2


def test_chunker_default_argument_backward_compat():
    """Old two-argument call sites still work and produce legacy messages."""
    llm = _chunker_llm()
    _chunk_text(llm, "page text")

    assert len(llm.calls[0]) == 2


def test_chunker_node_reads_objectives_from_state():
    llm = _chunker_llm()
    node = create_semantic_chunker(llm)

    node({"raw_text": "some text", "learning_objectives": OBJECTIVES})

    assert OBJECTIVES in llm.calls[0][1]["content"]


# --- classifier ------------------------------------------------------------

def test_classifier_injects_objectives_message():
    llm = _classifier_llm()
    _classify_batch(llm, _batch(), OBJECTIVES)

    messages = llm.calls[0]
    assert [m["role"] for m in messages] == ["system", "user", "user"]
    assert messages[1]["content"] == f"Learning objectives for this course:\n{OBJECTIVES}"
    assert json.loads(messages[2]["content"]) == _batch()


def test_classifier_empty_objectives_keeps_legacy_messages():
    llm = _classifier_llm()
    _classify_batch(llm, _batch(), "")

    messages = llm.calls[0]
    assert [m["role"] for m in messages] == ["system", "user"]
    assert json.loads(messages[1]["content"]) == _batch()


def test_classifier_node_reads_objectives_from_state():
    llm = _classifier_llm()
    node = create_blooms_classifier(llm)

    node({"knowledge_map": _batch(), "learning_objectives": OBJECTIVES})

    assert OBJECTIVES in llm.calls[0][1]["content"]


# --- shared helper ----------------------------------------------------------

def test_build_messages_none_objectives_matches_legacy_form():
    assert build_messages("sys", None, "content") == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "content"},
    ]
