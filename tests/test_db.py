"""Tests for the course_intelligence.db package: models, session URL handling, and
an optional integration test against the real Postgres.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from course_intelligence.db.models import Base, Job, JobStatus, Result
from course_intelligence.db.session import get_database_url


# --- Unit tests (SQLite in-memory, no infrastructure needed) ---


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


def test_job_defaults(session):
    job = _make_job()
    session.add(job)
    session.commit()

    fetched = session.get(Job, job.id)
    assert fetched.status == JobStatus.queued
    assert fetched.error is None
    assert fetched.created_at is not None
    assert fetched.updated_at is not None


def test_job_status_transition(session):
    job = _make_job()
    session.add(job)
    session.commit()

    job.status = JobStatus.processing
    session.commit()
    assert session.get(Job, job.id).status == JobStatus.processing

    job.status = JobStatus.completed
    session.commit()
    assert session.get(Job, job.id).status == JobStatus.completed


def test_job_result_relationship(session):
    job = _make_job()
    session.add(job)
    session.commit()

    session.add_all([
        Result(job_id=job.id, topic="Trauma Systems", content="...", page_number=3),
        Result(job_id=job.id, topic="Golden Hour", content="...", page_number=5),
    ])
    session.commit()

    fetched = session.get(Job, job.id)
    assert len(fetched.results) == 2
    assert {r.topic for r in fetched.results} == {"Trauma Systems", "Golden Hour"}
    assert fetched.results[0].blooms_level is None  # filled later by classifier


def test_cascade_delete(session):
    job = _make_job()
    session.add(job)
    session.commit()
    session.add(Result(job_id=job.id, topic="T", content="C"))
    session.commit()

    session.delete(session.get(Job, job.id))
    session.commit()

    assert session.query(Result).count() == 0


def test_list_jobs_ordered_by_created_at_desc(session):
    """GET /jobs returns most-recent first."""
    import time as _time

    first = _make_job(filename="first.zip")
    session.add(first)
    session.commit()
    _time.sleep(0.01)

    second = _make_job(filename="second.zip")
    session.add(second)
    session.commit()

    jobs = (
        session.query(Job).order_by(Job.created_at.desc()).limit(50).all()
    )
    assert len(jobs) == 2
    assert jobs[0].filename == "second.zip"
    assert jobs[1].filename == "first.zip"


def test_list_jobs_filter_by_status(session):
    """GET /jobs?status=completed returns only completed jobs."""
    queued = _make_job(filename="queued.zip")
    session.add(queued)
    session.commit()

    done = _make_job(filename="done.zip")
    done.status = JobStatus.completed
    session.add(done)
    session.commit()

    jobs = (
        session.query(Job)
        .filter(Job.status == JobStatus.completed)
        .order_by(Job.created_at.desc())
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].filename == "done.zip"


def test_list_jobs_filter_by_tenant_id(session):
    """GET /jobs with X-Tenant-Id returns only that tenant's jobs."""
    a = _make_job(filename="a.zip", tenant_id="tenant-a")
    b = _make_job(filename="b.zip", tenant_id="tenant-b")
    c = _make_job(filename="c.zip")  # no tenant
    session.add_all([a, b, c])
    session.commit()

    jobs = (
        session.query(Job)
        .filter(Job.tenant_id == "tenant-a")
        .order_by(Job.created_at.desc())
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].filename == "a.zip"

    # Unfiltered returns all
    all_jobs = session.query(Job).order_by(Job.created_at.desc()).all()
    assert len(all_jobs) == 3


def test_list_jobs_limit(session):
    """GET /jobs?limit=N caps the response."""
    for i in range(5):
        session.add(_make_job(filename=f"job-{i}.zip"))
    session.commit()

    jobs = session.query(Job).order_by(Job.created_at.desc()).limit(2).all()
    assert len(jobs) == 2


def test_get_database_url_normalizes_psycopg_driver(monkeypatch):
    from course_intelligence import default_config

    monkeypatch.setitem(
        default_config.DEFAULT_CONFIG,
        "database_url",
        "postgresql://u:p@host:5432/db",
    )
    assert get_database_url() == "postgresql+psycopg://u:p@host:5432/db"


# --- Integration test (real Postgres; skipped if unreachable) ---


def _postgres_available() -> bool:
    try:
        engine = create_engine(get_database_url(), connect_args={"connect_timeout": 2})
        with engine.connect():
            return True
    except Exception:
        return False


@pytest.mark.skipif(not _postgres_available(), reason="Postgres not reachable")
def test_postgres_round_trip():
    """Insert/query/delete against the real (migrated) Postgres schema."""
    from course_intelligence.db.session import get_session

    session = get_session()
    try:
        job = _make_job(filename="integration-test.zip")
        session.add(job)
        session.commit()

        session.add(Result(job_id=job.id, topic="IT Topic", content="IT Content"))
        session.commit()

        fetched = session.get(Job, job.id)
        assert fetched.status == JobStatus.queued
        assert len(fetched.results) == 1
    finally:
        session.delete(session.get(Job, job.id))
        session.commit()
        session.close()
