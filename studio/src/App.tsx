import { Link, Route, Routes } from "react-router-dom";
import { BookOpen, GraduationCap, History } from "lucide-react";

import DocsPage from "@/pages/DocsPage";
import JobPage from "@/pages/JobPage";
import JobsListPage from "@/pages/JobsListPage";
import UploadPage from "@/pages/UploadPage";

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      <header className="border-b bg-white/70 backdrop-blur">
        <div className="container flex h-16 items-center gap-2">
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <GraduationCap className="h-6 w-6 text-primary" />
            <span>Course Intelligence</span>
            <span className="text-muted-foreground font-normal">
              Studio
            </span>
          </Link>
          <nav className="ml-auto flex items-center gap-6">
            <Link
              to="/docs"
              className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <BookOpen className="h-4 w-4" />
              Docs
            </Link>
            <Link
              to="/jobs"
              className="flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              <History className="h-4 w-4" />
              History
            </Link>
          </nav>
        </div>
      </header>

      <main className="container py-10">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/docs" element={<DocsPage />} />
          <Route path="/jobs" element={<JobsListPage />} />
          <Route path="/jobs/:id" element={<JobPage />} />
        </Routes>
      </main>
    </div>
  );
}
