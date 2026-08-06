"""Tests for S3 upload retention cleanup (cleanup_old_uploads)."""

from __future__ import annotations

import time as _time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import dialog.worker as worker_mod
from dialog.db.models import Base, Job, JobStatus


@pytest.fixture()
def session():
    """In-memory SQLite session with tables created from the models."""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


def _make_job(**overrides) -> Job:
    defaults = dict(
        filename="module.zip",
        storage_key="jobs/abc/module.zip",
        learning_objectives="Describe trauma systems",
    )
    defaults.update(overrides)
    return Job(**defaults)


def _seed_jobs(session, n_completed, n_failed=0, n_queued=0):
    """Insert jobs with staggered created_at timestamps."""
    for i in range(n_completed):
        job = _make_job(filename=f"done-{i}.zip", storage_key=f"jobs/done-{i}.zip")
        job.status = JobStatus.completed
        session.add(job)
        session.commit()
        _time.sleep(0.01)

    for i in range(n_failed):
        job = _make_job(filename=f"fail-{i}.zip", storage_key=f"jobs/fail-{i}.zip")
        job.status = JobStatus.failed
        session.add(job)
        session.commit()
        _time.sleep(0.01)

    for i in range(n_queued):
        job = _make_job(filename=f"queued-{i}.zip", storage_key=f"jobs/queued-{i}.zip")
        session.add(job)
        session.commit()
        _time.sleep(0.01)


def test_purges_beyond_retention_count(session, monkeypatch):
    """With retention_count=3 and 5 completed jobs, oldest 2 are purged."""
    _seed_jobs(session, n_completed=5)

    deleted_keys: list[str] = []
    monkeypatch.setattr(worker_mod.storage, "delete_object", lambda key: deleted_keys.append(key))
    monkeypatch.setattr(worker_mod, "get_session", lambda: session)
    monkeypatch.setitem(worker_mod.DEFAULT_CONFIG, "retention_count", 3)

    worker_mod.cleanup_old_uploads()

    assert len(deleted_keys) == 2
    # The 2 oldest completed jobs should be purged (done-0, done-1)
    remaining = (
        session.query(Job)
        .filter(Job.status == JobStatus.completed)
        .filter(Job.storage_key != "")
        .order_by(Job.created_at.desc())
        .all()
    )
    assert len(remaining) == 3
    remaining_names = {j.filename for j in remaining}
    assert remaining_names == {"done-2.zip", "done-3.zip", "done-4.zip"}


def test_no_purge_when_under_count(session, monkeypatch):
    """With retention_count=10 and 3 completed jobs, nothing is purged."""
    _seed_jobs(session, n_completed=3)

    deleted_keys: list[str] = []
    monkeypatch.setattr(worker_mod.storage, "delete_object", lambda key: deleted_keys.append(key))
    monkeypatch.setattr(worker_mod, "get_session", lambda: session)
    monkeypatch.setitem(worker_mod.DEFAULT_CONFIG, "retention_count", 10)

    worker_mod.cleanup_old_uploads()

    assert len(deleted_keys) == 0


def test_queued_jobs_not_purged(session, monkeypatch):
    """Queued/processing jobs are never touched regardless of count."""
    _seed_jobs(session, n_completed=2, n_queued=5)

    deleted_keys: list[str] = []
    monkeypatch.setattr(worker_mod.storage, "delete_object", lambda key: deleted_keys.append(key))
    monkeypatch.setattr(worker_mod, "get_session", lambda: session)
    monkeypatch.setitem(worker_mod.DEFAULT_CONFIG, "retention_count", 1)

    worker_mod.cleanup_old_uploads()

    # Only 1 completed job beyond retention=1 is purged; queued jobs untouched
    assert len(deleted_keys) == 1
    queued = session.query(Job).filter(Job.status == JobStatus.queued).all()
    assert len(queued) == 5
    assert all(j.storage_key != "" for j in queued)


def test_failed_jobs_counted(session, monkeypatch):
    """Failed jobs are included in the retention count and can be purged."""
    _seed_jobs(session, n_completed=2, n_failed=3)

    deleted_keys: list[str] = []
    monkeypatch.setattr(worker_mod.storage, "delete_object", lambda key: deleted_keys.append(key))
    monkeypatch.setattr(worker_mod, "get_session", lambda: session)
    monkeypatch.setitem(worker_mod.DEFAULT_CONFIG, "retention_count", 2)

    worker_mod.cleanup_old_uploads()

    # 5 total completed+failed, keep 2, purge 3
    assert len(deleted_keys) == 3


def test_already_purged_not_re_deleted(session, monkeypatch):
    """Jobs with blanked storage_key are not re-attempted."""
    _seed_jobs(session, n_completed=5)

    # Blank the oldest 2 storage_keys manually (simulate prior purge)
    jobs = (
        session.query(Job)
        .filter(Job.status == JobStatus.completed)
        .order_by(Job.created_at.asc())
        .all()
    )
    jobs[0].storage_key = ""
    jobs[1].storage_key = ""
    session.commit()

    deleted_keys: list[str] = []
    monkeypatch.setattr(worker_mod.storage, "delete_object", lambda key: deleted_keys.append(key))
    monkeypatch.setattr(worker_mod, "get_session", lambda: session)
    monkeypatch.setitem(worker_mod.DEFAULT_CONFIG, "retention_count", 3)

    worker_mod.cleanup_old_uploads()

    # 5 completed, 2 already blanked (excluded by filter), 3 have keys, keep 3 → 0 purged
    assert len(deleted_keys) == 0


def test_storage_key_blanked_after_purge(session, monkeypatch):
    """Purged jobs have storage_key set to empty string."""
    _seed_jobs(session, n_completed=5)

    monkeypatch.setattr(worker_mod.storage, "delete_object", lambda key: None)
    monkeypatch.setattr(worker_mod, "get_session", lambda: session)
    monkeypatch.setitem(worker_mod.DEFAULT_CONFIG, "retention_count", 3)

    worker_mod.cleanup_old_uploads()

    purged = (
        session.query(Job)
        .filter(Job.status == JobStatus.completed)
        .filter(Job.storage_key == "")
        .all()
    )
    assert len(purged) == 2
