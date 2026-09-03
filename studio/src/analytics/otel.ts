import { trace } from "@opentelemetry/api";
import { WebTracerProvider } from "@opentelemetry/sdk-trace-web";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { ZoneContextManager } from "@opentelemetry/context-zone";
import { DocumentLoadInstrumentation } from "@opentelemetry/instrumentation-document-load";
import { FetchInstrumentation } from "@opentelemetry/instrumentation-fetch";
import { UserInteractionInstrumentation } from "@opentelemetry/instrumentation-user-interaction";
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { Resource } from "@opentelemetry/resources";

// Runtime config: the OTel endpoint is injected by nginx as a global
// variable (window.__OTEL_ENDPOINT__) so it can change without an image
// rebuild. In dev, fall back to the Vite env var if set.
const endpoint =
  (typeof window !== "undefined" && (window as any).__OTEL_ENDPOINT__) ||
  import.meta.env.VITE_OTEL_EXPORTER_OTLP_ENDPOINT;

let analyticsEnabled = false;

export function initAnalytics() {
  if (!endpoint) return;

  const provider = new WebTracerProvider({
    resource: new Resource({
      "service.name": "course-intelligence-studio",
      "service.namespace": "course-intelligence",
    }),
  });

  provider.addSpanProcessor(
    new BatchSpanProcessor(
      new OTLPTraceExporter({ url: `${endpoint}/v1/traces` }),
    ),
  );

  // Register as the global provider so registerInstrumentations()
  // and trace.getTracer() use it. ZoneContextManager enables context
  // propagation across async boundaries (fetch, event handlers, promises).
  provider.register({
    contextManager: new ZoneContextManager(),
  });

  registerInstrumentations({
    instrumentations: [
      new DocumentLoadInstrumentation(),
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: ["/api"],
      }),
      new UserInteractionInstrumentation({
        eventNames: ["click", "submit"],
      }),
    ],
  });

  // Global error handlers — create error spans for uncaught exceptions
  // and unhandled promise rejections so they show up in traces.
  const tracer = trace.getTracer("course-intelligence.studio.errors");
  const errorHandler = (event: ErrorEvent) => {
    const span = tracer.startSpan("window.onerror", {
      attributes: {
        "error.message": event.message,
        "error.filename": event.filename,
        "error.lineno": event.lineno,
      },
    });
    span.recordException({
      name: event.error?.name || "Error",
      message: event.message,
      stack: event.error?.stack,
    });
    span.end();
  };
  const rejectionHandler = (event: PromiseRejectionEvent) => {
    const span = tracer.startSpan("unhandledrejection", {
      attributes: {
        "error.reason": String(event.reason),
      },
    });
    span.recordException(event.reason);
    span.end();
  };
  window.addEventListener("error", errorHandler);
  window.addEventListener("unhandledrejection", rejectionHandler);

  analyticsEnabled = true;
}

export function isAnalyticsEnabled() {
  return analyticsEnabled;
}
