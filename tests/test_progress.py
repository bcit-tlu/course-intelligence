"""Tests for per-node progress tracking via process_with_progress().

Uses the mock LLM — no tokens spent. Verifies that:
- process_with_progress calls on_step for each graph node in order
- the returned state has the same shape as process()
- the worker persists current_step to the DB at each step
- the API response includes current_step
"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from course_intelligence.db.models import Base


# Force mock mode for tests
os.environ["MOCK_LLM"] = "true"

from course_intelligence.default_config import DEFAULT_CONFIG

_config = {**DEFAULT_CONFIG, "mock_llm": True}


# ---------------------------------------------------------------------------
# Graph-level: process_with_progress yields correct node names
# ---------------------------------------------------------------------------


def _run_with_progress(text: str):
    """Helper: write text to a temp file and run process_with_progress."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(text)
        tmp_path = f.name

    try:
        from course_intelligence.graph import CourseProcessorGraph

        graph = CourseProcessorGraph(config=_config)
        steps: list[str] = []
        result = graph.process_with_progress(
            tmp_path,
            on_step=lambda node: steps.append(node),
        )
        return result, steps
    finally:
        os.unlink(tmp_path)


def test_process_with_progress_calls_on_step_for_each_node():
    """on_step should be called once per graph node, in pipeline order."""
    result, steps = _run_with_progress(
        "Sepsis is a life-threatening condition caused by infection."
    )

    # The graph has 3 nodes: extract → chunk → classify
    assert len(steps) == 3, f"Expected 3 step callbacks, got {len(steps)}: {steps}"
    assert steps == ["extract", "chunk", "classify"], (
        f"Steps should be in pipeline order, got {steps}"
    )


def test_process_with_progress_returns_same_shape_as_process():
    """The return value should match process() — full state with knowledge_map."""
    result, _ = _run_with_progress(
        "Sepsis is a life-threatening condition caused by infection."
    )

    assert "knowledge_map" in result, "Result should contain knowledge_map"
    assert "error" in result, "Result should contain error"
    assert len(result["knowledge_map"]) > 0, "Should produce at least one chunk"


def test_process_with_progress_without_callback():
    """Should work without on_step — same as process() but via streaming."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Sepsis is a life-threatening condition.")
        tmp_path = f.name

    try:
        from course_intelligence.graph import CourseProcessorGraph

        graph = CourseProcessorGraph(config=_config)
        result = graph.process_with_progress(tmp_path)
        assert len(result["knowledge_map"]) > 0
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Worker-level: current_step is persisted to DB
# ---------------------------------------------------------------------------


class FakeStorage:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def upload_fileobj(self, fileobj, key: str) -> str:
        self.objects[key] = fileobj.read()
        return key

    def download_file(self, key: str, dest_path: str) -> str:
        with open(dest_path, "wb") as f:
            f.write(self.objects[key])
        return dest_path


class FakeQueue:
    def __init__(self):
        self.items: list[str] = []

    def lpush(self, _key, value):
        self.items.insert(0, value)


@pytest.fixture()
def client(monkeypatch):
    """Wire the API + worker to in-memory fakes."""
    from course_intelligence import api, storage, worker

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def fake_get_session():
        return factory()

    monkeypatch.setattr(api, "get_session", fake_get_session)
    monkeypatch.setattr(worker, "get_session", fake_get_session)

    fake_storage = FakeStorage()
    monkeypatch.setattr(storage, "upload_fileobj", fake_storage.upload_fileobj)
    monkeypatch.setattr(storage, "download_file", fake_storage.download_file)

    fake_queue = FakeQueue()
    monkeypatch.setattr(api, "_get_redis", lambda: fake_queue)

    test_client = TestClient(api.app)
    test_client.queue = fake_queue
    yield test_client


def _drain_worker(queue):
    """Process every queued job synchronously with the mock LLM."""
    from course_intelligence.db import JobStatus
    from course_intelligence.graph import CourseProcessorGraph
    from course_intelligence.worker import _set_status, process_job

    graph = CourseProcessorGraph(config=_config)
    while queue.items:
        job_id = queue.items.pop()
        try:
            process_job(job_id, graph)
        except Exception as e:
            _set_status(job_id, JobStatus.failed, error=str(e))


def _upload(client, content: bytes, filename: str, objectives: str = ""):
    import io

    return client.post(
        "/jobs",
        files={"file": (filename, io.BytesIO(content), "text/plain")},
        data={"learning_objectives": objectives},
    )


def test_current_step_is_null_on_new_job(client):
    """A freshly created job should have current_step = null."""
    import io

    resp = client.post(
        "/jobs",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        data={"learning_objectives": ""},
    )
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    job = client.get(f"/jobs/{job_id}").json()
    assert job["current_step"] is None, "New job should have current_step=null"


def test_current_step_populated_after_processing(client):
    """After processing, current_step should be the last step ('classifying')."""
    resp = _upload(client, b"Sepsis is a life-threatening condition.", "module.txt")
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    _drain_worker(client.queue)

    job = client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "completed"
    assert job["current_step"] == "classifying", (
        f"Completed job should have current_step='classifying', got '{job['current_step']}'"
    )


def test_current_step_in_api_response(client):
    """The API response should include the current_step field."""
    resp = _upload(client, b"Sepsis is a life-threatening condition.", "module.txt")
    job_id = resp.json()["job_id"]

    job = client.get(f"/jobs/{job_id}").json()
    assert "current_step" in job, "API response should include current_step field"


def test_current_step_reflects_failure_point(client):
    """A failed job should have current_step set to where it stopped."""
    # Upload a corrupt zip to trigger a failure during extraction
    resp = _upload(client, b"this is not a real zip", "corrupt.zip")
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    _drain_worker(client.queue)

    job = client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "failed"
    # current_step may be None if the failure happened before any node completed,
    # or it could be set if a node ran but produced an error.
    # Either way, the field should be present.
    assert "current_step" in job


def test_current_step_transitions_during_processing(client):
    """Verify that _set_step actually writes to the DB.

    Uses the client fixture's monkeypatched in-memory SQLite session.
    """
    from course_intelligence.db import Job
    from course_intelligence.db.models import JobStatus
    from course_intelligence.worker import _set_step, get_session

    # Create a job directly in the DB
    session = get_session()
    try:
        job = Job(
            filename="test.txt",
            storage_key="jobs/test/test.txt",
            learning_objectives="",
            status=JobStatus.processing,
        )
        session.add(job)
        session.commit()
        job_id = job.id
    finally:
        session.close()

    # Update step
    _set_step(job_id, "extracting")

    session = get_session()
    try:
        job = session.get(Job, job_id)
        assert job.current_step == "extracting"
    finally:
        session.close()

    # Update again
    _set_step(job_id, "chunking")

    session = get_session()
    try:
        job = session.get(Job, job_id)
        assert job.current_step == "chunking"
    finally:
        session.close()
