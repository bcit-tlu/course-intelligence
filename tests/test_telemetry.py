"""Tests for the frontend telemetry relay endpoint.

Validates that the ``POST /telemetry/events`` endpoint:
- Accepts batched events and re-emits them as structured log records.
- Drops events with unknown names silently.
- Propagates ``session.id`` from the ``X-Session-Id`` header.
- Enforces per-session rate limiting.
- Propagates ``traceparent`` for trace correlation.
"""

from __future__ import annotations

import time

import opentelemetry.trace as _trace_mod
import opentelemetry._logs._internal as _logs_mod
from opentelemetry._logs import LogRecord
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.trace import TracerProvider
from fastapi.testclient import TestClient

import pytest


class _CapturingLogProcessor:
    """Captures LogRecords for assertion in tests."""

    def __init__(self):
        self.records: list[LogRecord] = []

    def on_emit(self, log_record) -> None:
        self.records.append(log_record.log_record)

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True


# --- Module-level OTel setup: set the logger provider once ---

_tracer_provider = TracerProvider()
_log_processor = _CapturingLogProcessor()
_logger_provider = LoggerProvider()
_logger_provider.add_log_record_processor(_log_processor)

# Set the tracer provider (the API app instruments FastAPI at import).
# Do NOT set the meter provider — test_analytics.py owns that and
# reloading analytics here would rebind its module-level meter to our
# provider, breaking its metric-reader assertions.
_trace_mod._TRACER_PROVIDER = _tracer_provider
_logs_mod._LOGGER_PROVIDER = _logger_provider

import course_intelligence.telemetry as _telemetry  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_providers():
    """Restore the test logger provider before each test and clear records."""
    _logs_mod._LOGGER_PROVIDER = _logger_provider
    _log_processor.records.clear()
    yield


@pytest.fixture()
def client(monkeypatch):
    """Yield a TestClient for the API app with in-memory fakes.

    The telemetry endpoint touches neither the DB, storage, nor Redis, but
    the API app's startup hooks instrument shared resources. We monkeypatch
    the bits that require external services so the app constructs cleanly.
    """
    from course_intelligence import api

    # The API constructs a DB engine at import time via get_engine(). In
    # tests that only hit /telemetry/events this is never used, but
    # instrument_shared(engine=...) is called at module scope. Patch it
    # to a no-op so we don't need a real database.
    monkeypatch.setattr(api, "instrument_shared", lambda engine=None: None)

    # Reset rate-limit buckets between tests so limits don't leak.
    monkeypatch.setattr(_telemetry, "_rate_buckets",
                        _telemetry.defaultdict(list))

    test_client = TestClient(api.app)
    yield test_client


def _post(client, events, session_id="test-session"):
    headers = {"X-Session-Id": session_id}
    return client.post("/telemetry/events",
                       json={"events": events}, headers=headers)


# --- Acceptance ---


def test_accepts_valid_event_and_emits_log_record(client):
    """A known event name is accepted (202) and re-emitted via emit_event."""
    resp = _post(client, [{
        "event": "studio.upload.started",
        "attributes": {"file.name": "module.pdf", "file.size": 1024},
    }])
    assert resp.status_code == 202

    assert len(_log_processor.records) == 1
    record = _log_processor.records[0]
    assert record.event_name == "studio.upload.started"
    assert record.attributes["session.id"] == "test-session"
    assert record.attributes["event.source"] == "studio"
    assert record.attributes["file.name"] == "module.pdf"
    assert record.attributes["file.size"] == 1024


def test_drops_unknown_event_names_silently(client):
    """Events not in the allowlist are dropped without error."""
    resp = _post(client, [
        {"event": "studio.upload.started"},
        {"event": "evil.injection"},
        {"event": "studio.docs.viewed"},
    ])
    assert resp.status_code == 202
    assert len(_log_processor.records) == 2
    names = {r.event_name for r in _log_processor.records}
    assert names == {"studio.upload.started", "studio.docs.viewed"}


def test_session_id_from_header(client):
    """session.id in the log record matches the X-Session-Id header."""
    _post(client, [{"event": "studio.docs.viewed"}], session_id="abc-123")
    assert _log_processor.records[0].attributes["session.id"] == "abc-123"


def test_session_id_defaults_to_unknown_when_header_missing(client):
    """Without X-Session-Id, session.id falls back to 'unknown'."""
    resp = client.post("/telemetry/events",
                       json={"events": [{"event": "studio.docs.viewed"}]})
    assert resp.status_code == 202
    assert _log_processor.records[0].attributes["session.id"] == "unknown"


def test_propagates_traceparent(client):
    """traceparent header is recorded for trace correlation."""
    resp = client.post(
        "/telemetry/events",
        json={"events": [{"event": "studio.docs.viewed"}]},
        headers={"X-Session-Id": "s1", "traceparent": "00-abc-def-01"},
    )
    assert resp.status_code == 202
    assert _log_processor.records[0].attributes["trace.parent"] == "00-abc-def-01"


def test_rejects_oversized_batch(client):
    """Batches exceeding _MAX_EVENTS_PER_REQUEST are rejected (422)."""
    events = [{"event": "studio.docs.viewed"} for _ in range(11)]
    resp = _post(client, events)
    assert resp.status_code == 422


def test_rejects_too_many_attributes_per_event(client):
    """Events with more than _MAX_ATTRIBUTES_PER_REQUEST attributes are
    rejected (422) before the handler iterates them."""
    too_many = {f"k{i}": i for i in range(_telemetry._MAX_ATTRIBUTES_PER_EVENT + 1)}
    resp = _post(client, [{
        "event": "studio.docs.viewed",
        "attributes": too_many,
    }])
    assert resp.status_code == 422
    assert len(_log_processor.records) == 0


def test_rejects_oversized_attribute_key(client):
    """Attribute keys exceeding _MAX_ATTRIBUTE_KEY_LENGTH are rejected (422)."""
    long_key = "x" * (_telemetry._MAX_ATTRIBUTE_KEY_LENGTH + 1)
    resp = _post(client, [{
        "event": "studio.docs.viewed",
        "attributes": {long_key: "v"},
    }])
    assert resp.status_code == 422
    assert len(_log_processor.records) == 0


def test_max_attributes_boundary_is_accepted(client):
    """Exactly _MAX_ATTRIBUTES_PER_EVENT attributes are accepted (not off-by-one)."""
    attrs = {f"k{i}": i for i in range(_telemetry._MAX_ATTRIBUTES_PER_EVENT)}
    resp = _post(client, [{
        "event": "studio.docs.viewed",
        "attributes": attrs,
    }])
    assert resp.status_code == 202
    assert len(_log_processor.records) == 1


def test_enforces_rate_limit(client):
    """Per-session rate limiting returns 429 after the limit is exceeded."""
    # _RATE_LIMIT_MAX_REQUESTS = 30; send 30 then expect 429 on the 31st.
    for _ in range(30):
        resp = _post(client, [{"event": "studio.docs.viewed"}])
        assert resp.status_code == 202
    resp = _post(client, [{"event": "studio.docs.viewed"}])
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_rate_limit_is_per_session(client):
    """One session hitting the limit does not block a different session."""
    for _ in range(30):
        _post(client, [{"event": "studio.docs.viewed"}], session_id="sess-a")
    # sess-a is now rate-limited
    assert _post(client, [{"event": "studio.docs.viewed"}],
                 session_id="sess-a").status_code == 429
    # sess-b is unaffected
    assert _post(client, [{"event": "studio.docs.viewed"}],
                 session_id="sess-b").status_code == 202


def test_reaps_expired_buckets(client, monkeypatch):
    """Buckets with only expired timestamps are dropped to bound memory.

    A session that was active long ago and never returns would otherwise
    leave an entry in _rate_buckets forever; the periodic sweep removes it.
    """
    stale = "stale-session"
    stale_time = time.monotonic() - 2 * _telemetry._RATE_LIMIT_WINDOW_S
    _telemetry._rate_buckets[stale] = [stale_time]
    # Force the next request to sweep (last sweep predates the window).
    monkeypatch.setattr(_telemetry, "_last_sweep", stale_time)

    _post(client, [{"event": "studio.docs.viewed"}], session_id="active")

    assert stale not in _telemetry._rate_buckets
    assert "active" in _telemetry._rate_buckets


def test_oversized_session_id_collapses_to_unknown(client):
    """Session IDs exceeding _MAX_SESSION_ID_LENGTH fall back to "unknown".

    Without this bound, a client could send oversized X-Session-Id headers
    (up to the HTTP limit) so each bucket key bloats worker memory.
    """
    long_id = "x" * (_telemetry._MAX_SESSION_ID_LENGTH + 1)
    _post(client, [{"event": "studio.docs.viewed"}], session_id=long_id)
    assert len(_log_processor.records) == 1
    assert _log_processor.records[0].attributes["session.id"] == "unknown"


def test_session_id_at_boundary_is_accepted(client):
    """Exactly _MAX_SESSION_ID_LENGTH chars is accepted (not off-by-one)."""
    boundary_id = "y" * _telemetry._MAX_SESSION_ID_LENGTH
    _post(client, [{"event": "studio.docs.viewed"}], session_id=boundary_id)
    assert len(_log_processor.records) == 1
    assert _log_processor.records[0].attributes["session.id"] == boundary_id


def test_bucket_cap_collapses_new_sessions_to_overflow(client, monkeypatch):
    """When _rate_buckets is at capacity, new sessions share the overflow
    bucket so memory is bounded regardless of session-ID cardinality.

    Existing sessions keep their own buckets; only new ones collapse. The
    overflow bucket has the same per-session limit, so sessions sharing it
    are collectively rate-limited.
    """
    monkeypatch.setattr(_telemetry, "_MAX_RATE_BUCKETS", 1)
    # sess-a fills the single allowed bucket.
    _post(client, [{"event": "studio.docs.viewed"}], session_id="sess-a")
    assert len(_telemetry._rate_buckets) == 1

    # sess-b is new and at capacity -> collapses into the overflow bucket.
    # Exhaust the overflow bucket's limit (30 requests).
    for _ in range(30):
        assert _post(client, [{"event": "studio.docs.viewed"}],
                     session_id="sess-b").status_code == 202

    # sess-c is also new and at capacity -> same overflow bucket -> 429.
    assert _post(client, [{"event": "studio.docs.viewed"}],
                 session_id="sess-c").status_code == 429

    # Memory stayed bounded: only sess-a + the overflow bucket exist.
    assert len(_telemetry._rate_buckets) == 2
    assert "sess-a" in _telemetry._rate_buckets
    assert _telemetry._OVERFLOW_BUCKET in _telemetry._rate_buckets


def test_existing_session_keeps_own_bucket_at_capacity(client, monkeypatch):
    """An existing session is not displaced when the cap is hit."""
    monkeypatch.setattr(_telemetry, "_MAX_RATE_BUCKETS", 1)
    # sess-a fills the cap.
    _post(client, [{"event": "studio.docs.viewed"}], session_id="sess-a")
    # sess-b overflows.
    _post(client, [{"event": "studio.docs.viewed"}], session_id="sess-b")
    # sess-a still has its own bucket and is not rate-limited by sess-b.
    assert "sess-a" in _telemetry._rate_buckets
    assert _telemetry._rate_buckets["sess-a"] is not _telemetry._rate_buckets.get(
        _telemetry._OVERFLOW_BUCKET)


def test_optional_fields_are_emitted(client):
    """Optional envelope fields (outcome, duration_ms, error, page) are passed through."""
    _post(client, [{
        "event": "studio.upload.failed",
        "outcome": "failure",
        "duration_ms": 250.0,
        "error": "Network error",
        "page": "upload",
    }])
    record = _log_processor.records[0]
    assert record.attributes["event.outcome"] == "failure"
    assert record.attributes["event.duration_ms"] == 250.0
    assert record.attributes["error.message"] == "Network error"
    assert record.attributes["event.page"] == "upload"


def test_long_attribute_values_are_truncated(client):
    """String attribute values exceeding the limit are truncated."""
    long_value = "x" * 2000
    _post(client, [{
        "event": "studio.upload.started",
        "attributes": {"file.name": long_value},
    }])
    record = _log_processor.records[0]
    assert len(record.attributes["file.name"]) == 1000


def test_client_cannot_forge_provenance(client):
    """Reserved provenance fields in client attributes are dropped; server
    values always win.

    Without this guard, a client could inject records attributed to another
    session, pose as a backend source, forge a schema version, or corrupt
    trace correlation.
    """
    resp = client.post(
        "/telemetry/events",
        json={"events": [{
            "event": "studio.docs.viewed",
            "attributes": {
                "session.id": "victim-session",
                "event.source": "backend",
                "schema.version": 999,
                "trace.parent": "00-forged-forged-01",
                "file.name": "legit.pdf",
            },
        }]},
        headers={"X-Session-Id": "real-session"},
    )
    assert resp.status_code == 202
    assert len(_log_processor.records) == 1
    attrs = _log_processor.records[0].attributes
    # Server-stamped provenance wins over forged client values.
    assert attrs["session.id"] == "real-session"
    assert attrs["event.source"] == "studio"
    assert attrs["schema.version"] == _telemetry.TELEMETRY_SCHEMA_VERSION
    # No traceparent header on the request -> no trace.parent at all (not
    # the client's forged value).
    assert "trace.parent" not in attrs
    # Non-reserved client attributes still pass through.
    assert attrs["file.name"] == "legit.pdf"


def test_traceparent_header_wins_over_client_attribute(client):
    """When the request carries a traceparent header, the server-stamped
    value wins over any client-supplied trace.parent attribute."""
    resp = client.post(
        "/telemetry/events",
        json={"events": [{
            "event": "studio.docs.viewed",
            "attributes": {"trace.parent": "00-forged-forged-01"},
        }]},
        headers={"X-Session-Id": "s1", "traceparent": "00-real-real-01"},
    )
    assert resp.status_code == 202
    attrs = _log_processor.records[0].attributes
    assert attrs["trace.parent"] == "00-real-real-01"


def test_schema_version_defaults_to_current(client):
    """Omitted schema_version defaults to TELEMETRY_SCHEMA_VERSION."""
    _post(client, [{"event": "studio.docs.viewed"}])
    record = _log_processor.records[0]
    assert record.attributes["schema.version"] == _telemetry.TELEMETRY_SCHEMA_VERSION
