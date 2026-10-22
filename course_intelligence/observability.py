"""OpenTelemetry setup — called once at startup of each role."""

from __future__ import annotations

import logging
import os

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry._logs import set_logger_provider
from opentelemetry.instrumentation.logging.handler import LoggingHandler


def setup_otel(service_name: str) -> None:
    """Configure OTel SDK for traces, metrics, and logs.

    Reads OTEL_EXPORTER_OTLP_ENDPOINT from the environment (standard OTel
    env var). If not set, telemetry is silently disabled — safe for local dev.
    The service name is taken from OTEL_SERVICE_NAME when set (standard OTel
    env var, wired by the chart), falling back to the provided argument.
    """
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return

    # OTEL_SERVICE_NAME is the standard OTel env var for overriding the
    # service name. The chart sets it per-role (e.g.
    # course-intelligence-backend-api); prefer it over the hardcoded
    # fallback so Loki service_name matches what the chart declares.
    service_name = os.environ.get("OTEL_SERVICE_NAME", service_name)

    # Ensure INFO-level logs are forwarded to the OTel LoggingHandler.
    # The handler uses level=NOTSET (processes whatever the logger passes),
    # but the root logger defaults to WARNING — so without this, INFO logs
    # from the API (uvicorn access logs, logger.info calls) never reach
    # Loki. The worker already calls basicConfig separately; calling it
    # here is idempotent (only the first call takes effect).
    logging.basicConfig(level=logging.INFO)

    resource = Resource.create({
        "service.name": service_name,
        "service.namespace": os.environ.get("OTEL_SERVICE_NAMESPACE", ""),
        "deployment.environment.name": os.environ.get("DEPLOYMENT_ENVIRONMENT", ""),
    })

    # --- Traces ---
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)

    # --- Metrics ---
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
        export_interval_millis=15000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # --- Logs ---
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{endpoint}/v1/logs"))
    )

    # Bridge Python logging → OTel logs so existing logger.info/error calls
    # flow to Loki with trace context (trace_id, span_id).
    handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)


def instrument_shared(engine=None) -> None:
    """Instrument SQLAlchemy and Redis — call from each role's startup.

    Safe to call when OTEL_EXPORTER_OTLP_ENDPOINT is unset: the instrumentors
    are no-ops without a configured provider.
    """
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor

    if engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine)
    else:
        SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
