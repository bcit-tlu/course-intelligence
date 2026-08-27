"""User analytics — events and metrics for product insights.

Emits structured log records (via the OTel Logs API) with an ``event.name``
attribute for queryability in Loki, plus low-cardinality counters and
histograms for Prometheus. Trace context (trace_id, span_id) is injected
from the current span automatically.

When OTel is not configured (no OTEL_EXPORTER_OTLP_ENDPOINT), the SDK
returns no-op instruments and loggers — all calls are silently dropped.
"""

from __future__ import annotations

import time

from opentelemetry import metrics
from opentelemetry._logs import SeverityNumber, get_logger
from opentelemetry.sdk._logs import LogRecord
from opentelemetry.trace import get_current_span

_meter = metrics.get_meter("course-intelligence.analytics")

# --- Metrics (low-cardinality, aggregated) ---

jobs_submitted = _meter.create_counter(
    "ci.analytics.jobs.submitted",
    unit="1",
    description="Jobs submitted by users",
)
jobs_completed = _meter.create_counter(
    "ci.analytics.jobs.completed",
    unit="1",
    description="Jobs completed successfully",
)
jobs_failed = _meter.create_counter(
    "ci.analytics.jobs.failed",
    unit="1",
    description="Jobs that failed processing",
)
elements_produced = _meter.create_counter(
    "ci.analytics.elements.produced",
    unit="1",
    description="Learning elements produced, by Bloom's level",
)
llm_tokens_by_tenant = _meter.create_counter(
    "ci.analytics.llm.tokens.by_tenant",
    unit="1",
    description="LLM tokens consumed per tenant",
)
job_processing_time = _meter.create_histogram(
    "ci.analytics.job.processing_time",
    unit="s",
    description="User-facing job processing time (wall clock)",
)
file_size_uploaded = _meter.create_histogram(
    "ci.analytics.upload.file_size",
    unit="By",
    description="Size of uploaded files",
)


def emit_event(name: str, attributes: dict | None = None) -> None:
    """Emit a structured analytics event with trace context.

    The event is emitted as a standard OTel log record (via the Logs API)
    with an ``event.name`` attribute for queryability in Loki. Trace context
    (trace_id, span_id, trace_flags) is injected from the current span.
    """
    logger = get_logger(__name__)
    span = get_current_span()
    span_context = span.get_span_context() if span else None
    has_valid_context = span_context is not None and span_context.is_valid

    logger.emit(LogRecord(
        timestamp=time.time_ns(),
        trace_id=span_context.trace_id if has_valid_context else None,
        span_id=span_context.span_id if has_valid_context else None,
        trace_flags=span_context.trace_flags if has_valid_context else None,
        severity_number=SeverityNumber.INFO,
        body=name,
        attributes={**(attributes or {}), "event.name": name},
    ))
