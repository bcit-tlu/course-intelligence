import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, CheckCircle2, Loader2, Clock, Timer } from "lucide-react";

import { ApiError, listJobs } from "@/api/client";
import { analytics } from "@/analytics/events";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Job, JobStatus } from "@/types";

const POLL_INTERVAL_MS = 2000;
const TERMINAL = new Set<JobStatus>(["completed", "failed"]);

const STATUS_STYLES: Record<JobStatus, string> = {
  queued: "border-border text-muted-foreground",
  processing: "border-primary text-primary",
  completed: "border-emerald-500 text-emerald-600",
  failed: "border-destructive text-destructive",
};

function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <Badge className={cn("gap-1", STATUS_STYLES[status])}>
      {status === "processing" && <Loader2 className="h-3 w-3 animate-spin" />}
      {status === "completed" && <CheckCircle2 className="h-3 w-3" />}
      {status === "failed" && <AlertCircle className="h-3 w-3" />}
      {status === "queued" && <Clock className="h-3 w-3" />}
      <span className="capitalize">{status}</span>
    </Badge>
  );
}

function formatRelative(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function useElapsed(startIso: string): string {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const seconds = Math.max(0, Math.floor((now - new Date(startIso).getTime()) / 1000));
  return formatDuration(seconds);
}

function JobDuration({ job }: { job: Job }) {
  if (job.status === "processing") {
    const elapsed = useElapsed(job.created_at);
    return (
      <span className="flex items-center gap-1 text-sm text-primary">
        <Timer className="h-3.5 w-3.5" />
        {elapsed}
      </span>
    );
  }
  if (job.status === "completed" || job.status === "failed") {
    const seconds = Math.max(
      0,
      Math.floor(
        (new Date(job.updated_at).getTime() -
          new Date(job.created_at).getTime()) /
          1000,
      ),
    );
    return (
      <span className="flex items-center gap-1 text-sm text-muted-foreground">
        <Timer className="h-3.5 w-3.5" />
        {formatDuration(seconds)}
      </span>
    );
  }
  return null;
}

export default function JobsListPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const activeRef = useRef(true);

  const fetchJobs = useCallback(async () => {
    try {
      const list = await listJobs();
      if (!activeRef.current) return;
      setJobs(list);
      setLoading(false);
      setError(null);
      analytics.jobsListed(list.length);

      // Keep polling only if there are non-terminal jobs
      if (!list.some((j) => !TERMINAL.has(j.status))) return;
      setTimeout(fetchJobs, POLL_INTERVAL_MS);
    } catch (err) {
      if (!activeRef.current) return;
      const message =
        err instanceof ApiError ? err.message : "Failed to load jobs";
      setError(message);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    activeRef.current = true;
    fetchJobs();
    return () => {
      activeRef.current = false;
    };
  }, [fetchJobs]);

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          <span>Loading jobs…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl">
        <Card className="border-destructive/40">
          <CardHeader>
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <CardTitle className="text-xl">Unable to load jobs</CardTitle>
            </div>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link to="/">Back to upload</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="mx-auto max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle>No jobs yet</CardTitle>
            <CardDescription>
              Uploaded course modules will appear here.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link to="/">Upload a module</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Job History</h1>
      <div className="space-y-3">
        {jobs.map((job) => (
          <Link
            key={job.job_id}
            to={`/jobs/${job.job_id}`}
            className="block"
          >
            <Card className="transition-colors hover:border-primary/50 hover:bg-accent/40">
              <CardContent className="flex items-center justify-between py-4">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{job.filename}</p>
                  <div className="mt-0.5 flex items-center gap-3 text-sm text-muted-foreground">
                    <span>{formatRelative(job.created_at)}</span>
                    <JobDuration job={job} />
                  </div>
                </div>
                <StatusBadge status={job.status} />
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
