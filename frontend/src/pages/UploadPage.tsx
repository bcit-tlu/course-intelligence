import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Loader2, UploadCloud, X } from "lucide-react";
import { toast } from "sonner";

import { ApiError, createJob } from "@/api/client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { cn, formatBytes } from "@/lib/utils";
import { SUPPORTED_EXTENSIONS } from "@/types";

function getExtension(filename: string): string {
  const dot = filename.lastIndexOf(".");
  return dot === -1 ? "" : filename.slice(dot).toLowerCase();
}

export default function UploadPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [objectives, setObjectives] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const selectFile = useCallback((candidate: File) => {
    const ext = getExtension(candidate.name);
    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
      toast.error(`Unsupported file type "${ext || "unknown"}"`, {
        description: `Accepted: ${SUPPORTED_EXTENSIONS.join(", ")}`,
      });
      return;
    }
    setFile(candidate);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      const dropped = e.dataTransfer.files?.[0];
      if (dropped) selectFile(dropped);
    },
    [selectFile],
  );

  const onSubmit = useCallback(async () => {
    if (!file) return;
    setUploading(true);
    setProgress(0);
    try {
      const { job_id } = await createJob(file, objectives, setProgress);
      toast.success("Upload complete — processing started");
      navigate(`/jobs/${job_id}`);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Upload failed unexpectedly";
      toast.error("Upload failed", { description: message });
      setUploading(false);
    }
  }, [file, objectives, navigate]);

  return (
    <div className="mx-auto max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Upload a Course Module</CardTitle>
          <CardDescription>
            Upload a D2L export or document to extract learning elements and
            classify them by Bloom&apos;s taxonomy.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Drop zone */}
          <div
            role="button"
            tabIndex={0}
            onClick={() => inputRef.current?.click()}
            onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={onDrop}
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-10 text-center transition-colors",
              dragActive
                ? "border-primary bg-primary/5"
                : "border-input hover:border-primary/50 hover:bg-accent/50",
            )}
          >
            <input
              ref={inputRef}
              type="file"
              className="hidden"
              accept={SUPPORTED_EXTENSIONS.join(",")}
              onChange={(e) => {
                const chosen = e.target.files?.[0];
                if (chosen) selectFile(chosen);
                e.target.value = "";
              }}
            />
            <UploadCloud className="mb-3 h-10 w-10 text-muted-foreground" />
            <p className="font-medium">
              Drag &amp; drop a file, or click to browse
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {SUPPORTED_EXTENSIONS.join(", ")}
            </p>
          </div>

          {/* Selected file */}
          {file && (
            <div className="flex items-center justify-between rounded-md border bg-muted/40 px-4 py-3">
              <div className="flex min-w-0 items-center gap-3">
                <FileText className="h-5 w-5 shrink-0 text-primary" />
                <div className="min-w-0">
                  <p className="truncate font-medium">{file.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {formatBytes(file.size)}
                  </p>
                </div>
              </div>
              {!uploading && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setFile(null)}
                  aria-label="Remove file"
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          )}

          {/* Upload progress */}
          {uploading && (
            <div className="space-y-1">
              <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full bg-primary transition-all"
                  style={{ width: `${Math.round(progress * 100)}%` }}
                />
              </div>
              <p className="text-right text-xs text-muted-foreground">
                {Math.round(progress * 100)}%
              </p>
            </div>
          )}

          {/* Learning objectives */}
          <div className="space-y-2">
            <label htmlFor="objectives" className="text-sm font-medium">
              Learning objectives{" "}
              <span className="text-muted-foreground">
                (optional, one per line)
              </span>
            </label>
            <Textarea
              id="objectives"
              placeholder={"e.g. Describe the key principles of…\nExplain how to…\nDemonstrate…"}
              rows={4}
              value={objectives}
              disabled={uploading}
              onChange={(e) => setObjectives(e.target.value)}
            />
          </div>
        </CardContent>

        <CardFooter>
          <Button
            className="w-full"
            disabled={!file || uploading}
            onClick={onSubmit}
          >
            {uploading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Uploading…
              </>
            ) : (
              "Process Module"
            )}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
