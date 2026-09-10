// Typed fetch wrappers around the job API. All calls go through the
// `/api` prefix, which the Vite dev server proxies to the backend
// (and nginx proxies in the containerized build).

import type { CreateJobResponse, Job, JobResults } from "@/types";
import { getSessionId } from "@/analytics/session";

const BASE = "/api";

// Tenant ID is injected at runtime via /runtime-config.js (nginx envsubst).
// In dev, fall back to the Vite env var if set.
const tenantId =
  (typeof window !== "undefined" && (window as any).__TENANT_ID__) ||
  import.meta.env.VITE_TENANT_ID;

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (tenantId) headers["X-Tenant-Id"] = tenantId;
  const sessionId = getSessionId();
  if (sessionId) headers["X-Session-Id"] = sessionId;
  return headers;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function parseError(res: Response): Promise<never> {
  let detail = res.statusText;
  try {
    const body = await res.json();
    if (body?.detail) detail = body.detail;
  } catch {
    // non-JSON error body — keep statusText
  }
  throw new ApiError(res.status, detail);
}

export async function createJob(
  file: File,
  learningObjectives: string,
  onProgress?: (fraction: number) => void,
): Promise<CreateJobResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("learning_objectives", learningObjectives);

  // Use XHR (not fetch) so we can report upload progress for large zips.
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/jobs`);

    const headers = authHeaders();
    for (const [key, value] of Object.entries(headers)) {
      xhr.setRequestHeader(key, value);
    }

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total);
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        let detail = xhr.statusText;
        try {
          detail = JSON.parse(xhr.responseText).detail ?? detail;
        } catch {
          // keep statusText
        }
        reject(new ApiError(xhr.status, detail));
      }
    };
    xhr.onerror = () =>
      reject(new ApiError(0, "Network error — is the API running?"));

    xhr.send(form);
  });
}

export async function listJobs(): Promise<Job[]> {
  const res = await fetch(`${BASE}/jobs`, { headers: authHeaders() });
  if (!res.ok) return parseError(res);
  const body = await res.json();
  return body.jobs;
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE}/jobs/${jobId}`, { headers: authHeaders() });
  if (!res.ok) return parseError(res);
  return res.json();
}

export async function getResults(jobId: string): Promise<JobResults> {
  const res = await fetch(`${BASE}/jobs/${jobId}/results`, { headers: authHeaders() });
  if (!res.ok) return parseError(res);
  return res.json();
}
