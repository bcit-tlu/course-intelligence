import { trace } from "@opentelemetry/api";
import { isAnalyticsEnabled } from "./otel";

const tracer = trace.getTracer("course-intelligence.studio.analytics");

export function trackAction(
  name: string,
  attributes?: Record<string, string | number | boolean>,
) {
  if (!isAnalyticsEnabled()) return;
  const span = tracer.startSpan(name, { attributes });
  span.end();
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
    trackAction("studio.upload.failed", { "error": error }),

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
