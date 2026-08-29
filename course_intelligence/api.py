"""FastAPI application — async job API.

Flow: POST /jobs stores the upload in MinIO, creates a job row in
Postgres, and enqueues the job id in Redis. The worker picks it up.
Clients poll GET /jobs/{id} and fetch GET /jobs/{id}/results when done.
"""

from __future__ import annotations

import logging
from pathlib import Path

import redis as redis_lib
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from course_intelligence import storage
from course_intelligence.analytics import (
    emit_event,
    file_size_uploaded,
    jobs_failed,
    jobs_submitted,
)
from course_intelligence.engine.dataflows import SUPPORTED_EXTENSIONS
from course_intelligence.db import Job, JobStatus, get_session
from course_intelligence.db.session import get_engine
from course_intelligence.default_config import DEFAULT_CONFIG
from course_intelligence.observability import setup_otel, instrument_shared

logger = logging.getLogger(__name__)

setup_otel("course-intelligence-api")

JOB_QUEUE = "course-intelligence:jobs"

# Local dev fallback — matches the docker-compose redis service with its
# published port (6379) on localhost.
_LOCAL_DEV_REDIS = "redis://localhost:6379/0"

app = FastAPI(
    title="Course Intelligence API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # containerized studio
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

FastAPIInstrumentor.instrument_app(app)
instrument_shared(engine=get_engine())


def _get_redis():
    return redis_lib.Redis.from_url(
        DEFAULT_CONFIG.get("redis_url") or _LOCAL_DEV_REDIS
    )


def _job_to_dict(job: Job) -> dict:
    return {
        "job_id": job.id,
        "status": job.status.value,
        "filename": job.filename,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "error": job.error,
        "current_step": job.current_step,
        "step_progress": job.step_progress,
        "tenant_id": job.tenant_id,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "mock_llm": DEFAULT_CONFIG.get("mock_llm", False)}


@app.post("/jobs", status_code=202)
def create_job(
    file: UploadFile = File(...),
    learning_objectives: str = Form(""),
    x_tenant_id: str | None = Header(default=None),
):
    """Accept a course upload, store it, and queue it for processing."""
    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type '{suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    session = get_session()
    try:
        job = Job(
            filename=filename,
            storage_key="",  # set below once we know the job id
            learning_objectives=learning_objectives,
            tenant_id=x_tenant_id,
        )
        session.add(job)
        session.flush()  # assigns job.id

        # Stream the upload to object storage (no full-memory buffering)
        storage_key = f"jobs/{job.id}/{filename}"
        storage.upload_fileobj(file.file, storage_key)
        job.storage_key = storage_key
        session.commit()

        # Enqueue for the worker
        _get_redis().lpush(JOB_QUEUE, job.id)
        logger.info("Job %s queued (%s)", job.id, filename)

        tenant_id = job.tenant_id or "unknown"
        file_size = file.size or 0
        emit_event("ci.job.submitted", {
            "job.id": job.id,
            "job.filename": filename,
            "job.file_type": suffix,
            "job.file_size": file_size,
            "job.tenant_id": tenant_id,
            "job.has_learning_objectives": bool(learning_objectives),
        })
        jobs_submitted.add(1, {"tenant_id": tenant_id, "file_type": suffix})
        file_size_uploaded.record(file_size, {"file_type": suffix})

        return {"job_id": job.id, "status": job.status.value}
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error("Job creation failed: %s", e, exc_info=True)
        emit_event("ci.job.upload_failed", {
            "job.filename": filename,
            "job.file_type": suffix,
            "error": str(e),
        })
        jobs_failed.add(1, {"tenant_id": x_tenant_id or "unknown", "stage": "upload"})
        raise HTTPException(500, f"Job creation failed: {e}")
    finally:
        session.close()


@app.get("/jobs")
def list_jobs(
    limit: int = 50,
    status: JobStatus | None = None,
    x_tenant_id: str | None = Header(default=None),
):
    """List jobs, optionally filtered by status and/or tenant."""
    session = get_session()
    try:
        query = session.query(Job).order_by(Job.created_at.desc())
        if status is not None:
            query = query.filter(Job.status == status)
        if x_tenant_id is not None:
            query = query.filter(Job.tenant_id == x_tenant_id)
        jobs = query.limit(limit).all()
        emit_event("ci.jobs.listed", {
            "jobs.count": len(jobs),
            "jobs.filter_status": status.value if status else None,
            "jobs.tenant_id": x_tenant_id,
        })
        return {"jobs": [_job_to_dict(j) for j in jobs]}
    finally:
        session.close()


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    """Return the current status of a job."""
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        return _job_to_dict(job)
    finally:
        session.close()


@app.get("/jobs/{job_id}/results")
def get_job_results(job_id: str):
    """Return the learning elements for a completed job."""
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        if job.status != JobStatus.completed:
            raise HTTPException(
                409, f"Job is not completed (status: {job.status.value})"
            )
        emit_event("ci.results.viewed", {
            "job.id": job_id,
            "job.tenant_id": job.tenant_id,
            "results.count": len(job.results),
        })
        return {
            "job_id": job.id,
            "filename": job.filename,
            "elements": [
                {
                    "id": r.id,
                    "topic": r.topic,
                    "content": r.content,
                    "blooms_level": r.blooms_level,
                    "blooms_rationale": r.blooms_rationale,
                    "source_page": r.source_page,
                    "page_number": r.page_number,
                }
                for r in job.results
            ],
        }
    finally:
        session.close()
