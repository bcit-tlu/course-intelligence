# Course Intelligence Studio

Vite + React + TypeScript + Tailwind CSS UI for the Course Intelligence platform.

## Prerequisites

- Node.js 20+
- The backend API running on `http://localhost:8000` (see the repo root
  `README` / `docker compose up`)

## Development

```bash
npm install
npm run dev
```

The app runs at http://localhost:5173. API calls to `/api/*` are proxied
to the backend at `http://localhost:8000` (see `vite.config.ts`), so no
CORS configuration is needed in development.

## Build

```bash
npm run build      # type-check + production build into dist/
npm run preview    # preview the production build locally
```

## Structure

```text
src/
├── App.tsx              # routes: / (upload), /docs, /jobs, /jobs/:id
├── main.tsx            # entry point (router + toaster)
├── types.ts            # types mirroring the API schemas
├── vite-env.d.ts       # Vite client types (?raw imports)
├── api/client.ts       # typed fetch/XHR wrappers (createJob, getJob, getResults)
├── hooks/
│   └── useJob.ts       # polling hook for job status
├── components/
│   ├── ui/             # shadcn-style primitives (button, card, textarea)
│   ├── BloomsBadge.tsx     # Bloom's level badge
│   ├── BloomsSummary.tsx   # Bloom's distribution summary
│   ├── ElementCard.tsx     # single knowledge element card
│   ├── LevelFilter.tsx     # filter results by Bloom's level
│   ├── ProcessingView.tsx  # processing progress indicator
│   ├── ResultsView.tsx     # results layout with filtering
│   └── ResultsSkeleton.tsx # loading skeleton for results
├── docs/               # user manual markdown pages (bundled at build time)
│   ├── overview.md         # what Course Intelligence does, pipeline overview
│   ├── uploading.md        # how to upload a module
│   ├── results.md          # how to read results + Bloom's badges
│   └── job-status.md       # job lifecycle and polling
├── lib/
│   ├── utils.ts        # cn() + formatBytes()
│   └── blooms.ts       # Bloom's level constants, ordering, and helpers
└── pages/
    ├── UploadPage.tsx  # drag-drop upload + learning objectives
    ├── DocsPage.tsx    # user manual with sidebar nav + markdown rendering
    ├── JobsListPage.tsx # job history with status filtering
    └── JobPage.tsx     # job status + results with Bloom's badges
```

## Routes

- `/` — upload a module (drag-drop or picker), enter learning objectives,
  submit to create a job.
- `/docs` — user manual documentation (markdown pages rendered in-app).
- `/jobs` — job history list with status filtering.
- `/jobs/:id` — job status with live progress, results with Bloom's badges
  and level filtering.

## Dependencies

Core UI dependencies include React, React Router, Tailwind CSS, and Lucide
icons. The docs page additionally uses:

- `react-markdown` — renders markdown as React components
- `remark-gfm` — GitHub-flavored markdown (tables, strikethrough, task lists)
