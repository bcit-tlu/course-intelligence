import { isAnalyticsEnabled } from "./otel";
import { getSessionId, safeGetItem, safeSetItem } from "./session";
import { postTelemetryEvents, type TelemetryPayload } from "@/api/client";

// Batch + flush configuration. Events accumulate for up to FLUSH_INTERVAL_MS
// or until the batch reaches MAX_EVENTS_PER_REQUEST, then are POSTed to the
// backend relay endpoint (/api/telemetry/events) which re-emits them as
// structured OTel log records for Loki. Mirrors the HRIV pattern.
const FLUSH_INTERVAL_MS = 2000;
const MAX_EVENTS_PER_REQUEST = 10;

let _pendingEvents: TelemetryPayload[] = [];
let _flushTimer: ReturnType<typeof setTimeout> | null = null;

function queueFlush(): void {
  if (_flushTimer !== null) return;
  _flushTimer = setTimeout(() => {
    _flushTimer = null;
    flushPendingEvents();
  }, FLUSH_INTERVAL_MS);
}

function flushPendingEvents(): void {
  if (_flushTimer !== null) {
    clearTimeout(_flushTimer);
    _flushTimer = null;
  }
  if (_pendingEvents.length === 0) return;
  const events = _pendingEvents.splice(0, _pendingEvents.length);
  postTelemetryEvents(events);
}

// Flush on page unload so pending events are not lost. keepalive: true on
// the fetch keeps the request alive after the page navigates away.
if (typeof window !== "undefined") {
  window.addEventListener("beforeunload", flushPendingEvents);
}

/**
 * Queue a product-analytics event for delivery to the backend relay.
 * The event is batched with other pending events and flushed on a timer
 * or when the batch is full.
 */
export function trackAction(
  name: string,
  attributes?: Record<string, string | number | boolean>,
) {
  if (!isAnalyticsEnabled()) return;
  _pendingEvents.push({ event: name, attributes });
  if (_pendingEvents.length >= MAX_EVENTS_PER_REQUEST) {
    flushPendingEvents();
  } else {
    queueFlush();
  }
}

// Records the session ID a studio.session.started event has already been
// emitted for. sessionStorage survives reloads (which reuse the tab's
// session ID) so the event fires once per tab, not once per reload. Tied
// to the session ID so a regenerated ID can still start a new session.
// Uses the safe accessors so a blocked-storage browser still renders.
const SESSION_STARTED_KEY = "ci.session.started";

/**
 * Emit a session-started event once per tab session. Call from App init
 * so the first page load is counted as an active session in dashboards.
 */
export function trackSessionStarted(): void {
  if (!isAnalyticsEnabled()) return;
  const sessionId = getSessionId();
  if (!sessionId) return;
  if (safeGetItem(SESSION_STARTED_KEY) === sessionId) return;
  trackAction("studio.session.started");
  safeSetItem(SESSION_STARTED_KEY, sessionId);
}

// Predefined event helpers
export const analytics = {
  uploadStarted: (filename: string, fileType: string, fileSize: number) =>
    trackAction("studio.upload.started", {
      "file.name": filename,
      "file.type": fileType,
      "file.size": fileSize,
    }),

  uploadCompleted: (jobId: string) =>
    trackAction("studio.upload.completed", { "job.id": jobId }),

  uploadFailed: (error: string) =>
    trackAction("studio.upload.failed", { "error.message": error }),

  jobViewed: (jobId: string, status: string) =>
    trackAction("studio.job.viewed", { "job.id": jobId, "job.status": status }),

  resultsViewed: (jobId: string, elementCount: number) =>
    trackAction("studio.results.viewed", {
      "job.id": jobId,
      "results.count": elementCount,
    }),

  bloomsFilterApplied: (level: string) =>
    trackAction("studio.results.filter_blooms", { "blooms.level": level }),

  resultsSearched: (query: string) =>
    trackAction("studio.results.searched", {
      "search.query_length": query.length,
    }),

  docsViewed: () =>
    trackAction("studio.docs.viewed"),

  jobsListed: (count: number) =>
    trackAction("studio.jobs.listed", { "jobs.count": count }),
};
