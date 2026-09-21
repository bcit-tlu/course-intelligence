"""Frontend telemetry relay endpoint.

Accepts batched product-analytics events from the studio frontend and
re-emits them as structured OTel log records via ``emit_event`` so they
flow to Loki through the same analytics pipeline as backend ``ci.*``
events. Mirrors the HRIV pattern (``backend/app/routers/telemetry.py``)
but without authentication — CI has no auth yet (see ``tasks.md`` Phase 2).
A basic in-memory rate limit and event-name allowlist limit abuse until
auth lands.

Design notes:

- Events are **versioned** (``schema_version``) so dashboards and log
  parsers can evolve without silently misreading older records.
- Domain identifiers (job id, filename) are emitted as **structured event
  fields**, never as Prometheus labels, to keep cardinality out of metrics.
- The event-name allowlist is the single chokepoint for what the browser
  may inject into the analytics stream; unknown names are dropped silently.
- ``session.id`` is stamped from the ``X-Session-Id`` header so frontend
  and backend events join on the same field in Loki (sanitized to
  ``session_id`` by the OTLP-to-Loki exporter).
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from course_intelligence.analytics import emit_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

# Bump when the wire/log shape changes in a backward-incompatible way.
TELEMETRY_SCHEMA_VERSION = 1

# Event names the studio is allowed to emit. Keep this small and review
# any new event for privacy/PII implications before adding it. Keep in
# lockstep with ``studio/src/analytics/events.ts``.
_ALLOWED_EVENTS = frozenset({
    "studio.upload.started",
    "studio.upload.completed",
    "studio.upload.failed",
    "studio.job.viewed",
    "studio.results.viewed",
    "studio.results.filter_blooms",
    "studio.results.searched",
    "studio.docs.viewed",
    "studio.jobs.listed",
    "studio.session.started",
})

# Hard limits to prevent accidental or malicious payload abuse. These are
# per-request guards; per-session rate limiting is enforced separately below.
# Keep in sync with ``studio/src/analytics/events.ts`` MAX_EVENTS_PER_REQUEST
# or larger client batches will be rejected wholesale with a 422.
_MAX_EVENTS_PER_REQUEST = 10
_MAX_ATTRIBUTE_LENGTH = 1000

# Basic in-memory rate limit: per-session, per window. This is a stopgap
# until CI has authentication and a Redis-backed limiter like HRIV. In a
# multi-pod deployment this should move to Redis so limits are shared.
_RATE_LIMIT_WINDOW_S = 60
_RATE_LIMIT_MAX_REQUESTS = 30  # 30 batched requests per session per minute

_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(session_id: str) -> int | None:
    """Return retry-after seconds if rate limited, else None and record the attempt."""
    now = time.monotonic()
    window_start = now - _RATE_LIMIT_WINDOW_S
    bucket = [t for t in _rate_buckets[session_id] if t > window_start]
    if len(bucket) >= _RATE_LIMIT_MAX_REQUESTS:
        _rate_buckets[session_id] = bucket
        return _RATE_LIMIT_WINDOW_S
    bucket.append(now)
    _rate_buckets[session_id] = bucket
    return None


class TelemetryEvent(BaseModel):
    """A single frontend telemetry event."""
    model_config = ConfigDict(extra="ignore")

    event: str = Field(..., max_length=100, description="Stable, dotted event name")
    schema_version: int | None = None
    event_version: int | None = None
    outcome: Literal["success", "failure", "unknown"] | None = None
    duration_ms: float | None = None
    error: str | None = Field(None, max_length=_MAX_ATTRIBUTE_LENGTH)
    page: str | None = Field(None, max_length=64)
    # Structured domain fields the studio wants in Loki for drill-down.
    # Values are bounded per entry to prevent log injection / bloat.
    attributes: dict[str, str | int | float | bool] | None = None


class TelemetryBatch(BaseModel):
    """Batch of frontend telemetry events."""
    model_config = ConfigDict(extra="ignore")
    events: list[TelemetryEvent] = Field(..., max_length=_MAX_EVENTS_PER_REQUEST)


@router.post("/events", status_code=202)
async def ingest_telemetry_events(
    batch: TelemetryBatch,
    request: Request,
    x_session_id: str | None = Header(default=None, alias="X-Session-Id"),
) -> Response:
    """Accept a batch of validated frontend telemetry events.

    Events are re-emitted via ``emit_event`` so they flow to Loki through
    the same analytics pipeline as backend events. Unknown event names are
    dropped silently to keep the endpoint fast and resilient. Per-session
    rate limiting protects the log pipeline from a misbehaving client.
    """
    session_id = x_session_id or "unknown"

    retry_after = _check_rate_limit(session_id)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Telemetry rate limit exceeded.",
            headers={"Retry-After": str(retry_after)},
        )

    # Propagate any trace context from the incoming request so frontend
    # fetch spans and backend logs stay correlated.
    traceparent = request.headers.get("traceparent")

    for event in batch.events:
        if event.event not in _ALLOWED_EVENTS:
            continue

        attrs: dict[str, object] = {
            "session.id": session_id,
            "event.source": "studio",
            "schema.version": event.schema_version or TELEMETRY_SCHEMA_VERSION,
        }
        if event.outcome is not None:
            attrs["event.outcome"] = event.outcome
        if event.duration_ms is not None:
            attrs["event.duration_ms"] = event.duration_ms
        if event.error is not None:
            attrs["error.message"] = event.error
        if event.page is not None:
            attrs["event.page"] = event.page
        if traceparent:
            attrs["trace.parent"] = traceparent
        if event.attributes:
            for key, value in event.attributes.items():
                if isinstance(value, str) and len(value) > _MAX_ATTRIBUTE_LENGTH:
                    value = value[:_MAX_ATTRIBUTE_LENGTH]
                attrs[key] = value

        emit_event(event.event, attrs)

    return Response(status_code=status.HTTP_202_ACCEPTED)
