import { useEffect, useRef, useState } from "react";

import { ApiError, getJob, getResults } from "@/api/client";
import type { Job, JobResults } from "@/types";

const POLL_INTERVAL_MS = 2000;
const TERMINAL = new Set(["completed", "failed"]);

interface UseJobState {
  job: Job | null;
  results: JobResults | null;
  loading: boolean; // initial load, before the first job fetch resolves
  error: string | null; // fatal error (e.g. job not found)
}

/**
 * Poll a job until it reaches a terminal state, then fetch its results.
 * Polling stops automatically on completed/failed or on unmount.
 */
export function useJob(jobId: string | undefined): UseJobState {
  const [job, setJob] = useState<Job | null>(null);
  const [results, setResults] = useState<JobResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Guards against setState after unmount / overlapping fetches.
  const activeRef = useRef(true);

  useEffect(() => {
    if (!jobId) return;

    activeRef.current = true;
    let timer: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const next = await getJob(jobId);
        if (!activeRef.current) return;

        setJob(next);
        setLoading(false);

        if (next.status === "completed") {
          const res = await getResults(jobId);
          if (activeRef.current) setResults(res);
          return; // terminal — stop polling
        }
        if (next.status === "failed") {
          return; // terminal — stop polling
        }

        timer = setTimeout(poll, POLL_INTERVAL_MS);
      } catch (err) {
        if (!activeRef.current) return;
        const message =
          err instanceof ApiError ? err.message : "Failed to load job";
        setError(message);
        setLoading(false);
      }
    };

    poll();

    return () => {
      activeRef.current = false;
      clearTimeout(timer);
    };
  }, [jobId]);

  return { job, results, loading, error };
}

export { TERMINAL };
