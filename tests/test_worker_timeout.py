"""Unit tests for the per-job execution timeout (signal.alarm)."""

from __future__ import annotations

import signal
import time
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from course_intelligence.db.models import Base, Job, JobStatus
from course_intelligence.default_config import DEFAULT_CONFIG
from course_intelligence.exceptions import JobTimeout
from course_intelligence.worker import _timeout_handler


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    s = factory()
    yield s
    s.close()


def _make_job(**overrides) -> Job:
    defaults = dict(
        filename="module.zip",
        storage_key="jobs/abc/module.zip",
        learning_objectives="Describe trauma systems",
    )
    defaults.update(overrides)
    return Job(**defaults)


def test_timeout_handler_raises_job_timeout():
    """The SIGALRM handler raises JobTimeout."""
    with pytest.raises(JobTimeout):
        _timeout_handler(signal.SIGALRM, None)


def test_signal_alarm_fires_after_timeout(session, monkeypatch):
    """A job whose processing exceeds job_timeout_s gets JobTimeout raised."""
    job = _make_job()
    session.add(job)
    session.commit()

    monkeypatch.setitem(DEFAULT_CONFIG, "job_timeout_s", 1)

    import course_intelligence.worker as worker

    monkeypatch.setattr(worker, "get_session", lambda: session)
    monkeypatch.setattr(worker.storage, "download_file", lambda *a, **kw: None)

    def slow_process(*args, **kwargs):
        time.sleep(3)
        return {"knowledge_map": [], "error": None}

    fake_graph = type("FakeGraph", (), {"process_with_progress": slow_process})()

    with pytest.raises(JobTimeout):
        worker.process_job(job.id, fake_graph)


def test_signal_alarm_cancelled_on_success(session, monkeypatch):
    """signal.alarm(0) is called after successful processing — no lingering alarm."""
    job = _make_job()
    session.add(job)
    session.commit()

    monkeypatch.setitem(DEFAULT_CONFIG, "job_timeout_s", 10)

    import course_intelligence.worker as worker

    monkeypatch.setattr(worker, "get_session", lambda: session)
    monkeypatch.setattr(worker.storage, "download_file", lambda *a, **kw: None)
    monkeypatch.setattr(worker, "cleanup_old_uploads", lambda: None)

    def fast_process(*args, **kwargs):
        return {"knowledge_map": [{"topic": "T", "content": "C"}], "error": None}

    fake_graph = type("FakeGraph", (), {"process_with_progress": fast_process})()

    worker.process_job(job.id, fake_graph)

    refreshed = session.get(Job, job.id)
    assert refreshed.status == JobStatus.completed

    remaining = signal.alarm(0)
    assert remaining == 0, "alarm was not cancelled after successful processing"
