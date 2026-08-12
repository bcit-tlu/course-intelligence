"""Unit tests for the Bloom's classifier node — matching, batching,
and failure tolerance."""

import json

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from course_intelligence.engine.agents.classifier.blooms_classifier import (
    UNCLASSIFIED,
    create_blooms_classifier,
)


def _chunks(n: int) -> list[dict]:
    return [
        {"chunk_id": f"id-{i}", "topic": f"Topic {i}", "content": f"Content {i}"}
        for i in range(n)
    ]


def test_matches_by_chunk_id():
    """Levels are applied to the right chunks via chunk_id, regardless of order."""
    response = json.dumps([
        {"chunk_id": "id-1", "blooms_level": "Create", "rationale": "r1"},
        {"chunk_id": "id-0", "blooms_level": "Remember", "rationale": "r0"},
    ])
    node = create_blooms_classifier(FakeListChatModel(responses=[response]))

    state = {"knowledge_map": _chunks(2)}
    result = node(state)

    km = result["knowledge_map"]
    assert km[0]["blooms_level"] == "Remember"
    assert km[1]["blooms_level"] == "Create"


def test_positional_fallback_when_ids_missing():
    """If the LLM omits chunk_ids but counts match, match by position."""
    response = json.dumps([
        {"blooms_level": "Understand", "rationale": "r0"},
        {"blooms_level": "Apply", "rationale": "r1"},
    ])
    node = create_blooms_classifier(FakeListChatModel(responses=[response]))

    result = node({"knowledge_map": _chunks(2)})

    km = result["knowledge_map"]
    assert km[0]["blooms_level"] == "Understand"
    assert km[1]["blooms_level"] == "Apply"


def test_invalid_json_leaves_chunks_unclassified():
    """A malformed LLM response must not raise — chunks get 'unclassified'."""
    node = create_blooms_classifier(FakeListChatModel(responses=["not json at all"]))

    result = node({"knowledge_map": _chunks(3)})

    for chunk in result["knowledge_map"]:
        assert chunk["blooms_level"] == UNCLASSIFIED


def test_invalid_level_is_unclassified():
    """An unknown level string is normalized to 'unclassified'."""
    response = json.dumps([
        {"chunk_id": "id-0", "blooms_level": "Memorize", "rationale": "bad level"},
    ])
    node = create_blooms_classifier(FakeListChatModel(responses=[response]))

    result = node({"knowledge_map": _chunks(1)})

    assert result["knowledge_map"][0]["blooms_level"] == UNCLASSIFIED


def test_level_normalization_case_insensitive():
    """Levels are normalized to canonical capitalization."""
    response = json.dumps([
        {"chunk_id": "id-0", "blooms_level": "ANALYZE", "rationale": "r"},
    ])
    node = create_blooms_classifier(FakeListChatModel(responses=[response]))

    result = node({"knowledge_map": _chunks(1)})

    assert result["knowledge_map"][0]["blooms_level"] == "Analyze"


def test_batching_multiple_calls():
    """More than BATCH_SIZE chunks are classified across multiple calls."""
    # 12 chunks → 2 batches (10 + 2). Provide per-batch responses.
    batch1 = json.dumps([
        {"chunk_id": f"id-{i}", "blooms_level": "Remember", "rationale": "r"}
        for i in range(10)
    ])
    batch2 = json.dumps([
        {"chunk_id": f"id-{i}", "blooms_level": "Evaluate", "rationale": "r"}
        for i in range(10, 12)
    ])
    node = create_blooms_classifier(FakeListChatModel(responses=[batch1, batch2]))

    result = node({"knowledge_map": _chunks(12)})

    km = result["knowledge_map"]
    assert all(c["blooms_level"] == "Remember" for c in km[:10])
    assert all(c["blooms_level"] == "Evaluate" for c in km[10:])


def test_empty_knowledge_map_is_noop():
    node = create_blooms_classifier(FakeListChatModel(responses=["[]"]))
    assert node({"knowledge_map": []}) == {}
