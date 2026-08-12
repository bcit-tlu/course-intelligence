"""Background worker: dequeues jobs from Redis and runs the pipeline.

Uses the reliable queue pattern from the Redis docs (LMOVE): jobs are
atomically moved to a processing list while being worked on, removed
(LREM) once done, and reclaimed on startup if a previous worker run
crashed mid-job.

Loop: BLMOVE dialog:jobs → dialog:jobs:processing → load job from
Postgres → download upload from MinIO → run CourseProcessorGraph →
save results → mark completed/failed → LREM from processing list.
"""

from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path

import redis as redis_lib

from course_intelligence import storage
from course_intelligence.db import Job, JobStatus, Result, get_session
from course_intelligence.default_config import DEFAULT_CONFIG
from course_intelligence.engine import CourseProcessorGraph
from course_intelligence.engine.graph.steps import NODE_TO_STEP

logger = logging.getLogger(__name__)

JOB_QUEUE = "dialog:jobs"
PROCESSING_QUEUE = "dialog:jobs:processing"
BLOCK_TIMEOUT_S = 5

_LOCAL_DEV_REDIS = "redis://localhost:6379/0"


def _get_redis():
    return redis_lib.Redis.from_url(
        DEFAULT_CONFIG.get("redis_url") or _LOCAL_DEV_REDIS,
        # Must exceed the BLMOVE timeout, or idle blocking pops raise
        # a socket TimeoutError.
        socket_timeout=BLOCK_TIMEOUT_S + 5,
    )


def _set_status(job_id: str, status: JobStatus, error: str | None = None) -> None:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if job is None:
            return
        job.status = status
        job.error = error
        session.commit()
    finally:
        session.close()


def _set_step(job_id: str, step: str | None) -> None:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if job is None:
            return
        job.current_step = step
        session.commit()
    finally:
        session.close()


def process_job(job_id: str, graph: CourseProcessorGraph) -> None:
    """Process a single job: download, run pipeline, save results."""
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if job is None:
            logger.warning("Job %s not found in DB — skipping", job_id)
            return
        storage_key = job.storage_key
        filename = job.filename
        learning_objectives = job.learning_objectives
    finally:
        session.close()

    _set_status(job_id, JobStatus.processing)
    logger.info("Job %s: processing (%s)", job_id, filename)
    started = time.monotonic()

    with tempfile.TemporaryDirectory() as tmp_dir:
        local_path = str(Path(tmp_dir) / filename)
        storage.download_file(storage_key, local_path)

        result = graph.process_with_progress(
            local_path,
            learning_objectives,
            on_step=lambda node: _set_step(
                job_id, NODE_TO_STEP.get(node, node)
            ),
        )

    error = result.get("error")
    knowledge_map = result.get("knowledge_map", [])

    if not knowledge_map:
        raise RuntimeError(error or "Pipeline produced no results")

    session = get_session()
    try:
        # Idempotency: a reclaimed job may have partially saved results
        # from a crashed run — clear them before re-inserting.
        session.query(Result).filter_by(job_id=job_id).delete()
        for chunk in knowledge_map:
            session.add(
                Result(
                    job_id=job_id,
                    topic=chunk.get("topic", "Untitled"),
                    content=chunk.get("content", ""),
                    blooms_level=chunk.get("blooms_level"),
                    blooms_rationale=chunk.get("blooms_rationale"),
                    source_page=chunk.get("source_page"),
                    page_number=chunk.get("page_number"),
                )
            )
        job = session.get(Job, job_id)
        job.status = JobStatus.completed
        # Partial page failures are recorded but don't fail the job
        job.error = error
        session.commit()
    finally:
        session.close()

    elapsed = time.monotonic() - started
    logger.info(
        "Job %s: completed — %d elements in %.1fs%s",
        job_id, len(knowledge_map), elapsed,
        f" (partial: {error})" if error else "",
    )

    cleanup_old_uploads()


def cleanup_old_uploads() -> None:
    """Delete S3 uploads beyond the retention count.

    Keeps uploads for the N most recent completed+failed jobs.
    Older jobs have their S3 object deleted and storage_key blanked.
    Job and Result rows are preserved in Postgres.
    """
    keep = DEFAULT_CONFIG.get("retention_count", 10)
    session = get_session()
    try:
        old_jobs = (
            session.query(Job)
            .filter(Job.status.in_([JobStatus.completed, JobStatus.failed]))
            .filter(Job.storage_key != "")
            .order_by(Job.created_at.desc())
            .offset(keep)
            .all()
        )
        for job in old_jobs:
            storage.delete_object(job.storage_key)
            session.delete(job)
        if old_jobs:
            session.commit()
            logger.info("Purged %d old upload(s)", len(old_jobs))
    finally:
        session.close()


def _reclaim_stale_jobs(redis_client) -> None:
    """Requeue jobs left in the processing list by a crashed worker run.

    Per the Redis reliable-queue pattern: anything still in the
    processing list at startup was claimed but never finished.
    """
    reclaimed = 0
    while redis_client.lmove(PROCESSING_QUEUE, JOB_QUEUE, "RIGHT", "RIGHT"):
        reclaimed += 1
    if reclaimed:
        logger.warning("Reclaimed %d stale job(s) from a previous run", reclaimed)


def run() -> None:
    """Run the worker loop forever."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    redis_client = _get_redis()
    graph = CourseProcessorGraph(config=DEFAULT_CONFIG)
    _reclaim_stale_jobs(redis_client)
    logger.info("Worker started — waiting for jobs on '%s'...", JOB_QUEUE)

    while True:
        try:
            # Atomically claim the job: move it to the processing list
            raw_job_id = redis_client.blmove(
                JOB_QUEUE, PROCESSING_QUEUE, BLOCK_TIMEOUT_S, "RIGHT", "LEFT"
            )
            if raw_job_id is None:
                continue
            job_id = raw_job_id.decode()

            try:
                process_job(job_id, graph)
            except Exception as e:
                logger.error("Job %s: failed — %s", job_id, e, exc_info=True)
                _set_status(job_id, JobStatus.failed, error=str(e))
            finally:
                # Done (completed or marked failed) — release the claim
                redis_client.lrem(PROCESSING_QUEUE, 1, job_id)
        except KeyboardInterrupt:
            logger.info("Worker shutting down.")
            break
        except redis_lib.exceptions.TimeoutError:
            # Benign: no job arrived within the socket timeout window
            continue
        except redis_lib.exceptions.ConnectionError as e:
            logger.error("Redis connection error: %s — retrying in 5s", e)
            time.sleep(5)
