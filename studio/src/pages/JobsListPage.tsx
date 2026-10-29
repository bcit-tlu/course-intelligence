import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, CheckCircle2, Loader2, Clock, Timer, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { ApiError, deleteJob, listJobs } from "@/api/client";
import { analytics } from "@/analytics/events";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { computeProgressPercent } from "@/lib/progress";
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
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const activeRef = useRef(true);

  const handleDelete = useCallback(async (job: Job) => {
    setPending(true);
    try {
      await deleteJob(job.job_id);
      setJobs((prev) => prev.filter((j) => j.job_id !== job.job_id));
      analytics.jobDeleted(job.job_id, job.status);
      toast.success("Job deleted");
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to delete job";
      toast.error(message);
    } finally {
      setPending(false);
      setDeletingId(null);
    }
  }, []);

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
          <Card
            key={job.job_id}
            className="transition-colors hover:border-primary/50 hover:bg-accent/40"
          >
            <CardContent className="flex items-center justify-between py-4">
              <Link
                to={`/jobs/${job.job_id}`}
                className="min-w-0 flex-1 pr-3"
              >
                <p className="truncate font-medium">{job.filename}</p>
                <div className="mt-0.5 flex items-center gap-3 text-sm text-muted-foreground">
                  <span>{formatRelative(job.created_at)}</span>
                  <JobDuration job={job} />
                </div>
                {job.status === "processing" && (
                  <div className="mt-2">
                    <Progress
                      value={computeProgressPercent(job.status, job.current_step, job.step_progress)}
                      className="h-1.5"
                    />
                  </div>
                )}
              </Link>
              <div className="flex items-center gap-2">
                <StatusBadge status={job.status} />
                {job.status !== "processing" && (
                  <AlertDialog
                    open={deletingId === job.job_id}
                    onOpenChange={(open) => {
                      if (!pending) setDeletingId(open ? job.job_id : null);
                    }}
                  >
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      aria-label={`Delete job ${job.filename}`}
                      disabled={pending && deletingId === job.job_id}
                      onClick={() => setDeletingId(job.job_id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete job?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This permanently removes “{job.filename}” and its
                          results. This action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel disabled={pending}>
                          Cancel
                        </AlertDialogCancel>
                        <AlertDialogAction
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                          disabled={pending}
                          onClick={(e) => {
                            e.preventDefault();
                            handleDelete(job);
                          }}
                        >
                          {pending ? "Deleting…" : "Delete"}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
