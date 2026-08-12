// Shared types mirroring the FastAPI response schemas (course_intelligence/api.py).

export type JobStatus = "queued" | "processing" | "completed" | "failed";

export interface Job {
  job_id: string;
  status: JobStatus;
  filename: string;
  created_at: string;
  updated_at: string;
  error: string | null;
  current_step: string | null;
  tenant_id: string | null;
}

export interface CreateJobResponse {
  job_id: string;
  status: JobStatus;
}

export interface LearningElement {
  id: string;
  topic: string;
  content: string;
  blooms_level: string | null;
  blooms_rationale: string | null;
  source_page: string | null;
  page_number: number | null;
}

export interface JobResults {
  job_id: string;
  filename: string;
  elements: LearningElement[];
}

// Accepted upload extensions — mirrors SUPPORTED_EXTENSIONS in the backend
// (course_intelligence/dataflows/interface.py).
export const SUPPORTED_EXTENSIONS = [".zip", ".pdf", ".docx", ".txt", ".md"];
