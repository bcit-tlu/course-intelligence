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
from pydantic import BaseModel, Field, field_validator
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
# Bound the per-event attribute map so a single event can't force expensive
# per-entry validation or emit oversized analytics records. The count is
# checked before pydantic validates individual entries (see the validator
# on TelemetryEvent.attributes) so an oversized payload is rejected (422)
# without iterating it. Key length is capped to keep Loki attribute names
# small and prevent key-based log bloat. Values are truncated separately in
# the handler. Generous vs. current studio usage (≤3 attrs/event, ≤19-char
# keys — see studio/src/analytics/events.ts).
_MAX_ATTRIBUTES_PER_EVENT = 20
_MAX_ATTRIBUTE_KEY_LENGTH = 64

# Bounds on the X-Session-Id header value and the rate-limit bucket map. The
# endpoint is unauthenticated, so a client can send arbitrary (and oversized)
# session IDs; without these caps, each unique ID creates a rate-limit bucket
# until the next sweep, allowing rapid memory growth. Oversized IDs collapse
# to "unknown" (sharing that bucket); when the bucket count hits the cap, new
# sessions collapse into a shared overflow bucket so memory is bounded by
# _MAX_RATE_BUCKETS regardless of cardinality. Generous vs. the studio's
# 36-char crypto.randomUUID() session IDs (see studio/src/analytics/session.ts).
_MAX_SESSION_ID_LENGTH = 128
_MAX_RATE_BUCKETS = 10_000
_OVERFLOW_BUCKET = "__overflow__"

# Provenance fields the server stamps and trusts unconditionally. Applied
# after merging client attributes so untrusted input can never forge or
# overwrite them — e.g. attributing events to another session, posing as
# a backend source, or corrupting trace correlation. Keep in lockstep with
# the attrs dict built in ``ingest_telemetry_events``.
_RESERVED_ATTR_KEYS = frozenset({
    "session.id",
    "event.source",
    "schema.version",
    "trace.parent",
})

# Basic in-memory rate limit: per-session, per window. This is a stopgap
# until CI has authentication and a Redis-backed limiter like HRIV. In a
# multi-pod deployment this should move to Redis so limits are shared.
_RATE_LIMIT_WINDOW_S = 60
_RATE_LIMIT_MAX_REQUESTS = 30  # 30 batched requests per session per minute

_rate_buckets: dict[str, list[float]] = defaultdict(list)
_last_sweep = 0.0


def _check_rate_limit(session_id: str) -> int | None:
    """Return retry-after seconds if rate limited, else None and record the attempt.

    Concurrency invariant: this is a synchronous function with no ``await``
    points. Its single caller (``ingest_telemetry_events``) is an ``async
    def`` endpoint, so this runs to completion on the event loop without
    yielding — the read-filter-update of ``_rate_buckets`` is atomic
    relative to other coroutines on the same loop, and the GIL serializes
    bytecode across any threads. It is therefore safe for the current
    single-process deployment.

    It is **not** safe across OS processes: each uvicorn worker / pod owns
    a separate ``_rate_buckets`` and may over-count (the documented reason
    to move to a Redis-backed limiter — see the module note above). Do not
    add an ``await`` inside this function or call it from a sync endpoint
    (which FastAPI runs on a threadpool) without revisiting this invariant;
    in those cases a lock or an async-safe structure becomes necessary.
    """
    global _last_sweep
    now = time.monotonic()
    window_start = now - _RATE_LIMIT_WINDOW_S

    # Reap buckets whose timestamps have all expired so memory stays
    # bounded by recently-active sessions rather than by every session_id
    # this worker has ever seen. Sweeping at most once per window keeps
    # the amortized per-request cost near zero.
    if now - _last_sweep >= _RATE_LIMIT_WINDOW_S:
        _last_sweep = now
        expired = [sid for sid, ts in _rate_buckets.items()
                   if not any(t > window_start for t in ts)]
        for sid in expired:
            del _rate_buckets[sid]

    # Cap bucket cardinality: when at capacity, collapse new sessions into
    # a shared overflow bucket so a high-cardinality X-Session-Id attack
    # can't grow _rate_buckets beyond _MAX_RATE_BUCKETS between sweeps.
    # Existing sessions keep their own buckets; only new ones overflow. The
    # real session_id is still stamped in emitted event attributes — only the
    # rate-limit key is remapped, so legitimate sessions caught in overflow
    # remain attributable in Loki.
    if session_id not in _rate_buckets and len(_rate_buckets) >= _MAX_RATE_BUCKETS:
        session_id = _OVERFLOW_BUCKET

    bucket = [t for t in _rate_buckets.pop(session_id, []) if t > window_start]
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
    attributes: dict[str, str | int | float | bool] | None = Field(
        None, max_length=_MAX_ATTRIBUTES_PER_EVENT
    )

    @field_validator("attributes", mode="before")
    @classmethod
    def _bound_attributes(cls, v):
        """Reject oversized payloads before pydantic validates each entry.

        Checking count first (O(1)) avoids iterating a large dict just to
        reject it; key lengths are only checked once the count is already
        within bounds. Raises -> 422, consistent with the batch-size limit.
        Non-dict values (e.g. a number or list sent where attributes is
        expected) are returned unchanged so pydantic's built-in type
        validation produces the 422 — without this guard, ``len()`` / key
        iteration would raise ``TypeError``, which pydantic does not wrap
        into a ``ValidationError``, leaking a 500 to the client.
        """
        if v is None or not isinstance(v, dict):
            return v
        if len(v) > _MAX_ATTRIBUTES_PER_EVENT:
            raise ValueError(
                f"at most {_MAX_ATTRIBUTES_PER_EVENT} attributes per event"
            )
        for key in v:
            if len(key) > _MAX_ATTRIBUTE_KEY_LENGTH:
                raise ValueError(
                    f"attribute key exceeds {_MAX_ATTRIBUTE_KEY_LENGTH} chars"
                )
        return v


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
    if len(session_id) > _MAX_SESSION_ID_LENGTH:
        session_id = "unknown"

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

        # Build attributes in trust order: untrusted client payload first,
        # then typed/validated envelope fields, then server-owned provenance
        # last so it always wins over any colliding client-supplied value
        # (see _RESERVED_ATTR_KEYS).
        attrs: dict[str, object] = {}

        # Untrusted client attributes, with per-value bounds. Reserved
        # provenance keys are skipped here and stamped by the server below.
        if event.attributes:
            for key, value in event.attributes.items():
                if key in _RESERVED_ATTR_KEYS:
                    continue
                if isinstance(value, str) and len(value) > _MAX_ATTRIBUTE_LENGTH:
                    value = value[:_MAX_ATTRIBUTE_LENGTH]
                attrs[key] = value

        if event.outcome is not None:
            attrs["event.outcome"] = event.outcome
        if event.duration_ms is not None:
            attrs["event.duration_ms"] = event.duration_ms
        if event.error is not None:
            attrs["error.message"] = event.error
        if event.page is not None:
            attrs["event.page"] = event.page

        # Server-owned provenance — stamped last, always wins.
        attrs["session.id"] = session_id
        attrs["event.source"] = "studio"
        attrs["schema.version"] = event.schema_version or TELEMETRY_SCHEMA_VERSION
        if traceparent:
            attrs["trace.parent"] = traceparent

        emit_event(event.event, attrs)

    return Response(status_code=status.HTTP_202_ACCEPTED)
