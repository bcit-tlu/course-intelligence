"""Tests for the analytics module — events and metrics."""

from __future__ import annotations

import importlib

import opentelemetry.trace as _trace_mod
import opentelemetry.metrics._internal as _metrics_mod
import opentelemetry._logs._internal as _logs_mod
from opentelemetry import trace, metrics, _logs
from opentelemetry._logs import LogRecord
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider


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


# --- Module-level setup: set SDK providers once (bypassing Once guard) ---

_tracer_provider = TracerProvider()
_log_processor = _CapturingLogProcessor()
_logger_provider = LoggerProvider()
_logger_provider.add_log_record_processor(_log_processor)
_metric_reader = InMemoryMetricReader()
_meter_provider = MeterProvider(metric_readers=[_metric_reader])

# Directly set internal provider variables to bypass the set-once restriction.
# get_tracer()/get_meter()/get_logger() check these first, so no proxy
# notification is needed.
_trace_mod._TRACER_PROVIDER = _tracer_provider
_metrics_mod._METER_PROVIDER = _meter_provider
_logs_mod._LOGGER_PROVIDER = _logger_provider

# Reload analytics so module-level instruments use the SDK meter provider
import course_intelligence.analytics as _analytics
importlib.reload(_analytics)

import pytest


@pytest.fixture(autouse=True)
def _reset_providers():
    """Re-set internal provider vars before each test.

    Other test modules (test_observability.py) may call set_*_provider()
    which overrides our direct assignment. This fixture restores our
    test providers so every test in this module uses the capturing processors.
    """
    _trace_mod._TRACER_PROVIDER = _tracer_provider
    _metrics_mod._METER_PROVIDER = _meter_provider
    _logs_mod._LOGGER_PROVIDER = _logger_provider
    yield


def test_emit_event_creates_log_record_with_event_name():
    """emit_event should emit a LogRecord with the correct event_name field."""
    _log_processor.records.clear()
    _analytics.emit_event("ci.test.event", {"key": "value"})

    assert len(_log_processor.records) == 1
    record = _log_processor.records[0]
    assert record.event_name == "ci.test.event"
    assert record.body == "ci.test.event"
    assert record.attributes == {"key": "value"}


def test_emit_event_includes_trace_context():
    """emit_event should inject trace context from the active span."""
    _log_processor.records.clear()
    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("test-span") as span:
        _analytics.emit_event("ci.test.span_event", {})

        assert len(_log_processor.records) == 1
        record = _log_processor.records[0]
        span_context = span.get_span_context()
        assert record.trace_id == span_context.trace_id
        assert record.span_id == span_context.span_id
        assert record.trace_flags == span_context.trace_flags


def test_emit_event_no_attributes():
    """emit_event should work with no attributes dict."""
    _log_processor.records.clear()
    _analytics.emit_event("ci.test.no_attrs")

    assert len(_log_processor.records) == 1
    record = _log_processor.records[0]
    assert record.event_name == "ci.test.no_attrs"
    assert not record.attributes


def test_metric_counters_are_callable():
    """Counter instruments should accept .add() calls without error."""
    _analytics.jobs_submitted.add(1, {"tenant_id": "t1", "file_type": ".pdf"})
    _analytics.jobs_completed.add(1, {"tenant_id": "t1"})
    _analytics.jobs_failed.add(1, {"tenant_id": "t1", "stage": "processing"})
    _analytics.elements_produced.add(5, {"blooms_level": "remember"})
    _analytics.llm_tokens_by_tenant.add(
        100, {"tenant_id": "t1", "direction": "input"}
    )

    metrics_data = _metric_reader.get_metrics_data()
    assert metrics_data is not None

    found_names = set()
    for rm in metrics_data.resource_metrics:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                found_names.add(metric.name)

    assert "ci.analytics.jobs.submitted.total" in found_names
    assert "ci.analytics.jobs.completed.total" in found_names
    assert "ci.analytics.jobs.failed.total" in found_names
    assert "ci.analytics.elements.produced.total" in found_names
    assert "ci.analytics.llm.tokens.by_tenant.total" in found_names


def test_metric_histograms_are_callable():
    """Histogram instruments should accept .record() calls without error."""
    _analytics.job_processing_time.record(42.5, {"tenant_id": "t1"})
    _analytics.file_size_uploaded.record(1024, {"file_type": ".pdf"})

    metrics_data = _metric_reader.get_metrics_data()
    assert metrics_data is not None

    found_names = set()
    for rm in metrics_data.resource_metrics:
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                found_names.add(metric.name)

    assert "ci.analytics.job.processing_time.seconds" in found_names
    assert "ci.analytics.upload.file_size.bytes" in found_names


def test_metric_names_include_prometheus_suffixes():
    """Metric names should bake in Prometheus suffixes for consistency."""
    assert _analytics.jobs_submitted.name == "ci.analytics.jobs.submitted.total"
    assert _analytics.jobs_completed.name == "ci.analytics.jobs.completed.total"
    assert _analytics.jobs_failed.name == "ci.analytics.jobs.failed.total"
    assert _analytics.elements_produced.name == "ci.analytics.elements.produced.total"
    assert _analytics.llm_tokens_by_tenant.name == "ci.analytics.llm.tokens.by_tenant.total"
    assert _analytics.job_processing_time.name == "ci.analytics.job.processing_time.seconds"
    assert _analytics.file_size_uploaded.name == "ci.analytics.upload.file_size.bytes"
