"""Unit tests for the stale-job watchdog (_reap_stale_jobs)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from course_intelligence.db.models import Base, Job, JobStatus
from course_intelligence.default_config import DEFAULT_CONFIG


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


def test_reap_stale_job_marks_old_processing_as_failed(session, monkeypatch):
    """A processing job with an old updated_at is marked failed."""
    job = _make_job()
    job.status = JobStatus.processing
    job.updated_at = datetime.now(timezone.utc) - timedelta(seconds=1200)
    session.add(job)
    session.commit()

    monkeypatch.setitem(DEFAULT_CONFIG, "watchdog_stale_threshold_s", 900)

    import course_intelligence.worker as worker

    monkeypatch.setattr(worker, "get_session", lambda: session)

    worker._reap_stale_jobs()

    refreshed = session.get(Job, job.id)
    assert refreshed.status == JobStatus.failed
    assert "no progress" in (refreshed.error or "")


def test_reap_stale_job_skips_recent_processing(session, monkeypatch):
    """A processing job with a recent updated_at is NOT reaped."""
    job = _make_job()
    job.status = JobStatus.processing
    job.updated_at = datetime.now(timezone.utc) - timedelta(seconds=30)
    session.add(job)
    session.commit()

    monkeypatch.setitem(DEFAULT_CONFIG, "watchdog_stale_threshold_s", 900)

    import course_intelligence.worker as worker

    monkeypatch.setattr(worker, "get_session", lambda: session)

    worker._reap_stale_jobs()

    refreshed = session.get(Job, job.id)
    assert refreshed.status == JobStatus.processing
    assert refreshed.error is None


def test_reap_stale_job_skips_completed_and_failed(session, monkeypatch):
    """Completed and failed jobs are never reaped, regardless of updated_at."""
    old = datetime.now(timezone.utc) - timedelta(seconds=99999)

    done = _make_job(filename="done.zip")
    done.status = JobStatus.completed
    done.updated_at = old
    session.add(done)

    failed = _make_job(filename="failed.zip")
    failed.status = JobStatus.failed
    failed.updated_at = old
    session.add(failed)
    session.commit()

    monkeypatch.setitem(DEFAULT_CONFIG, "watchdog_stale_threshold_s", 900)

    import course_intelligence.worker as worker

    monkeypatch.setattr(worker, "get_session", lambda: session)

    worker._reap_stale_jobs()

    assert session.get(Job, done.id).status == JobStatus.completed
    assert session.get(Job, failed.id).status == JobStatus.failed


def test_reap_stale_job_skips_queued(session, monkeypatch):
    """Queued jobs are never reaped."""
    job = _make_job()
    job.updated_at = datetime.now(timezone.utc) - timedelta(seconds=99999)
    session.add(job)
    session.commit()

    monkeypatch.setitem(DEFAULT_CONFIG, "watchdog_stale_threshold_s", 900)

    import course_intelligence.worker as worker

    monkeypatch.setattr(worker, "get_session", lambda: session)

    worker._reap_stale_jobs()

    assert session.get(Job, job.id).status == JobStatus.queued
