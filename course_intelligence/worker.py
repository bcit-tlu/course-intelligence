"""Background worker: dequeues jobs from Redis and runs the pipeline.

Uses the reliable queue pattern from the Redis docs (LMOVE): jobs are
atomically moved to a processing list while being worked on, removed
(LREM) once done, and reclaimed on startup if a previous worker run
crashed mid-job.

Loop: BLMOVE course-intelligence:jobs → course-intelligence:jobs:processing → load job from
Postgres → download upload from MinIO → run CourseProcessorGraph →
save results → mark completed/failed → LREM from processing list.
"""

from __future__ import annotations

import logging
import signal
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import redis as redis_lib
from opentelemetry import trace, metrics

from course_intelligence import storage
from course_intelligence.analytics import (
    emit_event,
    elements_produced,
    job_processing_time,
    jobs_completed,
    jobs_failed,
)
from course_intelligence.db import Job, JobStatus, Result, get_session
from course_intelligence.exceptions import JobTimeout
from course_intelligence.default_config import DEFAULT_CONFIG
from course_intelligence.engine import CourseProcessorGraph
from course_intelligence.engine.graph.progress_context import set_progress_callback
from course_intelligence.engine.graph.steps import NODE_TO_STEP
from course_intelligence.observability import setup_otel, instrument_shared

logger = logging.getLogger(__name__)

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

jobs_counter = meter.create_counter(
    "ci.jobs.total", unit="1", description="Total jobs processed"
)
job_duration = meter.create_histogram(
    "ci.job.duration.seconds", unit="s", description="Job processing duration"
)
elements_counter = meter.create_counter(
    "ci.job.elements.total", unit="1", description="Total learning elements produced"
)
step_duration = meter.create_histogram(
    "ci.pipeline.step.duration.seconds",
    unit="s",
    description="Duration per pipeline step",
)
classified_counter = meter.create_counter(
    "ci.classified.chunks.total",
    unit="1",
    description="Chunks classified by Bloom's level",
)
queue_depth = meter.create_gauge(
    "ci.queue.depth",
    unit="1",
    description="Number of jobs waiting in the Redis queue",
)

JOB_QUEUE = "course-intelligence:jobs"
PROCESSING_QUEUE = "course-intelligence:jobs:processing"
BLOCK_TIMEOUT_S = 5

_LOCAL_DEV_REDIS = "redis://localhost:6379/0"


def _timeout_handler(signum, frame):
    raise JobTimeout("Job exceeded max processing time")


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


def _set_step_progress(job_id: str, progress: dict) -> None:
    session = get_session()
    try:
        job = session.get(Job, job_id)
        if job is None:
            return
        job.step_progress = progress
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
        if job.status in (JobStatus.completed, JobStatus.failed):
            logger.info("Job %s already %s — skipping", job_id, job.status)
            return
        storage_key = job.storage_key
        filename = job.filename
        learning_objectives = job.learning_objectives
    finally:
        session.close()

    _set_status(job_id, JobStatus.processing)
    logger.info("Job %s: processing (%s)", job_id, filename)
    started = time.monotonic()

    with tracer.start_as_current_span(
        "process_job",
        attributes={"job.id": job_id, "job.filename": filename},
    ) as span:
        step_start = started

        def _on_step(node: str) -> None:
            nonlocal step_start
            now = time.monotonic()
            step_duration.record(
                now - step_start, {"step": NODE_TO_STEP.get(node, node)}
            )
            step_start = now
            _set_step(job_id, NODE_TO_STEP.get(node, node))

        def _on_progress(step: str, progress: dict) -> None:
            _set_step_progress(job_id, progress)

        timeout_s = DEFAULT_CONFIG.get("job_timeout_s", 600)
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout_s)
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                local_path = str(Path(tmp_dir) / filename)
                storage.download_file(storage_key, local_path)

                result = graph.process_with_progress(
                    local_path,
                    learning_objectives,
                    on_step=_on_step,
                    on_progress=_on_progress,
                )
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

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
                blooms = chunk.get("blooms_level")
                if blooms:
                    classified_counter.add(1, {"blooms_level": blooms})
            job = session.get(Job, job_id)
            job.status = JobStatus.completed
            # Partial page failures are recorded but don't fail the job
            job.error = error
            session.commit()

            # Capture tenant_id for analytics before session closes
            tenant_id = job.tenant_id or "unknown"
        finally:
            session.close()

        elapsed = time.monotonic() - started
        logger.info(
            "Job %s: completed — %d elements in %.1fs%s",
            job_id, len(knowledge_map), elapsed,
            f" (partial: {error})" if error else "",
        )

        job_duration.record(elapsed)
        jobs_counter.add(1, {"status": "completed"})
        elements_counter.add(len(knowledge_map))

        # --- Analytics events ---
        blooms_counts: dict[str, int] = {}
        for chunk in knowledge_map:
            level = chunk.get("blooms_level", "unclassified")
            blooms_counts[level] = blooms_counts.get(level, 0) + 1

        emit_event("ci.job.completed", {
            "job.id": job_id,
            "job.filename": filename,
            "job.tenant_id": tenant_id,
            "job.elements_count": len(knowledge_map),
            "job.blooms_distribution": blooms_counts,
            "job.processing_time_s": elapsed,
            "job.has_partial_errors": bool(error),
        })
        jobs_completed.add(1, {"tenant_id": tenant_id})
        job_processing_time.record(elapsed, {"tenant_id": tenant_id})
        for level, count in blooms_counts.items():
            elements_produced.add(count, {"blooms_level": level})

    cleanup_old_uploads()


def cleanup_old_uploads() -> None:
    """Delete S3 uploads beyond the retention count.

    Keeps uploads for the N most recent completed+failed jobs.
    Older jobs have their S3 object deleted and the Job row (with its
    Result rows via ON DELETE CASCADE) is deleted from Postgres.
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


def _reap_stale_jobs() -> None:
    """Mark processing jobs as failed if they haven't been updated recently.

    Uses updated_at as a heartbeat: the worker touches updated_at on every
    pipeline step transition.  If a job's updated_at is older than the
    configured threshold, it's considered frozen and marked failed.

    Does NOT touch Redis — the worker's finally:LREM or _reclaim_stale_jobs
    handles Redis cleanup.
    """
    threshold_s = DEFAULT_CONFIG.get("watchdog_stale_threshold_s", 900)
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=threshold_s)
    session = get_session()
    try:
        stale_jobs = (
            session.query(Job)
            .filter(Job.status == JobStatus.processing)
            .filter(Job.updated_at < cutoff)
            .all()
        )
        for job in stale_jobs:
            job.status = JobStatus.failed
            job.error = f"Job timed out (no progress for {threshold_s}s)"
            logger.warning(
                "Watchdog: reaped stale job %s (last updated %s)",
                job.id, job.updated_at,
            )
        if stale_jobs:
            session.commit()
    finally:
        session.close()


def _watchdog_loop() -> None:
    """Background thread that periodically reaps stale jobs."""
    interval = DEFAULT_CONFIG.get("watchdog_interval_s", 60)
    while True:
        time.sleep(interval)
        try:
            _reap_stale_jobs()
        except Exception:
            logger.exception("Watchdog loop error")


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
    setup_otel("course-intelligence-worker")
    instrument_shared()
    redis_client = _get_redis()
    graph = CourseProcessorGraph(config=DEFAULT_CONFIG)
    _reclaim_stale_jobs(redis_client)
    threading.Thread(target=_watchdog_loop, daemon=True).start()
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

            # Report queue depth before processing (gauge is point-in-time)
            try:
                queue_depth.set(redis_client.llen(JOB_QUEUE))
            except Exception:
                pass

            try:
                process_job(job_id, graph)
            except Exception as e:
                logger.error("Job %s: failed — %s", job_id, e, exc_info=True)
                _set_status(job_id, JobStatus.failed, error=str(e))
                jobs_counter.add(1, {"status": "failed"})

                # Look up tenant_id and filename from the DB for correlation
                # with the ci.job.submitted event (success path captures
                # these at worker.py:214/136).
                fail_session = get_session()
                try:
                    failed_job = fail_session.get(Job, job_id)
                    tenant_id = failed_job.tenant_id or "unknown" if failed_job else "unknown"
                    filename = failed_job.filename if failed_job else "unknown"
                finally:
                    fail_session.close()

                jobs_failed.add(1, {"tenant_id": tenant_id, "stage": "processing"})
                emit_event("ci.job.failed", {
                    "job.id": job_id,
                    "job.tenant_id": tenant_id,
                    "job.filename": filename,
                    "error": str(e),
                })
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
