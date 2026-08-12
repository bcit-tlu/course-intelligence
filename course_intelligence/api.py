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

from course_intelligence import storage
from course_intelligence.engine.dataflows import SUPPORTED_EXTENSIONS
from course_intelligence.db import Job, JobStatus, get_session
from course_intelligence.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)

JOB_QUEUE = "dialog:jobs"

# Local dev fallback — matches the docker-compose redis service with its
# published port (6379) on localhost.
_LOCAL_DEV_REDIS = "redis://localhost:6379/0"

app = FastAPI(
    title="Knowledge Processor",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # containerized frontend
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        "tenant_id": job.tenant_id,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "mock_llm": DEFAULT_CONFIG.get("mock_llm", False)}


@app.post("/jobs", status_code=202)
def create_job(
    file: UploadFile = File(...),
    learning_objectives: str = Form(""),
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

        return {"job_id": job.id, "status": job.status.value}
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error("Job creation failed: %s", e, exc_info=True)
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
