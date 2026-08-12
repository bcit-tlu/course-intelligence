"""Test the ingestion pipeline using the mock LLM — no tokens spent."""

import os
import tempfile

from course_intelligence.graph import CourseProcessorGraph

# Force mock mode for tests
os.environ["MOCK_LLM"] = "true"

# Re-import config after setting env var so the override takes effect
from course_intelligence.default_config import DEFAULT_CONFIG

_config = {**DEFAULT_CONFIG, "mock_llm": True}


def _run_pipeline(text: str) -> dict:
    """Helper: write text to a temp file and run the pipeline."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(text)
        tmp_path = f.name

    try:
        graph = CourseProcessorGraph(config=_config)
        return graph.process(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_extraction_produces_raw_text():
    """The extractor node should populate raw_text from the file."""
    result = _run_pipeline("Sepsis is a life-threatening condition caused by infection.")

    assert result.get("raw_text"), "raw_text should be populated after extraction"


def test_chunker_produces_knowledge_map():
    """The chunker should produce at least one knowledge chunk."""
    result = _run_pipeline("Sepsis is a life-threatening condition caused by infection.")

    assert len(result["knowledge_map"]) > 0, "Should produce at least one chunk"
    for chunk in result["knowledge_map"]:
        assert "chunk_id" in chunk
        assert "topic" in chunk
        assert "content" in chunk


def test_classifier_populates_blooms_levels():
    """Every chunk should get a Bloom's level and rationale."""
    result = _run_pipeline("Sepsis is a life-threatening condition caused by infection.")

    valid_levels = {"Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"}
    assert len(result["knowledge_map"]) > 0
    for chunk in result["knowledge_map"]:
        assert chunk.get("blooms_level") in valid_levels, (
            f"Chunk {chunk['chunk_id']} has invalid level: {chunk.get('blooms_level')}"
        )
        assert chunk.get("blooms_rationale"), "Rationale should be populated"
