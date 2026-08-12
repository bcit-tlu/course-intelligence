"""Integration test for the async job flow — happy path + failure cases.

CI-friendly: MOCK_LLM=true, in-memory SQLite, and in-memory fakes for
object storage and the Redis queue. No external services required.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from course_intelligence.db.models import Base


# --- Fakes for the infra the API/worker touch ---


class FakeStorage:
    """In-memory object store standing in for MinIO/S3."""

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
    """Minimal Redis stand-in: only the ops the API uses."""

    def __init__(self):
        self.items: list[str] = []

    def lpush(self, _key, value):
        self.items.insert(0, value)


@pytest.fixture()
def client(monkeypatch):
    """Wire the API + worker to in-memory fakes and yield a test client
    plus the shared fakes so the test can drive the worker."""
    from course_intelligence import api, storage, worker

    # Shared in-memory SQLite across API and worker sessions
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
    """Process every queued job synchronously with the mock LLM.

    Mirrors the worker run() loop's per-job error handling: a failing
    job is marked failed instead of propagating.
    """
    from course_intelligence.db import JobStatus
    from course_intelligence.default_config import DEFAULT_CONFIG
    from course_intelligence.engine import CourseProcessorGraph
    from course_intelligence.worker import _set_status, process_job

    graph = CourseProcessorGraph(config={**DEFAULT_CONFIG, "mock_llm": True})
    while queue.items:
        job_id = queue.items.pop()
        try:
            process_job(job_id, graph)
        except Exception as e:
            _set_status(job_id, JobStatus.failed, error=str(e))


def _upload(client, content: bytes, filename: str, objectives: str = ""):
    return client.post(
        "/jobs",
        files={"file": (filename, io.BytesIO(content), "text/plain")},
        data={"learning_objectives": objectives},
    )


# --- Happy path ---


def test_full_job_flow(client):
    # 1. Submit
    resp = _upload(client, b"Sepsis is a life-threatening condition.", "module.txt",
                   "Define sepsis")
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    assert resp.json()["status"] == "queued"

    # 2. Queued status + 409 before processing
    assert client.get(f"/jobs/{job_id}").json()["status"] == "queued"
    assert client.get(f"/jobs/{job_id}/results").status_code == 409

    # 3. Process
    _drain_worker(client.queue)

    # 4. Completed with well-formed results
    assert client.get(f"/jobs/{job_id}").json()["status"] == "completed"
    results = client.get(f"/jobs/{job_id}/results")
    assert results.status_code == 200
    elements = results.json()["elements"]
    assert len(elements) > 0
    valid_levels = {"Remember", "Understand", "Apply", "Analyze",
                    "Evaluate", "Create", "unclassified"}
    for el in elements:
        assert el["topic"]
        assert el["content"]
        assert el["blooms_level"] in valid_levels


# --- Failure cases ---


def test_unsupported_extension_returns_400(client):
    resp = _upload(client, b"x", "bad.xyz")
    assert resp.status_code == 400


def test_unknown_job_returns_404(client):
    assert client.get("/jobs/does-not-exist").status_code == 404
    assert client.get("/jobs/does-not-exist/results").status_code == 404


def test_corrupt_zip_marks_failed_and_survives(client):
    resp = _upload(client, b"this is not a real zip", "corrupt.zip")
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    _drain_worker(client.queue)

    job = client.get(f"/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert job["error"]

    # Worker survived: a subsequent good job still completes
    good = _upload(client, b"Trauma care basics.", "ok.txt")
    _drain_worker(client.queue)
    assert client.get(f"/jobs/{good.json()['job_id']}").json()["status"] == "completed"
