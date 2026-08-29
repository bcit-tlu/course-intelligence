import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { computeProgressPercent, formatStepProgress } from "@/lib/progress";
import { cn } from "@/lib/utils";
import type { Job } from "@/types";

function useElapsed(startIso: string): string {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const seconds = Math.max(0, Math.floor((now - new Date(startIso).getTime()) / 1000));
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

// Pipeline steps — mirrors STEP_ORDER in course_intelligence/engine/graph/steps.py (backend).
const STEPS = [
  { key: "extracting", label: "Extracting course content" },
  { key: "chunking", label: "Identifying learning elements" },
  { key: "classifying", label: "Classifying cognitive levels" },
] as const;

export default function ProcessingView({ job }: { job: Job }) {
  const elapsed = useElapsed(job.created_at);

  if (job.status === "failed") {
    const failedStepIndex = job.current_step
      ? STEPS.findIndex((s) => s.key === job.current_step)
      : -1;
    return (
      <div className="mx-auto max-w-2xl">
        <Card className="border-destructive/40">
          <CardHeader>
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <CardTitle className="text-xl">Processing Failed</CardTitle>
            </div>
            <CardDescription>{job.filename}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {failedStepIndex >= 0 && (
              <p className="text-xs text-muted-foreground">
                Failed during: {STEPS[failedStepIndex].label}
              </p>
            )}
            <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {job.error ?? "An unknown error occurred."}
            </p>
            <Button asChild variant="outline">
              <Link to="/">Try another file</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const currentIndex = job.current_step
    ? STEPS.findIndex((s) => s.key === job.current_step)
    : -1;
  const isQueued = job.status === "queued";

  return (
    <div className="mx-auto max-w-2xl">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <CardTitle className="text-xl">Processing Module</CardTitle>
          </div>
          <CardDescription>
            {job.filename} · {elapsed} elapsed
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isQueued && (
            <p className="mb-4 text-sm text-muted-foreground">
              Queued for processing…
            </p>
          )}
          <div className="mb-6 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Overall progress</span>
              <span className="font-medium">
                {computeProgressPercent(job.status, job.current_step)}%
              </span>
            </div>
            <Progress
              value={computeProgressPercent(job.status, job.current_step)}
            />
          </div>
          <ol className="space-y-4">
            {STEPS.map((step, i) => {
              const done = i < currentIndex;
              const active = i === currentIndex;
              return (
                <li key={step.key} className="flex items-start gap-3">
                  <span
                    className={cn(
                      "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs",
                      done && "border-primary bg-primary text-primary-foreground",
                      active && "border-primary text-primary",
                      !done && !active && "border-border text-muted-foreground",
                    )}
                  >
                    {done ? (
                      <CheckCircle2 className="h-4 w-4" />
                    ) : active ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      i + 1
                    )}
                  </span>
                  <div className="flex flex-col">
                    <span
                      className={cn(
                        "text-sm",
                        active ? "font-medium" : "text-muted-foreground",
                      )}
                    >
                      {step.label}
                    </span>
                    {active && formatStepProgress(job.step_progress) && (
                      <span className="text-xs text-muted-foreground">
                        {formatStepProgress(job.step_progress)}
                      </span>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
          <p className="mt-6 text-xs text-muted-foreground">
            This can take several minutes for a full course module. The page
            updates automatically.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
