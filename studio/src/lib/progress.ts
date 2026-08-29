import type { JobStatus, StepProgress } from "@/types";

// Mirrors STEP_ORDER in course_intelligence/engine/graph/steps.py (backend).
export const STEP_ORDER = ["extracting", "chunking", "classifying"] as const;

export function computeProgressPercent(
  status: JobStatus,
  currentStep: string | null,
  stepProgress: StepProgress | null = null,
): number {
  if (status === "completed") return 100;
  if (status === "queued" || !currentStep) return 0;

  const idx = STEP_ORDER.indexOf(currentStep as (typeof STEP_ORDER)[number]);
  if (idx === -1) return 0;

  const stepFraction = 1 / STEP_ORDER.length;

  // Base progress from completed steps
  let percent = idx * stepFraction;

  // Interpolate within the current step using sub-step progress
  if (stepProgress && stepProgress.total > 0) {
    const withinStep = Math.min(stepProgress.current / stepProgress.total, 1);
    percent += withinStep * stepFraction;
  } else {
    // No sub-step data — show the full step as started
    percent += stepFraction;
  }

  return Math.round(percent * 100);
}

export function formatStepProgress(progress: StepProgress | null): string | null {
  if (!progress || progress.total === 0) return null;
  const verb = progress.current < progress.total ? "Processing" : "Processed";
  return `${verb} ${progress.current} of ${progress.total} ${progress.unit}`;
}
