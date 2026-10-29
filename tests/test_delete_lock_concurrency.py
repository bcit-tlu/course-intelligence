"""Postgres-gated tests for the delete_job / _claim_job row-lock coordination.

These verify the TOCTOU fix on a real database: SQLite ignores
``SELECT ... FOR UPDATE``, so the lock-based coordination between
``delete_job`` and the worker's ``_claim_job`` can only be exercised
against Postgres. The suite skips entirely when Postgres is unreachable
(mirroring the pattern in test_db.py).

Coverage:
  - delete-first outcome through the actual code paths (delete_job then
    _claim_job sees the row gone and returns None).
  - claim-first outcome through the actual code paths (_claim_job then
    delete_job sees "processing" and returns 409).
  - a raw two-session test proving FOR UPDATE genuinely blocks the
    second transaction until the first commits, for both interleavings.
"""

from __future__ import annotations

import threading
import time

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from course_intelligence import api, storage, worker
from course_intelligence.db.models import Base, Job, JobStatus
from course_intelligence.db.session import get_database_url, get_session


def _postgres_available() -> bool:
    try:
        engine = create_engine(get_database_url(), connect_args={"connect_timeout": 2})
        with engine.connect():
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(), reason="Postgres not reachable"
)


@pytest.fixture()
def pg_session():
    """A session against the real (migrated) Postgres schema.

    Assumes migrations have been applied (same as test_db.py's integration
    test). Yields a session and cleans up any job it created. Cleanup is
    best-effort: a test may have already deleted the job.
    """
    created: list[str] = []
    session = get_session()
    try:
        yield session, created
    finally:
        session.close()
        # Cleanup in a fresh session so it always sees committed state.
        cleanup = get_session()
        try:
            for job_id in created:
                cleanup.query(Job).filter(Job.id == job_id).delete(
                    synchronize_session=False
                )
            cleanup.commit()
        finally:
            cleanup.close()


def _make_job(session, created, **overrides) -> Job:
    defaults = dict(
        filename="module.zip",
        storage_key="jobs/abc/module.zip",
        learning_objectives="Describe trauma systems",
    )
    defaults.update(overrides)
    job = Job(**defaults)
    session.add(job)
    session.commit()
    created.append(job.id)
    return job


def _stub_external_deps(monkeypatch):
    """Neutralize S3 and Redis so delete_job only exercises the DB."""
    monkeypatch.setattr(storage, "delete_object", lambda key: None)
    monkeypatch.setattr(api, "_get_redis", lambda: type("Q", (), {"lrem": lambda *a, **k: None})())


# --- Outcome tests through the actual code paths ---


def test_delete_first_then_claim_returns_none(pg_session, monkeypatch):
    """delete_job commits first; _claim_job then sees the row gone."""
    session, created = pg_session
    _stub_external_deps(monkeypatch)
    job = _make_job(session, created, status=JobStatus.queued)

    # delete_job uses its own session (api.get_session -> real Postgres)
    resp = api.delete_job(job.id, None, None)
    assert resp.status_code == 204

    # Worker claim now finds nothing
    assert worker._claim_job(job.id) is None


def test_claim_first_then_delete_returns_409(pg_session, monkeypatch):
    """_claim_job commits 'processing' first; delete_job then sees 409."""
    session, created = pg_session
    _stub_external_deps(monkeypatch)
    job = _make_job(session, created, status=JobStatus.queued)

    claimed = worker._claim_job(job.id)
    assert claimed is not None
    storage_key, filename, learning_objectives = claimed
    assert filename == "module.zip"

    with pytest.raises(HTTPException) as exc:
        api.delete_job(job.id, None, None)
    assert exc.value.status_code == 409

    # Job still exists and is processing — read in a fresh session so we
    # see the status _claim_job committed (the fixture session's identity
    # map is stale because expire_on_commit=False).
    check = get_session()
    try:
        refreshed = check.get(Job, job.id)
        assert refreshed.status == JobStatus.processing
    finally:
        check.close()


# --- Lock semantics: prove FOR UPDATE actually blocks ---


def test_for_update_blocks_until_delete_commits(pg_session):
    """A second FOR UPDATE transaction blocks until the first commits the
    delete, then sees the row is gone."""
    session, created = pg_session
    job = _make_job(session, created, status=JobStatus.queued)
    session.close()

    # Session A locks the row and holds the lock (no commit yet)
    session_a = get_session()
    locked = session_a.execute(
        select(Job).where(Job.id == job.id).with_for_update()
    ).scalar_one()

    outcome: dict = {}
    started = threading.Event()
    done = threading.Event()

    def try_lock():
        session_b = get_session()
        started.set()
        row = session_b.execute(
            select(Job).where(Job.id == job.id).with_for_update()
        ).scalar_one_or_none()
        outcome["row"] = row
        session_b.commit()
        session_b.close()
        done.set()

    t = threading.Thread(target=try_lock)
    t.start()
    started.wait()
    time.sleep(0.5)
    # Still blocked — proves the row lock is held
    assert not done.is_set(), "second transaction should block on the row lock"

    # Commit the delete in A — releases the lock
    session_a.delete(locked)
    session_a.commit()
    session_a.close()

    assert done.wait(timeout=5), "second transaction should unblock after commit"
    t.join(timeout=5)
    assert outcome["row"] is None, "second transaction should see the row deleted"


def test_for_update_blocks_until_claim_commits(pg_session):
    """A second FOR UPDATE transaction blocks until the first commits the
    status change, then sees the new status."""
    session, created = pg_session
    job = _make_job(session, created, status=JobStatus.queued)
    session.close()

    # Session A locks the row and holds the lock (no commit yet)
    session_a = get_session()
    locked = session_a.execute(
        select(Job).where(Job.id == job.id).with_for_update()
    ).scalar_one()

    outcome: dict = {}
    started = threading.Event()
    done = threading.Event()

    def try_lock():
        session_b = get_session()
        started.set()
        row = session_b.execute(
            select(Job).where(Job.id == job.id).with_for_update()
        ).scalar_one_or_none()
        outcome["status"] = row.status.value if row else None
        session_b.rollback()
        session_b.close()
        done.set()

    t = threading.Thread(target=try_lock)
    t.start()
    started.wait()
    time.sleep(0.5)
    assert not done.is_set(), "second transaction should block on the row lock"

    # Commit the status change in A — releases the lock
    locked.status = JobStatus.processing
    session_a.commit()
    session_a.close()

    assert done.wait(timeout=5), "second transaction should unblock after commit"
    t.join(timeout=5)
    assert outcome["status"] == "processing", (
        "second transaction should see the committed 'processing' status"
    )
