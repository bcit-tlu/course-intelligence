"""Tests for the OpenTelemetry setup module."""

from __future__ import annotations

import logging

from opentelemetry import trace, metrics


def test_setup_otel_noop_without_endpoint(monkeypatch):
    """setup_otel should be a no-op when OTEL_EXPORTER_OTLP_ENDPOINT is unset."""
    from course_intelligence.observability import setup_otel

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    # Capture the provider state before calling setup_otel
    tracer_before = trace.get_tracer_provider()
    meter_before = metrics.get_meter_provider()

    setup_otel("test-service")

    # Providers should be unchanged — no SDK providers were set
    assert trace.get_tracer_provider() is tracer_before
    assert metrics.get_meter_provider() is meter_before


def test_setup_otel_noop_with_empty_endpoint(monkeypatch):
    """setup_otel should be a no-op when the endpoint is an empty string."""
    from course_intelligence.observability import setup_otel

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

    tracer_before = trace.get_tracer_provider()
    meter_before = metrics.get_meter_provider()

    setup_otel("test-service")

    assert trace.get_tracer_provider() is tracer_before
    assert metrics.get_meter_provider() is meter_before


def test_setup_otel_configures_providers_with_endpoint(monkeypatch):
    """setup_otel should configure SDK providers when the endpoint is set."""
    from course_intelligence.observability import setup_otel
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.metrics import MeterProvider

    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

    original_tracer = trace.get_tracer_provider()
    original_meter = metrics.get_meter_provider()

    try:
        setup_otel("test-service")

        assert isinstance(trace.get_tracer_provider(), TracerProvider)
        assert isinstance(metrics.get_meter_provider(), MeterProvider)
    finally:
        # Restore the default providers so other tests are not affected
        trace.set_tracer_provider(original_tracer)
        metrics.set_meter_provider(original_meter)
        # Remove the logging handler that setup_otel added to the root logger
        root = logging.getLogger()
        root.handlers = [
            h for h in root.handlers
            if type(h).__name__ != "LoggingHandler"
        ]
