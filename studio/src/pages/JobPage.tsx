import { Link, useParams } from "react-router-dom";
import { AlertCircle } from "lucide-react";

import ProcessingView from "@/components/ProcessingView";
import ResultsSkeleton from "@/components/ResultsSkeleton";
import ResultsView from "@/components/ResultsView";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useJob } from "@/hooks/useJob";

export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  const { job, results, loading, error } = useJob(id);

  // Fatal error (e.g. job not found / network failure)
  if (error) {
    return (
      <div className="mx-auto max-w-2xl">
        <Card className="border-destructive/40">
          <CardHeader>
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <CardTitle className="text-xl">Unable to load job</CardTitle>
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

  // Initial load, before the first job fetch resolves
  if (loading || !job) {
    return <ResultsSkeleton />;
  }

  // Completed and results are in
  if (job.status === "completed") {
    return results ? <ResultsView results={results} /> : <ResultsSkeleton />;
  }

  // queued / processing / failed
  return <ProcessingView job={job} />;
}
