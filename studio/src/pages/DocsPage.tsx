import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSlug from "rehype-slug";
import { BookOpen, ChevronRight, Code2, Menu, X } from "lucide-react";

import overview from "@/docs/overview.md?raw";
import uploading from "@/docs/uploading.md?raw";
import results from "@/docs/results.md?raw";
import jobStatus from "@/docs/job-status.md?raw";
import architecture from "@/dev-docs/architecture.md?raw";
import components from "@/dev-docs/components.md?raw";
import apiReference from "@/dev-docs/api-reference.md?raw";
import deployment from "@/dev-docs/deployment.md?raw";
import { analytics } from "@/analytics/events";
import { cn } from "@/lib/utils";

interface DocPage {
  slug: string;
  title: string;
  content: string;
  section?: "dev";
}

const PAGES: DocPage[] = [
  { slug: "overview", title: "Overview", content: overview },
  { slug: "uploading", title: "Uploading a Module", content: uploading },
  { slug: "results", title: "Reading Results", content: results },
  { slug: "job-status", title: "Job Status", content: jobStatus },
  { slug: "architecture", title: "Architecture", content: architecture, section: "dev" },
  { slug: "components", title: "System Components", content: components, section: "dev" },
  { slug: "api-reference", title: "API Reference", content: apiReference, section: "dev" },
  { slug: "deployment", title: "Deployment", content: deployment, section: "dev" },
];

export default function DocsPage() {
  const [activeSlug, setActiveSlug] = useState(PAGES[0].slug);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    analytics.docsViewed();
  }, []);

  const activePage = PAGES.find((p) => p.slug === activeSlug) ?? PAGES[0];

  const handleSelect = (slug: string) => {
    setActiveSlug(slug);
    setSidebarOpen(false);
  };

  return (
    <div className="mx-auto max-w-5xl">
      {/* Mobile header */}
      <div className="mb-4 flex items-center justify-between lg:hidden">
        <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
          <BookOpen className="h-5 w-5 text-primary" />
          User Documentation
        </h1>
        <button
          onClick={() => setSidebarOpen((v) => !v)}
          className="flex h-9 w-9 items-center justify-center rounded-md border text-muted-foreground hover:bg-accent"
          aria-label="Toggle navigation"
        >
          {sidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </button>
      </div>

      <div className="flex gap-8">
        {/* Sidebar */}
        <aside
          className={cn(
            "shrink-0 lg:w-56",
            sidebarOpen ? "block" : "hidden lg:block",
          )}
        >
          <nav className="sticky top-24 space-y-1">
            <h2 className="mb-3 hidden items-center gap-2 text-sm font-semibold text-muted-foreground lg:flex">
              <BookOpen className="h-4 w-4" />
              User Documentation
            </h2>
            {PAGES.filter((p) => !p.section).map((page) => (
              <button
                key={page.slug}
                onClick={() => handleSelect(page.slug)}
                className={cn(
                  "flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors",
                  page.slug === activeSlug
                    ? "bg-accent font-medium text-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                )}
              >
                <ChevronRight
                  className={cn(
                    "h-3.5 w-3.5 shrink-0 transition-transform",
                    page.slug === activeSlug && "rotate-90",
                  )}
                />
                {page.title}
              </button>
            ))}
            <div className="!mt-8 !mb-4 border-t border-border" />
            <h2 className="mb-3 hidden items-center gap-2 text-sm font-semibold text-muted-foreground lg:flex">
              <Code2 className="h-4 w-4" />
              Developer Docs
            </h2>
            {PAGES.filter((p) => p.section === "dev").map((page) => (
              <button
                key={page.slug}
                onClick={() => handleSelect(page.slug)}
                className={cn(
                  "flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors",
                  page.slug === activeSlug
                    ? "bg-accent font-medium text-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                )}
              >
                <ChevronRight
                  className={cn(
                    "h-3.5 w-3.5 shrink-0 transition-transform",
                    page.slug === activeSlug && "rotate-90",
                  )}
                />
                {page.title}
              </button>
            ))}
          </nav>
        </aside>

        {/* Content */}
        <article className="min-w-0 flex-1">
          <div className="prose max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeSlug]}
              components={{
                ...mdComponents,
                a: ({ children, href }) => {
                  if (href?.startsWith("#")) {
                    const anchor = href.slice(1);
                    const match = PAGES.find((p) =>
                      anchor === p.slug || anchor.startsWith(p.slug),
                    );
                    if (match) {
                      return (
                        <button
                          onClick={() => handleSelect(match.slug)}
                          className="font-medium text-primary underline underline-offset-2 hover:text-primary/80"
                        >
                          {children}
                        </button>
                      );
                    }
                    return (
                      <a
                        href={href}
                        onClick={(e) => {
                          e.preventDefault();
                          const el = document.getElementById(anchor);
                          if (el) el.scrollIntoView({ behavior: "smooth" });
                        }}
                        className="font-medium text-primary underline underline-offset-2 hover:text-primary/80"
                      >
                        {children}
                      </a>
                    );
                  }
                  return (
                    <a
                      href={href}
                      className="font-medium text-primary underline underline-offset-2 hover:text-primary/80"
                    >
                      {children}
                    </a>
                  );
                },
              }}
            >
              {activePage.content}
            </ReactMarkdown>
          </div>
        </article>
      </div>
    </div>
  );
}

const mdComponents: React.ComponentProps<typeof ReactMarkdown>["components"] = {
  h1: ({ children, id }) => (
    <h1 id={id} className="mb-6 text-3xl font-bold tracking-tight text-foreground">
      {children}
    </h1>
  ),
  h2: ({ children, id }) => (
    <h2 id={id} className="mt-8 mb-4 text-xl font-semibold tracking-tight text-foreground">
      {children}
    </h2>
  ),
  h3: ({ children, id }) => (
    <h3 id={id} className="mt-6 mb-3 text-lg font-medium text-foreground">{children}</h3>
  ),
  p: ({ children }) => (
    <p className="mb-4 leading-relaxed text-muted-foreground">{children}</p>
  ),
  ul: ({ children }) => (
    <ul className="mb-4 ml-6 list-disc space-y-1.5 text-muted-foreground">
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-4 ml-6 list-decimal space-y-1.5 text-muted-foreground">
      {children}
    </ol>
  ),
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => (
    <strong className="font-semibold text-foreground">{children}</strong>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-4 border-l-4 border-primary/30 bg-accent/40 px-4 py-3 text-sm italic text-muted-foreground">
      {children}
    </blockquote>
  ),
  code: ({ className, children, ...props }) => {
    const isInline = !className;
    if (isInline) {
      return (
        <code
          className="rounded bg-muted px-1.5 py-0.5 text-sm font-mono text-foreground"
          {...props}
        >
          {children}
        </code>
      );
    }
    return (
      <code className={cn("block", className)} {...props}>
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="my-4 overflow-x-auto rounded-lg border bg-slate-900 p-4 text-sm text-slate-50">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="my-4 overflow-x-auto">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="border-b bg-muted/50">{children}</thead>
  ),
  th: ({ children }) => (
    <th className="px-4 py-2 text-left font-semibold text-foreground">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border-t border-border px-4 py-2 text-muted-foreground">
      {children}
    </td>
  ),
  hr: () => <hr className="my-6 border-border" />,
};
